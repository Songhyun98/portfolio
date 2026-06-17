"""
네이버 쇼핑인사이트 수집기
키워드별 × 성별 × 연령 조합으로 수집
각 키워드 내에서 성별/연령 분포 파악용
"""

import requests
import json
from datetime import datetime
from typing import Optional

try:
    from collectors.base import with_retry, raise_for_status, DEFAULT_TIMEOUT
except ImportError:
    from base import with_retry, raise_for_status, DEFAULT_TIMEOUT


COLLECT_START_DATE = "2023-01-01"

# 키워드별 단독 요청 (param 1개씩)
KEYWORDS = [
    {"name": "아키클래식",   "param": ["아키클래식"]},
    # {"name": "여행시그널",   "param": ["트래킹화"]},
    # {"name": "발건강시그널", "param": ["발 건강 운동화"]},
    # {"name": "컴포트수요지수", "param": ["발 편한 운동화"]},
]

# 성별 
GENDERS = [
    {"label": "all", "param": ""},  # API는 빈 문자열로 all 구분
    {"label": "m", "param": "m"},
    {"label": "f", "param": "f"},
]

# 연령
AGES = [
    {"label": "all", "param": []},  # API는 빈 리스트로 all 구분
    {"label": "10s",  "param": ["10"]},
    {"label": "20s",  "param": ["20"]},
    {"label": "30s",  "param": ["30"]},
    {"label": "40s",  "param": ["40"]},
    {"label": "50s",  "param": ["50"]},
    {"label": "60s+", "param": ["60"]},
]


class NaverShoppingCollector:

    BASE_URL = "https://openapi.naver.com/v1/datalab/shopping"

    def __init__(self, client_id: str, client_secret: str):
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json",
        }

    def fetch_keyword_trend(
        self,
        category: str,
        keyword: dict,
        gender: str,
        ages: list,
        start_date: str = None,
        end_date: str = None,
        time_unit: str = "week",
    ) -> dict:
        if not end_date:
            end_date = datetime.today().strftime("%Y-%m-%d")
        if not start_date:
            start_date = COLLECT_START_DATE

        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": category,
            "keyword": [keyword],
            "device": "",
            "gender": gender,
            "ages": ages,
        }

        def _call():
            response = requests.post(
                f"{self.BASE_URL}/category/keywords",
                headers=self.headers,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                timeout=DEFAULT_TIMEOUT,
            )
            raise_for_status(response, "쇼핑인사이트 키워드 API")
            return response.json()

        return with_retry(_call, label=f"쇼핑({keyword['name']}, gender={gender}, ages={ages})")

    def fetch_all(self, category: str = "50000167") -> list[dict]:
        """
        키워드별 × 성별 × 연령 전체 수집
        총 48회 호출 (4키워드 × 3성별 × 7연령)
        """
        all_rows = []
        collected_at = datetime.now().isoformat()
        total = len(KEYWORDS) * len(GENDERS) * len(AGES)
        count = 0

        for keyword in KEYWORDS:
            for gender in GENDERS:
                for age in AGES:
                    count += 1
                    label = f"{keyword['name']} / gender={gender['label']} / age={age['label']}"
                    print(f"  [{count}/{total}] {label} 수집 중...")

                    try:
                        raw = self.fetch_keyword_trend(
                            category=category,
                            keyword=keyword,
                            gender=gender["param"],
                            ages=age["param"],
                        )
                        rows = self.parse_to_rows(
                            raw,
                            gender=gender["label"],
                            age=age["label"],
                            collected_at=collected_at,
                        )
                        all_rows.extend(rows)
                        print(f"     {len(rows)}개 수집")
                    except Exception as e:
                        print(f"     실패 (재시도 소진): {e}")

        return all_rows

    def parse_to_rows(
        self,
        api_response: dict,
        gender: str,
        age: str,
        collected_at: Optional[str] = None,
    ) -> list[dict]:
        """
        API 응답 -> DB insert용 행 리스트 변환

        반환 예시:
        {
            "period": "2023-01-02",
            "keyword": "아키클래식",
            "gender": "f",
            "age": "20s",
            "ratio": 12.5,
            "collected_at": "..."
        }
        """
        if not collected_at:
            collected_at = datetime.now().isoformat()

        rows = []
        for result in api_response.get("results", []):
            keyword_name = result["title"]
            for data_point in result["data"]:
                rows.append({
                    "period":       data_point["period"],
                    "keyword":      keyword_name,
                    "gender":       gender,
                    "age":          age,
                    "ratio":        data_point["ratio"],
                    "collected_at": collected_at,
                })
        return rows


# -- 실행 테스트 ----------------------------------------------
if __name__ == "__main__":
    import os

    collector = NaverShoppingCollector(
        client_id=os.getenv("NAVER_CLIENT_ID", "YOUR_CLIENT_ID"),
        client_secret=os.getenv("NAVER_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    )

    print("▶ 쇼핑인사이트 수집 시작 (2023-01-01 ~)")
    rows = collector.fetch_all()

    print(f"\n총 {len(rows)}개 데이터 포인트 수집 완료")
    for row in rows[:5]:
        print(row)