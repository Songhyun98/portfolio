-- 1. 이벤트 타입별 발생 횟수
SELECT event_type, COUNT(*) AS count
FROM events
GROUP BY event_type
ORDER BY count DESC;

-- 2. 유저별 총 이벤트 수 (상위 10명)
SELECT user_id, COUNT(*) AS total_events
FROM events
GROUP BY user_id
ORDER BY total_events DESC
LIMIT 10;

-- 3. 페이지별 이벤트 발생 횟수
SELECT page, COUNT(*) AS count
FROM events
GROUP BY page
ORDER BY count DESC;

-- 4. 에러 이벤트 비율
SELECT 
    ROUND(COUNT(*) FILTER (WHERE event_type = 'error') * 100.0 / COUNT(*), 2) AS error_rate
FROM events;

-- 5. 시간대별 이벤트 추이
SELECT EXTRACT(HOUR FROM created_at) AS hour, COUNT(*) AS count
FROM events
GROUP BY hour
ORDER BY hour;