from flask import Flask, request, jsonify
import requests

app = Flask(__name__)


@app.route("/route", methods=["POST"])
def route():
    data = request.json
    start = data.get("start")
    destination = data.get("destination")

    # 使用 NLSC 或其他 geocoding API 轉成經緯度（這裡先用 mock data）
    def mock_geocode(addr):
        if addr == "我的位置":
            return (24.147736, 120.673648)  # 模擬台中位置
        return (24.1500, 120.6830)  # 模擬地址轉換結果

    start_latlng = mock_geocode(start)
    dest_latlng = mock_geocode(destination)

    # 👉 這裡要做：查資料庫找最近的借/還站（以目前與目的地為中心）
    # result = {
    #     "user_to_borrow": [...],
    #     "borrow_station": (lat, lng),
    #     "return_station": (lat, lng),
    #     "return_to_dest": [...],
    # }

    return jsonify({
        "status": "ok",
        "data": {
            "start": start_latlng,
            "destination": dest_latlng,
            # "borrow_station": ...,
            # "return_station": ...,
        }
    })
if __name__ == "__main__":
    app.run(debug=True)