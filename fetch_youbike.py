import threading
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def setup_driver():
    """設定 Selenium WebDriver 選項並返回 driver"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 無頭模式
    options.add_argument("--ignore-certificate-errors")  # 忽略 SSL 證書錯誤
    options.add_argument("--allow-insecure-localhost")  # 允許不安全的本地端連線
    options.add_argument("--disable-blink-features=AutomationControlled")  # 禁用自動化控制提示
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )  # 設定 User-Agent
    return webdriver.Chrome(options=options)


def fetch_youbike_data(city_values):
    """爬取 YouBike 資料並存入 Excel"""
    start_time = time.time()  # 開始計時

    driver = setup_driver()
    driver.get("https://www.youbike.com.tw/region/i/stations/list/")

    # 等待頁面加載完成
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "stations-select-area"))
        )
        logging.info("站點選擇器載入完成！")
    except Exception as e:
        logging.error(f"等待頁面加載時發生錯誤: {e}")
        driver.quit()
        return

    # 建立資料夾來存放 Excel 檔案
    output_folder = "YouBike_Data"
    os.makedirs(output_folder, exist_ok=True)

    def switch_city(city_value):
        """切換到指定縣市"""
        try:
            select_element = driver.find_element(By.ID, "stations-select-area")
            select = Select(select_element)
            select.select_by_value(city_value)  # 根據 value 切換縣市
            logging.info(f"已切換到縣市 value: {city_value}")
            time.sleep(2)  # 等待頁面更新
        except Exception as e:
            logging.error(f"切換縣市時發生錯誤: {e}")
            return False
        return True

    def process_pagination():
        """處理分頁並返回所有站點資料"""
        data = []
        while True:
            # 取得當前頁面的 HTML
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            station_forms = soup.find_all("div", class_="station-form")

            if not station_forms:
                logging.warning("未找到任何站點資訊，請檢查 HTML 結構。")
                break

            for station_form in station_forms:
                ul = station_form.find("ul", class_="item-inner2")
                if ul:
                    ol_elements = ul.find_all("ol")
                    for ol in ol_elements:
                        li_elements = ol.find_all("li")
                        if len(li_elements) >= 5:
                            data.append({
                                "城市": li_elements[0].text.strip(),
                                "區域": li_elements[1].text.strip(),
                                "站點": li_elements[2].text.strip(),
                                "可用車": li_elements[3].text.strip(),
                                "可停位": li_elements[4].text.strip(),
                            })
                        else:
                            logging.warning("站點資訊不完整，請檢查 HTML 結構！")
                else:
                    logging.warning("找不到 ul.item-inner2，請檢查 HTML 結構！")

            # 嘗試點擊下一頁按鈕
            try:
                next_button = driver.find_element(By.CLASS_NAME, "cdp_i.next")
                if "disabled" in next_button.get_attribute("class"):
                    logging.info("已到最後一頁。")
                    break
                next_button.click()
                time.sleep(2)  # 等待頁面更新
            except Exception as e:
                logging.warning(f"找不到下一頁按鈕或已到最後一頁: {e}")
                break
        return data

    # 處理每個縣市
    for city_value, city_name in city_values:
        if not switch_city(city_value):
            continue

        data = process_pagination()
        if data:
            # 將資料存入 DataFrame 並寫入 Excel
            df = pd.DataFrame(data)
            output_path = os.path.join(output_folder, f"{city_name}.xlsx")
            df.to_excel(output_path, index=False)
            logging.info(f"資料已寫入 {output_path}")

    # 關閉瀏覽器
    driver.quit()

    # 計算總耗時
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"所有資料已成功寫入 Excel 檔案！總耗時: {elapsed_time:.2f} 秒")


# 使用多執行緒爬取不同縣市資料
threads = [
    threading.Thread(target=fetch_youbike_data, args=([("06", "台中市")],), name="台中市"),
    threading.Thread(target=fetch_youbike_data, args=([("15", "臺東縣")],), name="臺東縣"),
]

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

logging.info("所有執行緒已完成！")