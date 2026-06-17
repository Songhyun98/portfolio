"""
raw 데이터 저장 모듈
수집된 데이터를 data/raw/ 에 parquet으로 저장
파일명 규칙: {source}_{YYYYMMDD}.parquet
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

RAW_DIR = Path("data/raw")


def save_raw(
    df: pd.DataFrame,
    source: str,
    date: str = None,
) -> Path:
    if df.empty:
        raise ValueError(f"[{source}] 빈 DataFrame — 저장 스킵 (수집 실패 여부 확인 필요)")

    if date is None:
        date = datetime.today().strftime("%Y%m%d")

    save_dir = RAW_DIR / source
    save_dir.mkdir(parents=True, exist_ok=True)

    filepath = save_dir / f"{source}_{date}.parquet"
    df.to_parquet(filepath, index=False)

    print(f"  💾 저장 완료: {filepath} ({len(df)}행)")
    return filepath


def load_latest(source: str) -> pd.DataFrame:
    source_dir = RAW_DIR / source
    files = sorted(source_dir.glob(f"{source}_*.parquet"))

    if not files:
        raise FileNotFoundError(f"'{source}' 데이터 없음: {source_dir}")

    latest = files[-1]
    print(f"  📂 로드: {latest}")
    return pd.read_parquet(latest)


def load_all(source: str) -> pd.DataFrame:
    source_dir = RAW_DIR / source
    files = sorted(source_dir.glob(f"{source}_*.parquet"))

    if not files:
        raise FileNotFoundError(f"'{source}' 데이터 없음: {source_dir}")

    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)

    dedup_cols = [c for c in ["period", "keyword", "keyword_group"] if c in df.columns]
    if dedup_cols:
        df = df.drop_duplicates(subset=dedup_cols, keep="last")

    print(f"  📂 {len(files)}개 파일 합산: {len(df)}행")
    return df


# ── 실행 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    load_dotenv()

    from collectors.naver_datalab import NaverDataLabCollector
    # from collectors.google_trends import GoogleTrendsCollector
    from collectors.naver_search import NaverSearchCollector
    from collectors.naver_shopping import NaverShoppingCollector

    naver_id     = os.getenv("NAVER_CLIENT_ID")
    naver_secret = os.getenv("NAVER_CLIENT_SECRET")

    def _save(df: pd.DataFrame, source: str) -> None:
        try:
            save_raw(df, source=source)
        except ValueError as e:
            print(f"  ⚠️ {e}")

    # 1. 네이버 DataLab 수집 → 저장
    print("▶ 네이버 DataLab 수집 중...")
    datalab = NaverDataLabCollector(naver_id, naver_secret)
    rows = datalab.fetch_all()
    _save(pd.DataFrame(rows), source="naver_datalab")

    # 2. 구글 트렌드 수집 → 저장
    # print("▶ 구글 트렌드 수집 중...")
    # gtrends = GoogleTrendsCollector()
    # df_google = gtrends.fetch_archi_vs_competitors()
    # _save(pd.DataFrame(gtrends.parse_to_rows(df_google)), source="google_trends")

    # 3. 네이버 검색 수집 → 저장 (4개 테이블)
    print("▶ 네이버 검색 수집 중...")
    search = NaverSearchCollector(naver_id, naver_secret)
    search_result = search.fetch_all()
    _save(pd.DataFrame(search_result["total"]), source="mention_total")
    _save(pd.DataFrame(search_result["blog"]),  source="mention_blog")
    _save(pd.DataFrame(search_result["news"]),  source="mention_news")
    _save(pd.DataFrame(search_result["cafe"]),  source="mention_cafe")

    # 4. 쇼핑인사이트 수집 → 저장
    print("▶ 쇼핑인사이트 수집 중...")
    shopping = NaverShoppingCollector(naver_id, naver_secret)
    rows_shopping = shopping.fetch_all()
    _save(pd.DataFrame(rows_shopping), source="naver_shopping")

    # 5. 최신 파일 로드 확인
    print("\n▶ 저장된 파일 로드 확인")
    for source in ["naver_datalab", "mention_total", "mention_blog", "mention_news", "mention_cafe", "naver_shopping"]:
        df_check = load_latest(source)
        print(f"  {source}: {len(df_check)}행")