from flask import Flask, render_template, request, jsonify
import mysql.connector
import requests
from geopy.distance import geodesic
from math import radians, cos, sin, sqrt, atan2

app = Flask(__name__)

ORS_API_KEY = "5b3ce3597851110001cf62485955782916f3457e8356700f40cc7beb"

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="lululala",
        database="youbike_data",
        port=3306
    )

@app.route("/")
def index():
    city = request.args.get("city", "臺中市")
    selected_districts = request.args.getlist("district")
    search_station = request.args.get("station")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 城市與區域選單準備
    cursor.execute("SELECT DISTINCT city FROM Taichung_youbike_data")
    all_cities = sorted([row['city'] for row in cursor.fetchall()])

    cursor.execute("SELECT DISTINCT district FROM Taichung_youbike_data WHERE city = %s", (city,))
    all_districts = sorted([row['district'] for row in cursor.fetchall()])

    data = []
    if search_station:
        cursor.execute("""
            SELECT t.city, t.district, t.station_name, t.bikes_available, t.docks_available
            FROM Taichung_youbike_data t
            INNER JOIN (
                SELECT station_name, MAX(record_time) AS latest_time
                FROM Taichung_youbike_data
                WHERE station_name = %s
                GROUP BY station_name
            ) latest
            ON t.station_name = latest.station_name AND t.record_time = latest.latest_time
        """, (search_station,))
        data = cursor.fetchall()

    elif selected_districts:
        format_strings = ','.join(['%s'] * len(selected_districts))
        cursor.execute(f"""
            SELECT t.city, t.district, t.station_name, t.bikes_available, t.docks_available
            FROM Taichung_youbike_data t
            INNER JOIN (
                SELECT station_name, MAX(record_time) AS latest_time
                FROM Taichung_youbike_data
                WHERE city = %s AND district IN ({format_strings})
                GROUP BY station_name
            ) latest
            ON t.station_name = latest.station_name AND t.record_time = latest.latest_time
            WHERE t.city = %s AND t.district IN ({format_strings})
            ORDER BY t.station_name
        """, [city] + selected_districts + [city] + selected_districts)
        data = cursor.fetchall()

    conn.close()
    return render_template("index.html", cities=all_cities, city=city, districts=all_districts, selected=selected_districts, stations=data)

@app.route("/search")
def search():
    keyword = request.args.get("q", "")
    city = request.args.get("city", "臺中市")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT station_name
        FROM Taichung_youbike_data
        WHERE city = %s AND station_name LIKE %s
        ORDER BY station_name
        LIMIT 10
    """, (city, f"%{keyword}%",))
    matches = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify({"suggestions": matches})

@app.route("/route")
def route():
    start = request.args.get("start")
    end = request.args.get("end")
    user_lat = float(request.args.get("user_lat"))
    user_lng = float(request.args.get("user_lng"))

    def geocode_osm(address):
        try:
            res = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "tw"},
                headers={"User-Agent": "YouBikeTaichung/1.0"},
                timeout=10
            )
            if res.status_code == 200 and res.json():
                return res.json()[0]
            return None
        except Exception as e:
            print(f"Geocode error: {e}")
            return None

    def find_nearest_station(lat, lng):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT station_name, latitude, longitude
            FROM Taichung_station_locations
            WHERE act = '1'
        """)
        stations = cursor.fetchall()
        conn.close()
        for s in stations:
            s["latitude"] = float(s["latitude"])
            s["longitude"] = float(s["longitude"])
        stations = sorted(
            stations,
            key=lambda s: geodesic((lat, lng), (s['latitude'], s['longitude'])).meters
        )
        return stations[0] if stations else None

    def ors_route(start, end):
        # 防呆
        for v in start + end:
            if not isinstance(v, (int, float)):
                print(f"[ERROR] ORS 參數型別錯誤: {v} ({type(v)})")
                return None
            if not (23 <= v <= 25 or 120 <= v <= 122):
                print(f"[ERROR] ORS 參數超出台灣範圍: {v}")
                return None
        if None in start or None in end or 0 in start or 0 in end:
            print(f"[ERROR] ORS 參數異常: start={start}, end={end}")
            return None
        if start == end:
            print(f"[ERROR] ORS 起訖點相同: {start}")
            return None
        print(f"[ORS DEBUG] start={start}, end={end}")
        try:
            res = requests.post(
                "https://api.openrouteservice.org/v2/directions/foot-walking",
                headers={"Authorization": ORS_API_KEY, "Content-Type": "application/json"},
                json={
                    "coordinates": [start, end],
                    "radiuses": [1000, 1000],
                    "instructions": True,
                    "geometry": True
                },
                timeout=15
            )
            print(f"[ORS DEBUG] status={res.status_code}, text={res.text}")
            if res.status_code != 200:
                print(f"ORS API 錯誤 ({res.status_code}): {res.text}")
                return None
            return res.json()
        except Exception as e:
            print(f"ORS error: {e}")
            return None

    start_loc = geocode_osm(start)
    end_loc = geocode_osm(end)

    if not start_loc or not end_loc:
        return jsonify({"error": "地址無法轉換為座標"}), 400

    start_coord = (float(start_loc['lat']), float(start_loc['lon']))
    end_coord = (float(end_loc['lat']), float(end_loc['lon']))

    borrow_station = find_nearest_station(user_lat, user_lng)
    return_station = find_nearest_station(end_coord[0], end_coord[1])

    # 防呆：借還站點不可重複
    if not borrow_station or not return_station or (
        borrow_station['latitude'] == return_station['latitude'] and
        borrow_station['longitude'] == return_station['longitude']
    ):
        return jsonify({"error": "附近無可用站點或借還站點重複，無法規劃路線"}), 400

    # 強制轉 float
    b_lng = float(borrow_station['longitude'])
    b_lat = float(borrow_station['latitude'])
    r_lng = float(return_station['longitude'])
    r_lat = float(return_station['latitude'])
    e_lng = float(end_coord[1])
    e_lat = float(end_coord[0])

    print(f"[DEBUG] path1: {[user_lng, user_lat]} -> {[b_lng, b_lat]}")
    print(f"[DEBUG] path2: {[b_lng, b_lat]} -> {[r_lng, r_lat]}")
    print(f"[DEBUG] path3: {[r_lng, r_lat]} -> {[e_lng, e_lat]}")

    path1 = ors_route([user_lng, user_lat], [b_lng, b_lat])
    if not path1:
        print("[ERROR] path1 規劃失敗")
    path2 = ors_route([b_lng, b_lat], [r_lng, r_lat])
    if not path2:
        print("[ERROR] path2 規劃失敗")
    path3 = ors_route([r_lng, r_lat], [e_lng, e_lat])
    if not path3:
        print("[ERROR] path3 規劃失敗")

    if not path1 or not path2 or not path3:
        return jsonify({"error": "ORS API 路線規劃失敗，請檢查座標或稍後再試"}), 500

    return jsonify({
        "borrow": borrow_station,
        "return": return_station,
        "routes": {
            "walk1": path1,
            "bike": path2,
            "walk2": path3
        }
    })

# 計算兩點距離的 haversine 函式
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # 地球半徑 (km)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # 回傳公尺

@app.route("/nearest_station")
def nearest_station_api():
    lat = float(request.args.get("lat"))
    lng = float(request.args.get("lng"))

    if not (23.8 <= lat <= 24.4 and 120.4 <= lng <= 121.0):
        print(f"error：lat={lat}, lng={lng}")
        return jsonify({"error": "查無有效座標"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT station_name, latitude, longitude
        FROM Taichung_station_locations 
        WHERE act = '1'
    """)
    stations = cursor.fetchall()
    conn.close()

    # 強制型別轉換
    for s in stations:
        s["latitude"] = float(s["latitude"])
        s["longitude"] = float(s["longitude"])

    MAX_DISTANCE = 5000
    stations = [
        s for s in stations
        if s["latitude"] is not None and s["longitude"] is not None
        and geodesic((lat, lng), (s['latitude'], s['longitude'])).meters <= MAX_DISTANCE
    ]
    if not stations:
        print("[錯誤] 無符合距離閾值的站點")
        return jsonify({"error": "無符合距離的站點"}), 404

    stations = sorted(
        stations,
        key=lambda s: geodesic((lat, lng), (s['latitude'], s['longitude'])).meters
    )
    nearest = stations[0]
    distance = int(geodesic((lat, lng), (nearest['latitude'], nearest['longitude'])).meters)
    print(f"[Debug] 最近站點：{nearest['station_name']}, 距離：{distance} 公尺")
    return jsonify({
        "station_name": nearest["station_name"],
        "lat": nearest["latitude"],
        "lng": nearest["longitude"],
        "distance": distance
    })

if __name__ == "__main__":
    app.run(debug=True)