from flask import Flask, render_template, request, jsonify
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="lululala",
        database="youbike_data",
        port=3306,
    )

@app.route("/", methods=["GET"])
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT DISTINCT district FROM Taichung_youbike_data WHERE city = '臺中市'")
    all_districts = sorted([row['district'] for row in cursor.fetchall()])

    selected = request.args.get("district")
    selected_districts = [selected] if selected else []

    search_station = request.args.get("station")
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
        cursor.execute("""
            SELECT t.city, t.district, t.station_name, t.bikes_available, t.docks_available
            FROM Taichung_youbike_data t
            INNER JOIN (
                SELECT station_name, MAX(record_time) AS latest_time
                FROM Taichung_youbike_data
                WHERE city = '臺中市' AND district = %s
                GROUP BY station_name
            ) latest
            ON t.station_name = latest.station_name AND t.record_time = latest.latest_time
            WHERE t.city = '臺中市' AND t.district = %s
            ORDER BY t.station_name
        """, (selected, selected))
        data = cursor.fetchall()

    conn.close()
    return render_template("index.html", districts=all_districts, selected=selected_districts, stations=data)

# 🔍 AJAX 搜尋 API
@app.route("/search")
def search():
    keyword = request.args.get("q", "")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT station_name
        FROM Taichung_youbike_data
        WHERE station_name LIKE %s
        ORDER BY station_name
        LIMIT 10
    """, (f"%{keyword}%",))
    matches = [row[0] for row in cursor.fetchall()]

    conn.close()
    return jsonify(matches)

if __name__ == "__main__":
    app.run(debug=True)
