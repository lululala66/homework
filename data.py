import mysql.connector
import pandas as pd
from datetime import timedelta

# 連線
conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="lululala",
    database="youbike_data",
    port=3306,
)

# 抓 act=0 的記錄（近 7.5 天內）
query_act = """
    SELECT station_name, record_time AS act_time
    FROM Taichung_station_locations
    WHERE act = 0 
    AND record_time > NOW() - INTERVAL 7.5 DAY
"""
df_act0 = pd.read_sql(query_act, conn)

# 抓主資料（近 7 天）
query_main = """
    SELECT station_name, record_time, bikes_available, docks_available
    FROM Taichung_youbike_data
    WHERE record_time > NOW() - INTERVAL 7 DAY
"""
df_main = pd.read_sql(query_main, conn)

conn.close()

# 加上 act 前 12 小時的開始時間
df_act0["start_time"] = df_act0["act_time"] - timedelta(hours=12)

# 合併
df_joined = df_main.merge(df_act0, on="station_name", how="left")

# 過濾：排除在不良時間內的資料
mask = (df_joined["record_time"] >= df_joined["start_time"]) & (df_joined["record_time"] < df_joined["act_time"])
df_filtered = df_joined[~mask | df_joined["act_time"].isna()]

# 正規化可借、可還
total = df_filtered["bikes_available"] + df_filtered["docks_available"]
df_filtered["normalized_available_bikes"] = df_filtered["bikes_available"] / total
df_filtered["normalized_docks_available"] = df_filtered["docks_available"] / total

# 🔹 每站加總正規化值
df_summary = df_filtered.groupby("station_name")[[
    "normalized_available_bikes", "normalized_docks_available"
]].sum().reset_index()

# 🔹 對加總值再次正規化
df_summary["final_normalized_available"] = df_summary["normalized_available_bikes"] / (
    df_summary["normalized_available_bikes"] + df_summary["normalized_docks_available"]
)
df_summary["final_normalized_docks"] = df_summary["normalized_docks_available"] / (
    df_summary["normalized_available_bikes"] + df_summary["normalized_docks_available"]
)

# 顯示結果
print(df_summary[[
    "station_name", "final_normalized_available", "final_normalized_docks"
]])

# 所有站的平均比例
mean_available = df_summary["final_normalized_available"].mean()
mean_docks = df_summary["final_normalized_docks"].mean()

print("全站平均：")
print(f"平均可借比例：{mean_available:.3f}")
print(f"平均可還比例：{mean_docks:.3f}")
