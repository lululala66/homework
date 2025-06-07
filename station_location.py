import time
import schedule
from datetime import datetime, timedelta
import requests
import mysql.connector

def fetch_and_store_data():
    now = datetime.now()
    print(f"🚀 開始執行：{now}")
    
    # 抓取資料
    url = "https://datacenter.taichung.gov.tw/swagger/OpenData/b87c286d-0dce-4094-b34d-6935f3813539"
    response = requests.get(url)
    data = response.json()

    # 建立資料庫連線
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="lululala",
        database="youbike_data",
        port=3306,
    )
    cursor = conn.cursor()

    # 處理資料
    stations = data["retVal"]

    if isinstance(stations, list):
        for station in stations:
            city = station.get("scity", "未知城市")
            district = station.get("sarea", "未知區域")
            station_name = station.get("ar", "未知站點")
            lat = float(station.get("lat", 0))
            lon = float(station.get("lng", 0))
            act = int(station.get("act", 0))

            try:
                cursor.execute("""
                    INSERT IGNORE INTO Taichung_station_locations (city, district, station_name, record_time, latitude, longitude, act)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (city, district, station_name, now, lat, lon, act))
                print(f"✅ 成功寫入資料: {station_name}")
            except Exception as e:
                print(f"❌ 寫入失敗: {e}")
    else:
        print("❌ stations 資料結構不是列表，請檢查 API 回應內容")

    # 清除8天前的資料
    eight_days_ago = now - timedelta(days=8)
    try:
        cursor.execute("""
            DELETE FROM Taichung_station_locations
            WHERE record_time < %s
        """, (eight_days_ago,))
        print(f"🧹 清除 Taichung_station_locations 舊資料，共 {cursor.rowcount} 筆")
    except Exception as e:
        print(f"❌ 清除舊資料失敗: {e}")

    # 提交並關閉資料庫連線
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 資料匯入與清理完成！\n")

# 設定每天早上9點和晚上9點執行一次的排程
schedule.every().day.at("09:00").do(fetch_and_store_data)
schedule.every().day.at("21:00").do(fetch_and_store_data)

# 進入排程檢查狀態
while True:
    schedule.run_pending()
    time.sleep(1)
