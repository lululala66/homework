
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, LocationMessage, TextSendMessage
import requests

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/linewebhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text.strip()
    if msg.startswith("查站 "):
        station_name = msg[3:]
        res = requests.get("https://yourapi/yourendpoint", params={"station": station_name})
        reply = f"查詢結果（模擬）：{station_name}"
    elif msg.startswith("搜尋 "):
        keyword = msg[3:]
        res = requests.get("https://yourapi/search", params={"q": keyword})
        data = res.json()
        reply = "找到站點：" + ", ".join(data.get("suggestions", []))
    else:
        reply = "請輸入「查站 站名」或「搜尋 關鍵字」，或傳送位置"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    lat, lng = event.message.latitude, event.message.longitude
    res = requests.get("https://yourapi/nearest_station", params={"lat": lat, "lng": lng})
    if res.status_code == 200:
        data = res.json()
        reply = f"📍 最近站點：{data['station_name']}，距離：{data['distance']} 公尺"
    else:
        reply = "無法取得最近站點資訊"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
