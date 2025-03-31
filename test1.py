from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 使用 Selenium 獲取動態內容
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # 無頭模式（不開視窗）
driver = webdriver.Chrome(options=options)  # 確保已安裝 ChromeDriver
driver.get("https://www.youbike.com.tw/region/i/stations/list/")

# 等待頁面加載完成
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "station-form"))
    )
except Exception as e:
    print("等待頁面加載時發生錯誤:", e)
    driver.quit()
    exit()
    
# 獲取頁面 HTML
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

# 繼續處理 HTML 結構
station_forms = soup.find_all("div", class_="station-form")
if not station_forms:
    print("未找到任何包含站點資訊的區域，請檢查 HTML 結構。")
else:
    for form in station_forms:
        # 找到站點資訊的 ul
        ul = form.find("ul", class_="item-inner2")
        if ul:
            # 遍歷 ul 中的每個 ol
            ol_elements = ul.find_all("ol")
            for ol in ol_elements:
                li_elements = ol.find_all("li")
                if len(li_elements) >= 4:
                    city = li_elements[0].text.strip()  # 城市
                    district = li_elements[1].text.strip()  # 區域
                    station_name = li_elements[2].text.strip()  # 站點名稱
                    bike_count = li_elements[3].text.strip()  # 可借車輛數
                    dock_count = li_elements[4].text.strip()  # 可停空位數
                    print(f"城市: {city} 區域: {district} 站點: {station_name} 可用車: {bike_count} 可停位: {dock_count}")
                else:
                    print("未找到足夠的 li 元素，請檢查 HTML 結構。")
        else:
            print("未找到 ul 元素，請檢查 HTML 結構。")

driver.quit()