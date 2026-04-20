-- ============================================
-- Steam 동접자 트렌드 분석 쿼리
-- 프로젝트: Steam Daily CCU Pipeline
-- 작성자: 송현
-- ============================================


-- 1. 전체 데이터 확인
-- 날짜별 수집된 게임 수 확인
SELECT 
    collected_at, 
    COUNT(*) AS game_count
FROM steam_games 
GROUP BY collected_at 
ORDER BY collected_at;


-- 2. 게임별 일일 동접자 절대 변화량
-- 어제 대비 동접자가 얼마나 늘었는지/줄었는지
SELECT 
    name,
    collected_at,
    ccu,
    LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at) AS prev_ccu,
    ccu - LAG(ccu) OVER (PARTITION BY appid ORDER BY collected_at) AS diff
FROM steam_games
ORDER BY name, collected_at;


-- 3. 게임별 일일 동접자 변화율 (%)
-- 퍼센트로 보면 규모가 다른 게임끼리도 비교 가능
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


-- 4. 특정 날짜 기준 게임별 동접자 순위
-- 원하는 날짜로 바꿔서 사용
SELECT 
    name,
    ccu,
    RANK() OVER (ORDER BY ccu DESC) AS ranking
FROM steam_games
WHERE collected_at = '2026-04-19'
ORDER BY ranking;


-- 5. 게임별 전체 기간 평균 동접자
SELECT 
    name,
    ROUND(AVG(ccu)) AS avg_ccu,
    MAX(ccu) AS max_ccu,
    MIN(ccu) AS min_ccu
FROM steam_games
GROUP BY name
ORDER BY avg_ccu DESC;


-- 6. 일별 변화율 급등/급락 포착
-- 변화율 절댓값 기준으로 이상 징후 탐지
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