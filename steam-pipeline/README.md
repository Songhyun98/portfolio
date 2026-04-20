# Steam Daily CCU Pipeline

Steam 인기 게임의 동시접속자(CCU) 데이터를 매일 자동 수집하고, 트렌드를 분석하는 데이터 파이프라인입니다.

---

## 프로젝트 개요

Steam 플랫폼의 장르별 대표 게임 8개를 선정하여 매일 동시접속자 수를 수집하고 PostgreSQL에 적재합니다.
시계열 데이터를 분석하여 패치, 업데이트, 이벤트가 게임 유저 트렌드에 미치는 영향을 파악합니다.

---

## 아키텍처

```
Steam API → Python ETL → Airflow (매일 자동 실행) → PostgreSQL → SQL 분석
```

```
[내 컴퓨터]
├── PostgreSQL (steam_pipeline DB)
└── Docker
    ├── Airflow Webserver (포트 8080)
    ├── Airflow Scheduler
    └── PostgreSQL (Airflow 전용 DB, 포트 5433)
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| 데이터베이스 | PostgreSQL 18 |
| 워크플로우 | Apache Airflow 2.8.0 |
| 컨테이너 | Docker, Docker Compose |
| 데이터 소스 | Steam Web API |
| 버전 관리 | Git |

---

## 수집 대상 게임

| 장르 | 게임 |
|------|------|
| FPS | Counter-Strike 2 |
| 배틀로얄 | PUBG |
| 배틀로얄 | Apex Legends |
| 오픈월드 | GTA V |
| 서바이벌 | Palworld |
| MMORPG | Lost Ark |
| 넥슨 | The First Descendant |
| 인디 | Stardew Valley |

---

## DB 테이블 구조

```sql
CREATE TABLE steam_games (
    id SERIAL PRIMARY KEY,
    collected_at DATE NOT NULL,
    appid VARCHAR(20),
    name VARCHAR(200),
    ccu INT,
    CONSTRAINT unique_game_per_day UNIQUE (collected_at, appid)
);
```

---

## 분석 쿼리 예시

### 게임별 일일 동접자 변화율 (%)
```sql
SELECT 
    name,
    collected_at,
    ccu,
    ROUND(
        (ccu - LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at)) * 100.0 
        / NULLIF(LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at), 0), 1
    ) AS change_pct
FROM steam_games
ORDER BY name, collected_at;
```

### 급등/급락 이상 징후 탐지 (Top 10)
```sql
SELECT 
    name,
    collected_at,
    ccu,
    ROUND(
        (ccu - LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at)) * 100.0 
        / NULLIF(LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at), 0), 1
    ) AS change_pct
FROM steam_games
ORDER BY ABS(
    ROUND(
        (ccu - LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at)) * 100.0 
        / NULLIF(LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at), 0), 1
    )
) DESC NULLS LAST
LIMIT 10;
```

---

## 분석 인사이트 (수집 중)

> 데이터 누적에 따라 지속 업데이트 예정

- **The First Descendant**: 특정 날짜 +112.6% 급등 포착 → 업데이트/이벤트 영향 추정
- **PUBG**: 주말 효과로 평일 대비 동접자 최대 +36.8% 상승
- **Palworld**: 꾸준한 상승세 유지 중

---

## 실행 방법

### 사전 준비
```bash
# 1. 레포 클론
git clone https://github.com/Songhyun98/portfolio.git

# 2. steam-pipeline 폴더로 이동
cd portfolio/steam-pipeline

# 3. 가상환경 생성 및 활성화
python -m venv venv
source venv/Scripts/activate  # Windows

# 4. 라이브러리 설치
pip install requests python-dotenv psycopg2-binary
```

### 환경변수 설정
`.env` 파일 생성 후 아래 내용 입력
```
DB_PASSWORD=PostgreSQL_비밀번호
```

### Docker 실행
```bash
docker-compose up -d
```

### 수동 수집
```bash
python collect.py
```

---

## 프로젝트 구조

```
steam-pipeline/
├── dags/
│   └── steam_collect.py     # Airflow DAG
├── analysis/
│   └── trend_queries.sql    # 분석 쿼리 모음
├── collect.py               # 수동 수집 스크립트
├── docker-compose.yml       # Airflow + PostgreSQL 컨테이너 설정
├── .env                     # 환경변수 (Git 제외)
└── README.md
```
