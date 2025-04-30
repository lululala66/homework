import openrouteservice
import folium

# 你的金鑰
client = openrouteservice.Client(key='5b3ce3597851110001cf62485955782916f3457e8356700f40cc7beb')

# 起點、終點座標 (經度, 緯度)
start = (120.68337,24.13785)  # 台中火車站
end = (120.677916, 24.141392)    # 繼光街166號附近

# 取得路線資料
routes = client.directions(
    coordinates=[start, end],
    profile='foot-walking',  # 腳踏車模式
    format='geojson'
)

# 提取真實路徑距離（公尺）
distance = routes['features'][0]['properties']['summary']['distance']
duration = routes['features'][0]['properties']['summary']['duration']

print(f"真實道路距離: {distance/1000:.2f} 公里")
print(f"預估需要時間: {duration/60:.1f} 分鐘")

# 🎯 建立 folium 地圖，中心在起點
m = folium.Map(location=[start[1], start[0]], zoom_start=16)

# 🎯 畫路線
folium.GeoJson(routes, name='route').add_to(m)

# 🎯 標記起點
folium.Marker(
    location=[start[1], start[0]],
    popup='起點：綠川東街/中山路口(東側)',
    icon=folium.Icon(color='green')
).add_to(m)

# 🎯 標記終點
folium.Marker(
    location=[end[1], end[0]],
    popup='終點：繼光街166號附近',
    icon=folium.Icon(color='red')
).add_to(m)

# 🎯 把地圖存成 HTML 檔
m.save('route_map.html')
print("地圖已經儲存成 route_map.html，打開看看吧！")
