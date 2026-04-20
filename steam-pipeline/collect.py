import requests
import psycopg2
from dotenv import load_dotenv
import os
from datetime import date

load_dotenv()

# 추적할 게임 목록
GAMES = {
    730:     "Counter-Strike 2",
    578080:  "PUBG",
    1172470: "Apex Legends",
    271590:  "GTA V",
    1623730: "Palworld",
    1599340: "Lost Ark",
    2073850: "The First Descendant",
    413150:  "Stardew Valley",
}

# DB 연결
conn = psycopg2.connect(
    host="localhost",
    database="steam_pipeline",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)
cursor = conn.cursor()

today = date.today()

for appid, name in GAMES.items():
    url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    response = requests.get(url, params={"appid": appid})
    data = response.json()

    ccu = data['response'].get('player_count', 0)
    print(f"{name}: {ccu:,}명")

    cursor.execute("""
        INSERT INTO steam_games (collected_at, appid, name, ccu)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (collected_at, appid) DO NOTHING
    """, (today, str(appid), name, ccu))

conn.commit()
cursor.close()
conn.close()

print(f"\n✅ {len(GAMES)}개 게임 수집 완료!")