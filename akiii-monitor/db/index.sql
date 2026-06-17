-- =============================================
-- 인덱스 설계
-- 카디널리티가 높은 period/날짜 컬럼에만 설정
-- Supabase SQL Editor에서 실행
-- =============================================

CREATE INDEX IF NOT EXISTS idx_search_trend_period    ON search_trend(period);
CREATE INDEX IF NOT EXISTS idx_shopping_trend_period  ON shopping_trend(period);
CREATE INDEX IF NOT EXISTS idx_mention_total_date     ON mention_total(collected_date);
CREATE INDEX IF NOT EXISTS idx_mention_blog_postdate  ON mention_blog(postdate);
CREATE INDEX IF NOT EXISTS idx_mention_news_pub_date  ON mention_news(pub_date);