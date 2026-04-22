# 데이터 기반 보고서 생성 자동화
**Python · SQL · Jinja2 기반 광고 성과 보고서 자동화 파이프라인 구축**

---

## 프로젝트 개요
target_id, 분석 기간, 타겟 연령/성별 등 파라미터 설정만으로 데이터 추출부터 PDF 보고서 생성까지 전체 파이프라인이 자동 실행되는 구조를 설계 및 구현했습니다.

> 본 프로젝트는 실무 인턴십에서 진행한 작업으로, 코드는 보안상 공개하지 않습니다.
---

## 아키텍처

```
config 파라미터 입력
    ↓
processor.py (SQL 쿼리) → integrated_report.json
    ↓
visualizer.py (SVG 차트 생성)
    ↓
reporter.py (Jinja2 → HTML)
    ↓
Playwright (HTML → PDF)
```

---

## 구현 내용
- PostgreSQL 2개 DB(분석 DB, 서비스 DB) 연결 및 SQL 추출 함수 모듈화
- CTR 추이, 오가닉 조회수, 팔로워, 키워드 성과 등 10개 이상 지표 자동 산출
- Kiwi 형태소 분석기로 키워드를 명사/동형용사로 분리하고 키워드 조합(A+B)별 CTR 분석
- line, bar, heatmap, bubble 등 6가지 차트 타입을 SVG로 렌더링
- Jinja2 템플릿과 결합하여 HTML 보고서 자동 생성 후 Playwright로 PDF 변환
- 수동 작업 구조를 파라미터 기반 실행 구조로 전환하여 리포트 생성 시간 90% 이상 단축

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python |
| 데이터베이스 | PostgreSQL, SQLAlchemy |
| 데이터 처리 | Pandas, NumPy |
| 시각화 | Matplotlib |
| 보고서 생성 | Jinja2, HTML/CSS, Playwright |
| 형태소 분석 | Kiwi |
