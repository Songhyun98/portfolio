# 김송현 포트폴리오

데이터의 올바른 흐름을 만드는 엔지니어입니다.
수집부터 적재, 자동화까지 파이프라인 전체를 설계하고, 데이터로 비즈니스 문제를 해결하는 경험을 쌓아왔습니다.

---

## 데이터 엔지니어링

### [AkiiiMonitor — 브랜드 헬스 모니터링 파이프라인](./AkiiiMonitor) 🔗 [Live Dashboard](https://akiiimonitor-drzwpg7oyhfdcsnrcmfujq.streamlit.app/)
> 네이버 Open API 기반 브랜드 검색·언급·쇼핑 트렌드 수집 및 자동 적재 파이프라인, 분석가와 협업해 Streamlit 대시보드까지 배포

- 네이버 DataLab·검색·쇼핑인사이트 3개 API를 활용해 axis(동급/대중/시장)별, 세그먼트(성별·연령)별로 데이터 수집 구조 설계
- 페이지네이션으로 키워드당 최대 1000건 언급 문서 수집, 공통 retry/timeout 모듈로 4개 수집기 안정성 통일
- Supabase PostgreSQL에 upsert 전략 적용해 중복 없이 주간 데이터 갱신, 카디널리티 기반으로 인덱스 설계
- GitHub Actions로 매주 자동 수집·적재 파이프라인 구축, 1000행 응답 제한을 페이지네이션으로 우회하는 분석가용 조회 모듈 제공
- LLM 인사이트 생성에 SHA256 해시 기반 캐싱 적용해 동일 데이터 재호출 방지, 강제 재생성 옵션으로 유연성 확보
- `Python` `PostgreSQL(Supabase)` `GitHub Actions` `Streamlit` `Pandas`

### [Steam 동시접속자 트렌드 파이프라인](./steam-pipeline)
> Docker · Airflow 기반 Steam 게임 동시접속자 자동 수집 및 이상 징후 탐지 파이프라인

- Steam Web API로 장르별 대표 게임 8개의 CCU 데이터를 수집하고 PostgreSQL에 적재하는 ETL 파이프라인 설계
- Apache Airflow를 Docker 환경에서 운영하며 매일 자동 수집되는 DAG 작성
- SQL 윈도우 함수(LAG)로 일일 변화율 계산 및 +112% 급등 이상 징후 포착
- `Python` `PostgreSQL` `Apache Airflow` `Docker`

### [이벤트 로그 파이프라인](./event-log-pipeline)
> State Machine 기반 유저 행동 시뮬레이션 및 데이터 파이프라인 구축

- 온라인 강의 플랫폼의 유저 행동을 State Machine으로 모델링해 현실적인 이벤트 데이터 생성
- Docker Compose로 PostgreSQL + 이벤트 생성기를 단일 명령으로 실행 가능한 환경 구성
- SQL 집계 쿼리 5개 작성 및 matplotlib으로 시각화 차트 5개 생성
- Kubernetes Deployment/ConfigMap manifest 작성 및 AWS 아키텍처 설계
- `Python` `PostgreSQL` `Docker` `Kubernetes` `AWS`

### [데이터 기반 보고서 생성 자동화](./data_driven_report_generation_automation)
> Python · SQL · Jinja2 기반 광고 성과 보고서 자동화 파이프라인 구축

- 파라미터 설정만으로 데이터 추출부터 PDF 보고서 생성까지 전체 파이프라인 자동 실행
- PostgreSQL 2개 DB 연결 및 SQL 추출 함수 모듈화, 10개 이상 지표 자동 산출
- 리포트 생성 시간 90% 이상 단축
- `Python` `PostgreSQL` `Jinja2` `Matplotlib` `Playwright`

---

## 데이터 분석

### [데이터 기반 유통 재고관리: 수요-공급 연계 예측 모델](./demand_supply_forecasting_model_report.pdf)
식료품 유통 수요·공급 예측 모델 개발, 최소 오차율 SMAPE 8.29% 달성

### [SNS 앱 리텐션 강화 전략](./sns_app_retention_enhancement_strategy.pdf)
사용자 로그 데이터 및 네트워크 분석 기반 DAU 회복 전략 제안

### [회원 행동 분석을 통한 구독회원 확대 전략](./subscription_growth_strategy_based_on_member_behavior_analysis.pdf)
퍼널 분석, RFM 세그먼트 기반 구독 전환율 개선 전략 제안

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python, SQL |
| 데이터베이스 | PostgreSQL, Supabase |
| 워크플로우 | Apache Airflow, GitHub Actions |
| 컨테이너 | Docker, Docker Compose |
| 데이터 처리 | Pandas, NumPy |
| 시각화 | Matplotlib, Streamlit |
| 클라우드 | AWS S3 |