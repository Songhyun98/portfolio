import random
import time
import psycopg2
from datetime import datetime, timedelta

# DB 연결
def get_connection():
    return psycopg2.connect(
        host="db",
        database="eventlog",
        user="postgres",
        password="postgres"
    )

# 테이블 생성
def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          SERIAL PRIMARY KEY,
                event_type  VARCHAR(50) NOT NULL,
                user_id     INTEGER NOT NULL,
                session_id  VARCHAR(50) NOT NULL,
                page        VARCHAR(100),
                created_at  TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()

# 랜덤 타임스탬프 생성 (최근 7일 이내)
def random_timestamp():
    now = datetime.now()
    random_seconds = random.randint(0, 7 * 24 * 60 * 60)
    return now - timedelta(seconds=random_seconds)

# 이벤트 생성
def generate_session_events():
    session_id = f"sess_{random.randint(1000, 9999)}"
    user_id = random.randint(1, 100)
    events = []
    session_time = random_timestamp()

    def make_event(event_type, page):
        nonlocal session_time
        session_time += timedelta(seconds=random.randint(10, 300))
        return {
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "page": page,
            "created_at": session_time
        }

    # 각 페이지에서 다음 상태로 갈 확률
    transitions = {
        "/home": {
            "/lecture/python-basic": 0.25,
            "/lecture/data-engineering": 0.25,
            "/mypage": 0.2,
            "/cart": 0.1,
            "lecture_start": 0.05,
            "purchase": 0.05,
            "end": 0.1,
        },
        "/mypage": {
            "/home": 0.2,
            "/lecture/python-basic": 0.2,
            "/lecture/data-engineering": 0.2,
            "/cart": 0.2,
            "purchase": 0.1,
            "end": 0.1,
        },
        "/lecture/python-basic": {
            "/home": 0.1,
            "/lecture/data-engineering": 0.1,
            "/mypage": 0.1,
            "/cart": 0.1,
            "lecture_start": 0.4,
            "end": 0.2,
        },
        "/lecture/data-engineering": {
            "/home": 0.1,
            "/lecture/python-basic": 0.1,
            "/mypage": 0.1,
            "/cart": 0.1,
            "lecture_start": 0.4,
            "end": 0.2,
        },
        "/cart": {
            "/home": 0.2,
            "/lecture/python-basic": 0.1,
            "/lecture/data-engineering": 0.1,
            "/mypage": 0.1,
            "purchase": 0.4,
            "end": 0.1,
        },
        "lecture_start": {
            "/home": 0.1,
            "/cart": 0.4,
            "/mypage": 0.1,
            "/lecture/python-basic": 0.1,
            "/lecture/data-engineering": 0.1,
            "end": 0.2,
        },
        "purchase": {
            "/home": 0.4,
            "/lecture/python-basic": 0.2,
            "/lecture/data-engineering": 0.2,
            "/mypage": 0.1,
            "end": 0.1,
        },
    }

    # 항상 /home에서 시작
    current = "/home"
    events.append(make_event("page_view", current))

    for _ in range(20):  # 최대 20번 이동
        if current not in transitions:
            break

        # 다음 상태 확률로 결정
        next_states = list(transitions[current].keys())
        probs = list(transitions[current].values())
        current = random.choices(next_states, weights=probs, k=1)[0]

        if current == "end":
            break
        elif current == "purchase":
            # 이전 페이지가 /cart가 아닐 때만 /cart page_view 추가
            if events[-1]["page"] != "/cart":
                events.append(make_event("page_view", "/cart"))
            events.append(make_event("purchase", "/cart"))
        elif current == "lecture_start":
          # 이전 페이지가 강의 페이지가 아니면 강의 페이지 먼저 방문
          if not events[-1]["page"].startswith("/lecture"):
              lecture_page = random.choice(["/lecture/python-basic", "/lecture/data-engineering"])
              events.append(make_event("page_view", lecture_page))
          else:
              lecture_page = events[-1]["page"]
          events.append(make_event("lecture_start", lecture_page))
        else:
            events.append(make_event("page_view", current))

        # 10% 확률로 에러 발생 후 종료
        if random.random() < 0.1:
            events.append(make_event("error", events[-1]["page"]))
            break

    return events

# 이벤트 저장
def insert_event(conn, event):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO events (event_type, user_id, session_id, page, created_at)
            VALUES (%(event_type)s, %(user_id)s, %(session_id)s, %(page)s, %(created_at)s)
        """, event)
        conn.commit()

if __name__ == "__main__":
    print("DB 연결 대기 중...")
    for i in range(10):
        try:
            conn = get_connection()
            break
        except Exception:
            print(f"재시도 중... ({i+1}/10)")
            time.sleep(3)

    create_table(conn)
    print("이벤트 생성 시작!")

    total = 0
    while total < 500:
        events = generate_session_events()
        for event in events:
            insert_event(conn, event)
            total += 1
            print(f"[{total}] {event['event_type']} - user_{event['user_id']} - {event['session_id']}")

    conn.close()
    print("완료!")