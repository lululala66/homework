import threading
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

def fetch_youbike_data(city_values):
# 設定 Selenium 選項
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # 啟動 WebDriver
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.youbike.com.tw/region/i/stations/list/")

    # 等待頁面加載完成
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "stations-select-area"))
        )
        print(" 站點選擇器載入完成！")
    except Exception as e:
        print(" 等待頁面加載時發生錯誤:", e)
        driver.quit()
        exit()

    # 建立資料夾來存放 Excel 檔案
    output_folder = "YouBike_Data"
    os.makedirs(output_folder , exist_ok=True)

    # 切換縣市
    def switch_city(city_value):
        try:
            select_element = driver.find_element(By.ID, "stations-select-area")
            select = Select(select_element)
            select.select_by_value(city_value)  # 根據 value 切換縣市
            print(f" 已切換到縣市 value: {city_value}")
            time.sleep(2)  # 等待頁面更新
        except Exception as e:
            print(f" 切換縣市時發生錯誤: {e}")
            driver.quit()
            exit()

    # 遍歷分頁
    def process_pagination():
        data = []  # 用於存放所有站點資訊
        while True:
            # 取得當前頁面的 HTML
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            station_forms = soup.find_all("div", class_="station-form")

            if not station_forms:
                print(" 未找到任何站點資訊，請檢查 HTML 結構。")
            else:
                for form in station_forms:
                    ul = form.find("ul", class_="item-inner2")
                    if ul:
                        ol_elements = ul.find_all("ol")
                        for ol in ol_elements:
                            li_elements = ol.find_all("li")
                            if len(li_elements) >= 5:
                                city = li_elements[0].text.strip()
                                district = li_elements[1].text.strip()
                                station_name = li_elements[2].text.strip()
                                bike_count = li_elements[3].text.strip()
                                dock_count = li_elements[4].text.strip()
                                print(f" 城市: {city} |  區域: {district} |  站點: {station_name} |  可用車: {bike_count} |  可停位: {dock_count}")
                                # 將資料加入列表
                                data.append({
                                    "城市": city,
                                    "區域": district,
                                    "站點": station_name,
                                    "可用車": bike_count,
                                    "可停位": dock_count
                                })
                            else:
                                print(" 站點資訊不完整，請檢查 HTML 結構！")
                    else:
                        print(" 找不到 ul.item-inner2，請檢查 HTML 結構！")

            # 嘗試點擊下一頁按鈕
            try:
                next_button = driver.find_element(By.CLASS_NAME, "cdp_i.next")
                if "disabled" in next_button.get_attribute("class"):
                    print(" 已到最後一頁。")
                    break
                next_button.click()
                time.sleep(2)  # 等待頁面更新
            except :
                print(" 找不到下一頁按鈕或已到最後一頁。")
                break
        return data

    # 測試切換到不同縣市並遍歷分頁
    for city_value, city_name in city_values:
        switch_city(city_value)
        data = process_pagination()

        # 將資料存入 DataFrame 並寫入 Excel
        df = pd.DataFrame(data)
        output_path = os.path.join(output_folder, f"{city_name}.xlsx")
        df.to_excel(output_path, index=False)
        print(f" 資料已寫入 {output_path}")

    # 關閉瀏覽器
    driver.quit()
    print(" 所有資料已成功寫入 Excel 檔案！")

a = threading.Thread(target=fetch_youbike_data, args=([("03", "桃園市")],))
b = threading.Thread(target=fetch_youbike_data, args=([("15", "臺東縣")],))

a.start()
b.start()

a.join()
b.join()
print("Done")

# 這段程式碼使用 Selenium 爬取 YouBike 的站點資訊，並將資料存入 Excel 檔案中。
