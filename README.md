# 김송현 포트폴리오

데이터의 올바른 흐름을 만드는 엔지니어입니다.
수집부터 적재, 자동화까지 파이프라인 전체를 설계하고, 데이터로 비즈니스 문제를 해결하는 경험을 쌓아왔습니다.

---

## 데이터 엔지니어링

### [Steam 동시접속자 트렌드 파이프라인](./steam-pipeline)
> Docker · Airflow 기반 Steam 게임 동시접속자 자동 수집 및 이상 징후 탐지 파이프라인

- Steam Web API로 장르별 대표 게임 8개의 CCU 데이터를 수집하고 PostgreSQL에 적재하는 ETL 파이프라인 설계
- Apache Airflow를 Docker 환경에서 운영하며 매일 자동 수집되는 DAG 작성
- SQL 윈도우 함수(LAG)로 일일 변화율 계산 및 +112% 급등 이상 징후 포착
- `Python` `PostgreSQL` `Apache Airflow` `Docker`

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
| 데이터베이스 | PostgreSQL |
| 워크플로우 | Apache Airflow |
| 컨테이너 | Docker, Docker Compose |
| 데이터 처리 | Pandas, NumPy |
| 시각화 | Matplotlib |
