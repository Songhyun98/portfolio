"""
네이버 검색 API - 블로그/뉴스/카페 수집기
- mention_total: 키워드별 총 언급량 스냅샷
- mention_blog:  블로그 개별 문서
- mention_news:  뉴스 개별 문서
- mention_cafe:  카페 개별 문서
"""

import requests
from datetime import datetime
from typing import Optional

try:
    from collectors.base import with_retry, raise_for_status, DEFAULT_TIMEOUT
except ImportError:
    from base import with_retry, raise_for_status, DEFAULT_TIMEOUT


# 수집 대상 키워드 (정확히 일치 검색)
KEYWORDS = ['"아키클래식"', '"포즈간츠"', '"23.65"']

DISPLAY = 100       # 1회 요청당 문서 수 (최대 100)
MAX_DOCS = 1000     # 키워드당 최대 수집 건수 (API 한계)


class NaverSearchCollector:

    BLOG_URL = "https://openapi.naver.com/v1/search/blog.json"
    NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
    CAFE_URL = "https://openapi.naver.com/v1/search/cafearticle.json"

    def __init__(self, client_id: str, client_secret: str):
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    def _search_page(self, url: str, query: str, start: int, display: int = DISPLAY) -> dict:
        """단일 페이지 요청"""
        params = {
            "query":   query,
            "display": display,
            "start":   start,
            "sort":    "date",
        }

        def _call():
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )
            raise_for_status(response, f"검색 API ({query})")
            return response.json()

        return with_retry(_call, label=f"검색({query}, start={start})")

    def _search_all_pages(self, url: str, query: str, max_docs: int = MAX_DOCS) -> dict:
        """
        페이지네이션으로 최대 max_docs건 수집
        첫 요청에서 total 확인 후 실제 수집 가능한 만큼만 요청
        """
        first = self._search_page(url, query, start=1)
        total = first.get("total", 0)
        items = first.get("items", [])

        # 실제 수집 가능한 최대값 (API 한계 1000건, total 중 작은 값)
        collect_limit = min(total, max_docs)

        start = DISPLAY + 1
        while len(items) < collect_limit and start <= MAX_DOCS:
            remaining = collect_limit - len(items)
            display = min(DISPLAY, remaining)
            page = self._search_page(url, query, start=start, display=display)
            items.extend(page.get("items", []))
            start += DISPLAY

        first["items"] = items
        return first

    def fetch_all(self) -> dict:
        """
        전체 키워드 × 블로그/뉴스/카페 수집
        키워드당 최대 1000건 × 3개 = 최대 3000건

        반환:
        {
            "total": [...],  # mention_total 테이블용
            "blog":  [...],  # mention_blog 테이블용
            "news":  [...],  # mention_news 테이블용
            "cafe":  [...],  # mention_cafe 테이블용
        }
        """
        collected_at = datetime.now().isoformat()
        result = {"total": [], "blog": [], "news": [], "cafe": []}

        for keyword in KEYWORDS:
            print(f"  ▶ '{keyword}' 수집 중...")

            blog_raw = self._search_all_pages(self.BLOG_URL, keyword)
            news_raw = self._search_all_pages(self.NEWS_URL, keyword)
            cafe_raw = self._search_all_pages(self.CAFE_URL, keyword)

            # total 스냅샷
            result["total"].append({
                "keyword":      keyword.strip('"'),
                "blog_total":   blog_raw.get("total", 0),
                "news_total":   news_raw.get("total", 0),
                "cafe_total":   cafe_raw.get("total", 0),
                "collected_at": collected_at,
            })

            # 블로그 개별 문서
            for item in blog_raw.get("items", []):
                result["blog"].append({
                    "keyword":      keyword.strip('"'),
                    "title":        item.get("title", ""),
                    "description":  item.get("description", ""),
                    "bloggername":  item.get("bloggername", ""),
                    "postdate":     item.get("postdate", ""),
                    "link":         item.get("link", ""),
                    "collected_at": collected_at,
                })

            # 뉴스 개별 문서
            for item in news_raw.get("items", []):
                result["news"].append({
                    "keyword":       keyword.strip('"'),
                    "title":         item.get("title", ""),
                    "description":   item.get("description", ""),
                    "originallink":  item.get("originallink", ""),
                    "pub_date":      item.get("pubDate", ""),
                    "link":          item.get("link", ""),
                    "collected_at":  collected_at,
                })

            # 카페 개별 문서
            for item in cafe_raw.get("items", []):
                result["cafe"].append({
                    "keyword":      keyword.strip('"'),
                    "title":        item.get("title", ""),
                    "description":  item.get("description", ""),
                    "cafename":     item.get("cafename", ""),
                    "cafeurl":      item.get("cafeurl", ""),
                    "link":         item.get("link", ""),
                    "collected_at": collected_at,
                })

            print(f"     블로그 {len(blog_raw.get('items',[]))}건 / 뉴스 {len(news_raw.get('items',[]))}건 / 카페 {len(cafe_raw.get('items',[]))}건 수집 (전체: 블로그 {blog_raw.get('total',0):,} / 뉴스 {news_raw.get('total',0):,} / 카페 {cafe_raw.get('total',0):,})")

        # 중복 제거 (네이버 API 페이지네이션 중복 방지)
        result["blog"] = list({(item["keyword"], item["link"]): item for item in result["blog"]}.values())
        result["news"] = list({(item["keyword"], item["link"]): item for item in result["news"]}.values())
        result["cafe"] = list({(item["keyword"], item["link"]): item for item in result["cafe"]}.values())

        return result


# ── 실행 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    import os

    collector = NaverSearchCollector(
        client_id=os.getenv("NAVER_CLIENT_ID", "YOUR_CLIENT_ID"),
        client_secret=os.getenv("NAVER_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    )

    print("▶ 네이버 검색 수집 시작...")
    result = collector.fetch_all()

    print(f"\n✅ 수집 완료")
    print(f"  total: {len(result['total'])}행")
    print(f"  blog:  {len(result['blog'])}행")
    print(f"  news:  {len(result['news'])}행")
    print(f"  cafe:  {len(result['cafe'])}행")