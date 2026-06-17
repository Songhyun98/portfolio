"""
Supabase 읽기 모듈
분석가가 Supabase 테이블을 DataFrame으로 읽어오는 모듈
PostgREST 1000행 제한을 .range()로 우회
"""

import pandas as pd
from supabase import create_client, Client


class SupabaseReader:

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    def fetch_all(self, table: str) -> pd.DataFrame:
        """
        테이블 전체 읽기 (1000행 제한 우회)

        사용 예시:
        df = reader.fetch_all("search_trend")
        """
        rows = []
        start = 0
        page_size = 1000

        while True:
            response = (
                self.client.table(table)
                .select("*")
                .range(start, start + page_size - 1)
                .execute()
            )
            data = response.data
            rows.extend(data)

            if len(data) < page_size:
                break
            start += page_size

        print(f"  📂 [{table}] 총 {len(rows)}행 로드")
        return pd.DataFrame(rows)

    def fetch_filtered(self, table: str, filters: dict) -> pd.DataFrame:
        """
        조건 필터링해서 읽기

        사용 예시:
        df = reader.fetch_filtered("search_trend", {"axis": "direct"})
        df = reader.fetch_filtered("search_trend", {"keyword_group": "아키클래식"})
        """
        rows = []
        start = 0
        page_size = 1000

        while True:
            query = self.client.table(table).select("*")
            for col, val in filters.items():
                query = query.eq(col, val)

            response = query.range(start, start + page_size - 1).execute()
            data = response.data
            rows.extend(data)

            if len(data) < page_size:
                break
            start += page_size

        print(f"  📂 [{table}] {filters} → {len(rows)}행 로드")
        return pd.DataFrame(rows)


# ── 사용 예시 ─────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    reader = SupabaseReader(
        url=os.getenv("SUPABASE_URL"),
        key=os.getenv("SUPABASE_KEY"),
    )

    # 전체 읽기
    df_search = reader.fetch_all("search_trend")
    print(df_search.head())

    # 필터링 읽기
    df_direct = reader.fetch_filtered("search_trend", {"axis": "direct"})
    print(df_direct.head())

    # 전체 테이블 행 수 확인
    print("\n▶ 테이블별 행 수")
    for table in ["search_trend", "mention_total", "mention_blog", "mention_news", "mention_cafe", "shopping_trend"]:
        df = reader.fetch_all(table)
        print(f"  {table}: {len(df)}행")