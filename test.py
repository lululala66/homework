import mysql.connector

# 建立資料庫連線
conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="lululala",
    database="youbike_data",
    port=3306
)

cursor = conn.cursor()

# 相同的站名數量
cursor.execute("""
SELECT COUNT(*) FROM (
    SELECT DISTINCT REPLACE(y.station_name, '/', '') AS name
    FROM Taichung_youbike_data y
    INNER JOIN Taichung_station_locations l
    ON REPLACE(y.station_name, '/', '') = REPLACE(l.station_name, '/', '')
) AS same;
""")
same_count = cursor.fetchone()[0]

# youbike 多出來的站名數
cursor.execute("""
SELECT COUNT(*) FROM (
    SELECT DISTINCT REPLACE(station_name, '/', '') AS name FROM Taichung_youbike_data
    WHERE REPLACE(station_name, '/', '') NOT IN (
        SELECT REPLACE(station_name, '/', '') FROM Taichung_station_locations
    )
) AS diff1;
""")
youbike_extra = cursor.fetchone()[0]

# station_locations 多出來的站名數
cursor.execute("""
SELECT COUNT(*) FROM (
    SELECT DISTINCT REPLACE(station_name, '/', '') AS name FROM Taichung_station_locations
    WHERE REPLACE(station_name, '/', '') NOT IN (
        SELECT REPLACE(station_name, '/', '') FROM Taichung_youbike_data
    )
) AS diff2;
""")
station_extra = cursor.fetchone()[0]

# 顯示比對結果
print(f"✅ 相同的站名數量: {same_count}")
print(f"🔴 youbike 多出來的站名數量: {youbike_extra}")
print(f"🔵 station_locations 多出來的站名數量: {station_extra}")

# 關閉連線
cursor.close()
conn.close()
