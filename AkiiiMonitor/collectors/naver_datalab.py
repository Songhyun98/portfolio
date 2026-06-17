"""
네이버 DataLab API - 검색어 트렌드 수집기
아키클래식 vs 컴포트화 시장 키워드 검색량 수집
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional

try:
    from collectors.base import with_retry, raise_for_status, DEFAULT_TIMEOUT
except ImportError:
    from base import with_retry, raise_for_status, DEFAULT_TIMEOUT


# 수집 기준 시작일 고정
COLLECT_START_DATE = "2023-01-01"


class NaverDataLabCollector:
    """네이버 DataLab 통합 검색어 트렌드 API"""

    BASE_URL = "https://openapi.naver.com/v1/datalab/search"

    def __init__(self, client_id: str, client_secret: str):
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json",
        }

    def fetch_trend(
        self,
        keyword_groups: list[dict],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        time_unit: str = "week",
    ) -> dict:
        """
        검색어 트렌드 조회

        keyword_groups 예시:
        [
            {"groupName": "아키클래식", "keywords": ["아키클래식", "ARCHIES"]},
            {"groupName": "컴포트화", "keywords": ["컴포트화", "편한신발"]},
        ]
        """
        if not end_date:
            end_date = datetime.today().strftime("%Y-%m-%d")
        if not start_date:
            start_date = COLLECT_START_DATE

        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keyword_groups,
        }

        def _call():
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                data=json.dumps(body),
                timeout=DEFAULT_TIMEOUT,
            )
            raise_for_status(response, "DataLab API")
            return response.json()

        return with_retry(_call, label="네이버 DataLab")

    def fetch_by_axis(self, axis: str, keyword_groups: list[dict]) -> dict:
        """
        axis별 트렌드 수집

        axis: "direct" / "mass" / "market"
        """
        return self.fetch_trend(keyword_groups)

    def fetch_all(self) -> list[dict]:
        """
        3개 axis 전체 수집 → rows 반환
        """
        axes = {
            "direct": [
                {
                    "groupName": "아키클래식",
                    "keywords": ["아키클래식", "AKIII", "AKIII CLASSIC", "아키 클래식"],
                },
                {
                    "groupName": "포즈간츠",
                    "keywords": ["포즈간츠", "포츠간츠", "POSEGANCH", "포즈 간츠"],
                },
                {
                    "groupName": "23.65",
                    "keywords": ["23.65", "이십삼점육오", "2365"],
                },
            ],
            "mass": [
                {
                    "groupName": "아키클래식",
                    "keywords": ["아키클래식", "AKIII", "AKIII CLASSIC", "아키 클래식"],
                },
                {
                    "groupName": "스케쳐스",
                    "keywords": ["스케쳐스", "스케처스", "Skechers"],
                },
                {
                    "groupName": "휠라",
                    "keywords": ["휠라", "FILA"],
                },
            ],
            "market": [
                {
                    "groupName":"아키클래식",
                    "keywords":["아키클래식","AKIII","AKIII CLASSIC","아키 클래식"],
                },                       # ① 브랜드 층(anchor)
                {
                    "groupName":"컴포트수요지수",
                    "keywords":["편한 운동화","발 편한 신발","편한 신발","컴포트화","워킹화","경량 운동화"]
                },  # ② 시장 인덱스 층
                {
                    "groupName":"여행시그널",
                    "keywords":["여행 운동화","여행운동화","여행용 운동화","트레킹화","트래킹화"],
                },          # ③ 베팅1: 라이프스타일·여행
                {
                    "groupName":"발건강시그널",
                    "keywords":["족저근막염 운동화","족저근막 운동화","족저근막염 신발","아치서포트","발건강 운동화","발 건강 신발"]
                },  # ④ 베팅2: 의학적 편안함(APMA 해자)
            ],
        }

        all_rows = []
        collected_at = datetime.now().isoformat()

        for axis, keyword_groups in axes.items():
            print(f"  ▶ axis={axis} 수집 중...")
            raw = self.fetch_by_axis(axis, keyword_groups)
            rows = self.parse_to_rows(raw, axis=axis, collected_at=collected_at)
            all_rows.extend(rows)
            print(f"  ✅ axis={axis} {len(rows)}개 수집 완료")

        return all_rows

    def parse_to_rows(
        self,
        api_response: dict,
        axis: str,
        collected_at: Optional[str] = None,
    ) -> list[dict]:
        """
        API 응답 → DB insert용 행 리스트 변환

        반환 예시:
        [
            {
                "period": "2023-01-01",
                "keyword_group": "아키클래식",
                "axis": "direct",
                "ratio": 45.23,
                "collected_at": "..."
            },
            ...
        ]
        """
        if not collected_at:
            collected_at = datetime.now().isoformat()

        rows = []
        for result in api_response.get("results", []):
            group_name = result["title"]
            for data_point in result["data"]:
                rows.append({
                    "period": data_point["period"],
                    "keyword_group": group_name,
                    "axis": axis,
                    "ratio": data_point["ratio"],
                    "collected_at": collected_at,
                })
        return rows


# ── 실행 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    import os

    collector = NaverDataLabCollector(
        client_id=os.getenv("NAVER_CLIENT_ID", "YOUR_CLIENT_ID"),
        client_secret=os.getenv("NAVER_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    )

    print("▶ 네이버 DataLab 전체 수집 시작 (2023-01-01 ~)")
    rows = collector.fetch_all()

    print(f"\n✅ 총 {len(rows)}개 데이터 포인트 수집 완료")
    for row in rows[:5]:
        print(row)