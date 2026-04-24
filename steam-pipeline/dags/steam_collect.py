import os
import json
import boto3
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
    today = date.today()
    raw_data = []

    # Steam API 수집
    for appid, name in GAMES.items():
        url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
        response = requests.get(url, params={"appid": appid})
        ccu = response.json()['response'].get('player_count', 0)
        raw_data.append({
            "appid": str(appid),
            "name": name,
            "ccu": ccu,
            "collected_at": str(today)
        })

    # S3에 원본 JSON 저장
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="ap-northeast-2"
    )
    s3.put_object(
        Bucket=os.getenv("AWS_BUCKET_NAME"),
        Key=f"raw/{today}/ccu_data.json",
        Body=json.dumps(raw_data, ensure_ascii=False)
    )
    print(f"✅ S3 저장 완료: raw/{today}/ccu_data.json")

    # PostgreSQL 적재
    conn = psycopg2.connect(
        host="172.20.240.1",
        database="steam_pipeline",
        user="postgres",
        password=os.getenv("DB_PASSWORD")
    )
    cursor = conn.cursor()

    for item in raw_data:
        cursor.execute("""
            INSERT INTO steam_games (collected_at, appid, name, ccu)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (collected_at, appid) DO NOTHING
        """, (today, item["appid"], item["name"], item["ccu"]))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ PostgreSQL 적재 완료!")

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