from flask import Flask, render_template, request, jsonify
import mysql.connector
import requests
from geopy.distance import geodesic

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
        stations = sorted(
            stations,
            key=lambda s: geodesic((lat, lng), (s['latitude'], s['longitude'])).meters
        )
        return stations[0] if stations else None

    def ors_route(start, end):
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

    if not borrow_station or not return_station:
        return jsonify({"error": "找不到站點"}), 500

    path1 = ors_route([user_lng, user_lat], [borrow_station['longitude'], borrow_station['latitude']])
    path2 = ors_route([borrow_station['longitude'], borrow_station['latitude']], [return_station['longitude'], return_station['latitude']])
    path3 = ors_route([return_station['longitude'], return_station['latitude']], [end_coord[1], end_coord[0]])

    return jsonify({
        "borrow": borrow_station,
        "return": return_station,
        "routes": {
            "walk1": path1,
            "bike": path2,
            "walk2": path3
        }
    })

@app.route('/nearest_station')
def nearest_station():
    lat = float(request.args.get("lat"))
    lng = float(request.args.get("lng"))
    type_ = request.args.get("type")
    city = request.args.get("city", "臺中市")

    stations = get_all_youbike_stations(city)

    def dist(s):
        return geodesic((lat, lng), (s['latitude'], s['longitude'])).meters

    if type_ == "borrow":
        filtered = [s for s in stations if s["bikes_available"] > 0]
    else:
        filtered = [s for s in stations if s["docks_available"] > 0]

# fallback 若無可借/可還站，退回所有站點
    if not filtered:
        filtered = stations

    nearest = min(filtered, key=dist)

    return jsonify({
        "station_name": nearest["station_name"],
        "lat": nearest["latitude"],
        "lng": nearest["longitude"]
    })

def get_all_youbike_stations(city):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.station_name, s.latitude, s.longitude, y.bikes_available, y.docks_available
        FROM Taichung_station_locations s
        JOIN (
            SELECT station_name, MAX(record_time) AS latest_time
            FROM Taichung_youbike_data
            WHERE city = %s
            GROUP BY station_name
        ) latest ON s.station_name = latest.station_name
        JOIN Taichung_youbike_data y ON y.station_name = latest.station_name AND y.record_time = latest.latest_time
        WHERE s.act = 1
    """, (city,))
    stations = cursor.fetchall()
    conn.close()
    return stations

if __name__ == "__main__":
    app.run(debug=True)
