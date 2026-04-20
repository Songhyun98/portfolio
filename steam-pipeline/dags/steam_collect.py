import os
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import psycopg2
from datetime import date

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

def collect_steam_data():
    conn = psycopg2.connect(
        host="172.20.240.1",
        database="steam_pipeline",
        user="postgres",
        password=os.getenv("DB_PASSWORD")
    )
    cursor = conn.cursor()
    today = date.today()

    for appid, name in GAMES.items():
        url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
        response = requests.get(url, params={"appid": appid})
        ccu = response.json()['response'].get('player_count', 0)

        cursor.execute("""
            INSERT INTO steam_games (collected_at, appid, name, ccu)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (collected_at, appid) DO NOTHING
        """, (today, str(appid), name, ccu))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 수집 완료!")

default_args = {
    'owner': 'songhyun',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='steam_daily_collect',
    default_args=default_args,
    start_date=datetime(2026, 4, 18),
    schedule_interval='0 3 * * *',
    catchup=False,
) as dag:

    collect = PythonOperator(
        task_id='collect_steam_data',
        python_callable=collect_steam_data,
    )