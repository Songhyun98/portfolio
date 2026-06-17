-- =============================================
-- 아키클래식 브랜드 헬스 DB 스키마
-- Supabase SQL Editor에서 순서대로 실행
-- =============================================

-- 1. 검색어 트렌드 (네이버 DataLab)
CREATE TABLE IF NOT EXISTS search_trend (
    id             SERIAL PRIMARY KEY,
    period         DATE        NOT NULL,
    keyword_group  TEXT        NOT NULL,
    axis           TEXT        NOT NULL,  -- direct / mass / market
    ratio          FLOAT       NOT NULL,
    UNIQUE (period, keyword_group, axis)
);

-- 2. 언급량 스냅샷
CREATE TABLE IF NOT EXISTS mention_total (
    id             SERIAL PRIMARY KEY,
    collected_at   TIMESTAMPTZ NOT NULL,
    collected_date DATE,                  -- 트리거로 자동 채워짐 (날짜 기준 중복 방지용)
    keyword        TEXT        NOT NULL,
    blog_total     INTEGER     NOT NULL,
    news_total     INTEGER     NOT NULL,
    cafe_total     INTEGER     NOT NULL,
    UNIQUE (collected_date, keyword)
);

-- collected_at 입력/수정 시 collected_date 자동 계산
CREATE OR REPLACE FUNCTION set_collected_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.collected_date := NEW.collected_at::date;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_collected_date
BEFORE INSERT OR UPDATE ON mention_total
FOR EACH ROW
EXECUTE FUNCTION set_collected_date();

-- 3. 블로그 개별 문서
CREATE TABLE IF NOT EXISTS mention_blog (
    id           SERIAL PRIMARY KEY,
    keyword      TEXT        NOT NULL,
    title        TEXT,
    description  TEXT,
    bloggername  TEXT,
    postdate     TEXT,
    link         TEXT,
    collected_at TIMESTAMPTZ NOT NULL,
    UNIQUE (keyword, link)
);

-- 4. 뉴스 개별 문서
CREATE TABLE IF NOT EXISTS mention_news (
    id            SERIAL PRIMARY KEY,
    keyword       TEXT        NOT NULL,
    title         TEXT,
    description   TEXT,
    originallink  TEXT,
    pub_date      TEXT,
    link          TEXT,
    collected_at  TIMESTAMPTZ NOT NULL,
    UNIQUE (keyword, link)
);

-- 5. 카페 개별 문서
CREATE TABLE IF NOT EXISTS mention_cafe (
    id           SERIAL PRIMARY KEY,
    keyword      TEXT        NOT NULL,
    title        TEXT,
    description  TEXT,
    cafename     TEXT,
    cafeurl      TEXT,
    link         TEXT,
    collected_at TIMESTAMPTZ NOT NULL,
    UNIQUE (keyword, link)
);

-- 6. 쇼핑인사이트
CREATE TABLE IF NOT EXISTS shopping_trend (
    id       SERIAL PRIMARY KEY,
    period   DATE        NOT NULL,
    keyword  TEXT        NOT NULL,
    gender   TEXT        NOT NULL,  -- m / f / all
    age      TEXT        NOT NULL,  -- 10s / 20s / ... / 60s+ / all
    ratio    FLOAT       NOT NULL,
    UNIQUE (period, keyword, gender, age)
);

-- 7. LLM 인사이트 캐시
CREATE TABLE IF NOT EXISTS ai_insights (
    cache_key     TEXT PRIMARY KEY,
    asof_month    TEXT,
    insight_text  TEXT,
    generated_at  TIMESTAMPTZ
);

-- =============================================
-- 권한 설정 (service_role 키로 업로드하므로 필요)
-- =============================================
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;