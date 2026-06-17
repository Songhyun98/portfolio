# AkiiiMonitor — 아키클래식 브랜드 헬스 모니터링

🔗 **[Live Dashboard](https://akiiimonitor-drzwpg7oyhfdcsnrcmfujq.streamlit.app/)**

> 공개 데이터(검색량·소셜 언급량·쇼핑 클릭)로 아키클래식의 컴포트화 시장 건강도를 자동 진단하는 데이터 파이프라인

---

## 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **목적** | 아키클래식 브랜드의 시장 건강도를 공개 데이터로 주간 자동 진단 |
| **데이터 소스** | 네이버 DataLab, 네이버 검색 API, 네이버 쇼핑인사이트 |
| **수집 주기** | 매주 일요일 23:59 (KST) 자동 실행 |
| **저장소** | Supabase PostgreSQL |
| **역할** | 엔지니어(수집·적재) + 분석가(분석·시각화) |

---

## 아키텍처

```
[네이버 DataLab]     ──┐
[네이버 검색 API]    ──┤──→ collectors/ ──→ data/raw/ (parquet) ──→ Supabase DB
[네이버 쇼핑인사이트] ──┘

GitHub Actions (매주 일요일 23:59 KST)
└── db/storage.py (수집 → parquet 저장)
└── db/upload.py  (parquet → Supabase 적재)

Streamlit 대시보드 (akiiimonitor_app.py)
└── Supabase에서 직접 조회 → 지표 계산 → LLM 인사이트 생성/캐싱
```

---

## 폴더 구조

```
AkiiiMonitor/
├── collectors/
│   ├── base.py            # 공통 retry/timeout 유틸리티
│   ├── naver_datalab.py   # 검색어 트렌드 수집 (axis별)
│   ├── naver_search.py    # 블로그/뉴스/카페 언급량 수집
│   └── naver_shopping.py  # 쇼핑인사이트 수집 (성별×연령)
├── db/
│   ├── storage.py         # parquet 저장/로드
│   ├── upload.py          # Supabase 적재
│   ├── reader.py          # Supabase 읽기 (분석가용)
│   ├── schema.sql         # 테이블 생성 SQL
│   └── index.sql          # 인덱스 생성 SQL
├── .github/
│   └── workflows/
│       └── weekly_pipeline.yml  # GitHub Actions 자동화
├── data/
│   └── raw/               # 수집된 parquet 파일 (로컬 백업)
├── akiiimonitor_app.py     # Streamlit 대시보드
├── .env                    # API 키 (git 제외)
└── requirements.txt
```

---

## 데이터 소스 및 수집 전략

### 1. 네이버 DataLab (검색어 트렌드)
- **측정 대상**: 네이버 검색창 입력 횟수 (상대값 0~100)
- **기준**: 요청 내 전체 그룹 중 최고값 = 100
- **axis 설계**: 비교 목적에 따라 3개 요청으로 분리

| axis | 비교 대상 | 목적 |
|---|---|---|
| `direct` | 포즈간츠, 23.65 | 동급 브랜드 직접 비교 |
| `mass` | 스케쳐스, 휠라 | 대중 브랜드 대비 규모 |
| `market` | 컴포트수요지수, 여행시그널, 발건강시그널 | 시장 수요 트렌드 |

### 2. 네이버 검색 API (언급량)
- **측정 대상**: 블로그/뉴스/카페 총 문서 수 + 개별 문서
- **수집량**: 키워드당 최대 1000건 × 3개 소스
- **키워드**: `"아키클래식"`, `"포즈간츠"`, `"23.65"` (정확히 일치 검색)

### 3. 네이버 쇼핑인사이트
- **측정 대상**: 네이버쇼핑 클릭 트렌드 (상대값 0~100)
- **세분화**: 키워드 × 성별(m/f/all) × 연령(10s~60s+/all)
- **목적**: 키워드별 성별/연령 수요 분포 파악

---

## DB 스키마

### ERD

```
search_trend                    shopping_trend
─────────────────────           ──────────────────────────
period        DATE              period    DATE
keyword_group TEXT              keyword   TEXT
axis          TEXT              gender    TEXT
ratio         FLOAT             age       TEXT
                                ratio     FLOAT

mention_total                   mention_blog
─────────────────────           ──────────────────────────
collected_at  TIMESTAMPTZ       keyword      TEXT
collected_date DATE             title        TEXT
keyword       TEXT              description  TEXT
blog_total    INTEGER           bloggername  TEXT
news_total    INTEGER           postdate     TEXT
cafe_total    INTEGER           link         TEXT
                                collected_at TIMESTAMPTZ

mention_news                    mention_cafe
─────────────────────           ──────────────────────────
keyword       TEXT              keyword      TEXT
title         TEXT              title        TEXT
description   TEXT              description  TEXT
originallink  TEXT              cafename     TEXT
pub_date      TEXT              cafeurl      TEXT
link          TEXT              link         TEXT
collected_at  TIMESTAMPTZ       collected_at TIMESTAMPTZ

ai_insights
─────────────────────
cache_key     TEXT (PK)
asof_month    TEXT
insight_text  TEXT
generated_at  TIMESTAMPTZ
```

### 테이블별 적재 전략

| 테이블 | 전략 | 기준 키 | 이유 |
|---|---|---|---|
| `search_trend` | upsert | period + keyword_group + axis | 같은 주 데이터 덮어쓰기 |
| `shopping_trend` | upsert | period + keyword + gender + age | 같은 주 데이터 덮어쓰기 |
| `mention_total` | upsert | collected_date + keyword | 같은 날 중복 방지 |
| `mention_blog` | upsert | keyword + link | 같은 글 중복 방지 |
| `mention_news` | upsert | keyword + link | 같은 기사 중복 방지 |
| `mention_cafe` | upsert | keyword + link | 같은 글 중복 방지 |
| `ai_insights` | upsert | cache_key | 동일 입력값 조합당 1 row만 유지 |

### 인덱스 설계

카디널리티(값의 종류)가 높은 `period` 컬럼에만 인덱스를 설정했습니다. `keyword`, `axis`, `gender` 등 값의 종류가 적은 컬럼은 인덱스 효과가 없어 제외했습니다.

```sql
CREATE INDEX ON search_trend(period);
CREATE INDEX ON shopping_trend(period);
CREATE INDEX ON mention_total(collected_date);
CREATE INDEX ON mention_blog(postdate);
CREATE INDEX ON mention_news(pub_date);
```

---

## 시작하기

### 1. 환경 설정

```bash
pip install -r requirements.txt
```

`.env` 파일 생성:
```
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
SUPABASE_URL=...
SUPABASE_KEY=...
```

### 2. Supabase 테이블 생성

Supabase SQL Editor에서 순서대로 실행:
```
db/schema.sql
db/index.sql
```

### 3. 수동 실행

```bash
python db/storage.py   # 수집 → parquet 저장
python db/upload.py    # parquet → Supabase 적재
```

### 4. 자동화

GitHub Secrets에 환경변수 4개 등록 후 push하면 매주 일요일 23:59(KST) 자동 실행.

---

## 분석가용 데이터 접근

```python
from db.reader import SupabaseReader
from dotenv import load_dotenv
import os

load_dotenv()
reader = SupabaseReader(
    url=os.getenv("SUPABASE_URL"),
    key=os.getenv("SUPABASE_KEY"),
)

# 전체 읽기
df = reader.fetch_all("search_trend")

# 필터링
df_direct = reader.fetch_filtered("search_trend", {"axis": "direct"})
```

---

## 대시보드 & LLM 캐싱 전략

수집된 데이터는 Streamlit 대시보드(`akiiimonitor_app.py`)에서 시각화되며, 매월 마감 시점 데이터를 기반으로 LLM이 종합 소견(인사이트)을 생성합니다. LLM 호출은 비용이 발생하는 작업이므로, 동일한 데이터에 대한 중복 호출을 방지하기 위해 별도의 캐싱 레이어를 두었습니다.

### 완료월(ASOF) 컷오프

주간 데이터를 월간으로 리샘플링할 때, 집계가 진행 중인 당월은 통계 왜곡을 막기 위해 모든 지표 계산에서 자동 제외됩니다. 가장 최근 완료된 달을 `ASOF`로 잡고, 이 값을 모든 월별 지표(SoS, 모멘텀, 계절성 등)가 공유합니다.

### 캐시 키 설계 — ASOF가 아닌 입력값 해시

```
[search_trend 등 원본 데이터]
        ↓
[ASOF 결정] → 진행 중인 달 제외
        ↓
[지표 계산: 장기성장률, 3M YoY, SoS 등]
        ↓
[캐시 키 = 계산된 지표값들의 SHA256 해시]
        ↓
   ┌────┴────┐
 캐시 히트    캐시 미스 (또는 강제 재생성)
   ↓              ↓
 DB 조회만     LLM 호출 → Supabase upsert
(API 호출 0회)  (API 호출 1회)
```

`ASOF`(완료월) 하나만 캐시 키로 쓰면 같은 달 안에서 데이터가 정정·재수집되는 경우(드물지만 발생 가능)를 감지하지 못합니다. 대신 `ASOF`, SoS, 장기성장률, 3M 평활 YoY, 단일월 YoY, 최근 6개월 YoY 추이를 합쳐 해시를 생성합니다. 이 입력값 중 하나라도 바뀌면 해시가 달라져 자동으로 재생성되고, 변화가 없으면 항상 같은 해시로 캐시를 재사용합니다.

```python
def make_cache_key(asof_str, sos, m):
    yoy_trend_dict = {str(k): v for k, v in m["yoy_trend"].to_dict().items()}
    payload = {
        "asof": asof_str,
        "sos": round(sos, 2),
        "long": round(m["long"], 2),
        "yoy3": round(m["yoy3"], 2),
        "single_yoy": round(m["single_yoy"], 2),
        "yoy_trend": yoy_trend_dict,
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### `ai_insights` 테이블

```sql
create table ai_insights (
    cache_key text primary key,
    asof_month text,
    insight_text text,
    generated_at timestamptz
);
```

`cache_key`를 Primary Key로 두어 같은 입력값 조합에는 항상 단일 row만 존재하도록 했습니다(히스토리 누적이 아닌 upsert). 이 덕분에 조회 시 "여러 버전 중 무엇을 보여줄지" 판단할 필요 없이 항상 최신 1건만 가져오면 됩니다.

### 수동 트리거 + 강제 재생성

데이터 수집은 주 1회 자동화되어 있지만, 인사이트 생성은 분석가가 필요할 때 직접 트리거하는 방식으로 분리했습니다. 평소에는 해시 일치 시 캐시를 재사용하고, 데이터 재수집·정정이 의심될 때는 체크박스로 캐시를 무시하고 강제로 새로 생성할 수 있습니다.

```python
force = st.checkbox("강제 재생성 (데이터 재수집 시 체크)")
insight_text, was_generated = llm_insight(sos_now, ASOF.isoformat(), m, force=force)
st.caption("✅ 새로 생성됨" if was_generated else "📦 저장된 결과 재사용")
```

> **현재 상태**: `llm_insight`는 LLM이 생성한 해석을 그대로 반환하며, 위 캐싱 구조(동일 데이터 재호출 방지, 데이터 변경 시 자동 갱신, 수동 강제 갱신)가 적용되어 비용 효율적으로 운영되고 있습니다. 다만 출력 품질에 대한 체계적인 검증(`template_insight`와의 비교, 일관성 평가 등)은 아직 진행되지 않은 상태입니다.

---

## 설계 결정 기록

| 결정 | 이유 |
|---|---|
| parquet 로컬 저장 후 Supabase 적재 | raw 백업 보존 + DB 부하 분리 |
| axis별 DataLab 요청 분리 | 비교 목적이 다르면 같은 스케일로 비교 불가 |
| 쇼핑인사이트 키워드별 단독 요청 | API param 1개 제한 + 세그먼트별 독립 100 기준 |
| mention 계열 개별 문서 수집 | 감성 분석 등 텍스트 분석 확장 가능성 |
| collected_at 제거 (search/shopping) | period가 기준 시점 역할 → 중복 컬럼 제거 |
| 인덱스를 period에만 설정 | keyword/axis 등 카디널리티 낮은 컬럼은 효과 없음 |
| LLM 캐시 키 = ASOF가 아닌 입력값 해시 | ASOF만으로는 동일 월 내 데이터 정정·재수집을 감지 못함 |
| ai_insights 테이블에 upsert (히스토리 미보존) | cache_key당 1 row만 유지 → 조회 시 버전 판단 로직 불필요 |
| LLM 인사이트 생성을 수동 트리거로 분리 | 데이터 수집(주기)과 생성 시점(필요시)을 분리해 불필요한 API 비용 방지 |

---

## 분석 결과 활용

이 파이프라인이 수집·적재한 데이터는 분석가가 SoS(검색 점유율), SoV(언급 점유율), 계절성 지수 등 핵심 지표를 산출하는 데 활용되었습니다. 니치 마켓 검색 점유율 85.4%, 장기 성장률 +18% 등 구체적인 분석 결과와 방법론은 [Live Dashboard](https://akiiimonitor-jkb3nnfumu75enda2zjdmc.streamlit.app/)에서 확인할 수 있습니다.