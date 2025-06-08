import discord
import requests


TOKEN = "MTM4MTM0MDk2MjY0MjQ2MDc0Mg.GALeQX.29S92rmiy20XinJ7gHvDVRYaU6CzWQu36pWXYE"
API_BASE_URL = "http://localhost:5000"  # 改成你的 API 部署網址

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot 已上線：{client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    if content.startswith("!查站 "):
        station = content[4:]
        try:
            res = requests.get(f"{API_BASE_URL}/", params={"station": station})
            if res.status_code == 200 and res.text:
                json_res = requests.get(f"{API_BASE_URL}/station_info", params={"station": station}).json()
                if "station_name" in json_res:
                    reply = (
                        f"📍 {json_res['station_name']}\n"
                        f"🚲 可借車輛：{json_res['bikes_available']}\n"
                        f"📥 可停空位：{json_res['docks_available']}"
                    )
                else:
                    reply = "❌ 查無資料"
            else:
                reply = "❌ 查無資料"
            await message.channel.send(reply)  # ✅ 放在 if/else 外面，永遠都會發送
        except:
            await message.channel.send("🚨 無法連接查詢 API")


    elif content.startswith("!搜尋 "):
        keyword = content[4:]
        try:
            res = requests.get(f"{API_BASE_URL}/search", params={"q": keyword})
            data = res.json()
            suggestions = data.get("suggestions", [])
            if suggestions:
                await message.channel.send("🔍 找到站點：\n" + "\n".join(suggestions))
            else:
                await message.channel.send("❌ 沒有找到相關站點")
        except:
            await message.channel.send("🚨 無法連接搜尋 API")

    elif content.startswith("!附近 "):
        try:
            latlng = content[4:].split()
            lat, lng = float(latlng[0]), float(latlng[1])
            res = requests.get(f"{API_BASE_URL}/nearest_station", params={"lat": lat, "lng": lng})
            if res.status_code == 200:
                data = res.json()
                await message.channel.send(
                    f"📍 最近站點：{data['station_name']}，距離約 {data['distance']} 公尺"
                )
            else:
                await message.channel.send("❌ 找不到附近站點")
        except:
            await message.channel.send("⚠️ 請輸入正確格式：`!附近 緯度 經度`")

    elif content == "!幫助" or content == "!help":
        help_text = (
            "🤖 **YouBike Bot 指令清單：**\n"
            "```\n"
            "!查站 [站名]     ➜ 查詢指定站點資訊\n"
            "!搜尋 [關鍵字]   ➜ 模糊搜尋站名\n"
            "!附近 [緯度] [經度] ➜ 顯示你附近最近的站點\n"
            "!幫助             ➜ 顯示這份指令說明\n"
            "```"
        )
        await message.channel.send(help_text)

client.run(TOKEN)
