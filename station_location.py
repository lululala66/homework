import time
from datetime import datetime

while True:
    print(f"🚀 開始執行：{datetime.now()}")

    # === 你的原始程式碼貼在這裡（縮排） ===
    import requests
    import mysql.connector

    url = "https://datacenter.taichung.gov.tw/swagger/OpenData/34a848ab-eeb3-44fd-a842-a09cb3209a7d"
    response = requests.get(url)
    data = response.json()

    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="lululala",
        database="youbike_data",
        port=3306,
    )
    cursor = conn.cursor()

    stations = data["retVal"]

    if isinstance(stations, list):
        for station in stations:
            city = station.get("scity", "未知城市")
            district = station.get("sarea", "未知區域")
            station_name = station.get("ar", "未知站點")
            lat = float(station.get("lat", 0))
            lon = float(station.get("lng", 0))
            act = int(station.get("act", 0))
        now = datetime.now()
        try:
            cursor.execute("""
                INSERT IGNORE INTO Taichung_station_locations (city, district, station_name, record_time, latitude, longitude, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (city, district, station_name, now, lat, lon, act))
            print(f"✅ 成功寫入資料: {station_name}")
        except Exception as e:
                print(f"❌ 寫入失敗: {e}")
    else:
        print("❌ stations 資料結構不是列表，請檢查 API 回應內容")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 資料匯入完成！")

    # === 休眠 12 小時（43200 秒）===
    print("🕒 休眠 12 小時...")
    time.sleep(43200)
