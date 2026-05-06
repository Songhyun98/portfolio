import psycopg2
import matplotlib.pyplot as plt
import os

def get_connection():
    return psycopg2.connect(
        host="127.0.0.1",
        port=5434,
        database="eventlog",
        user="postgres",
        password="postgres"
    )

def plot_event_type_count(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_type, COUNT(*) AS count
            FROM events
            GROUP BY event_type
            ORDER BY count DESC
        """)
        rows = cur.fetchall()

    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]

    plt.figure(figsize=(8, 5))
    plt.bar(labels, values, color=["#4CAF50", "#2196F3", "#F44336", "#FF9800"])
    plt.title("Event Type Count")
    plt.xlabel("Event Type")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig("charts/event_type_count.png")
    plt.close()
    print("event_type_count.png 저장 완료!")

def plot_event_type_ratio(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_type, COUNT(*) AS count
            FROM events
            GROUP BY event_type
        """)
        rows = cur.fetchall()

    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]

    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
    plt.title("Event Type Ratio")
    plt.tight_layout()
    plt.savefig("charts/event_type_ratio.png")
    plt.close()
    print("event_type_ratio.png 저장 완료!")

def plot_top_users(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT user_id, COUNT(*) AS total_events
            FROM events
            GROUP BY user_id
            ORDER BY total_events DESC
            LIMIT 10
        """)
        rows = cur.fetchall()

    labels = [f"user_{row[0]}" for row in rows]
    values = [row[1] for row in rows]

    plt.figure(figsize=(10, 5))
    plt.bar(labels, values, color="#2196F3")
    plt.title("Top 10 Users by Event Count")
    plt.xlabel("User ID")
    plt.ylabel("Total Events")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("charts/top_users.png")
    plt.close()
    print("top_users.png 저장 완료!")

def plot_page_count(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT page, COUNT(*) AS count
            FROM events
            GROUP BY page
            ORDER BY count DESC
        """)
        rows = cur.fetchall()

    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]

    plt.figure(figsize=(10, 5))
    plt.bar(labels, values, color="#FF9800")
    plt.title("Event Count by Page")
    plt.xlabel("Page")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("charts/page_count.png")
    plt.close()
    print("page_count.png 저장 완료!")

def plot_hourly_trend(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXTRACT(HOUR FROM created_at) AS hour, COUNT(*) AS count
            FROM events
            GROUP BY hour
            ORDER BY hour
        """)
        rows = cur.fetchall()

    labels = [f"{int(row[0])}:00" for row in rows]
    values = [row[1] for row in rows]

    plt.figure(figsize=(12, 5))
    plt.plot(labels, values, marker="o", color="#4CAF50")
    plt.title("Hourly Event Trend")
    plt.xlabel("Hour")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("charts/hourly_trend.png")
    plt.close()
    print("hourly_trend.png 저장 완료!")

if __name__ == "__main__":
    os.makedirs("charts", exist_ok=True)
    conn = get_connection()
    plot_event_type_count(conn)
    plot_event_type_ratio(conn)
    plot_top_users(conn)
    plot_page_count(conn)
    plot_hourly_trend(conn)
    conn.close()
    print("시각화 완료!")