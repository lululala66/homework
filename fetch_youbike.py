import threading
import time
import logging
from datetime import datetime , timedelta
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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


def connect_to_database():
    """連線到 MySQL 資料庫"""
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="lululala",
            database="youbike_data",
            port=3306,
        )
        logging.info("成功連線到資料庫")
        return conn
    except mysql.connector.Error as e:
        logging.error(f"連線資料庫失敗: {e}")
        return None


def fetch_youbike_data(city_values):
    """爬取 YouBike 資料並存入 MySQL 資料庫"""
    start_time = time.time()  # 開始計時
    now = datetime.now() + timedelta(minutes=3)  # 台灣時間（UTC+8）
    # 初始化資料庫連線
    conn = connect_to_database()
    if not conn:
        return
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO Taichung_youbike_data (city, district, station_name, record_time, bikes_available, docks_available)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    # 初始化 WebDriver
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
        """處理分頁並將資料寫入資料庫"""
        records = []  # 用來儲存每批次要寫入的資料

        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            station_forms = soup.find_all("div", class_="station-form")

            if not station_forms:
                logging.warning("未找到任何站點資訊")
                break

            for station_form in station_forms:
                ul = station_form.find("ul", class_="item-inner2")
                if ul:
                    ol_elements = ul.find_all("ol")
                    for ol in ol_elements:
                        li_elements = ol.find_all("li")
                        if len(li_elements) >= 5:
                            try:
                                city = li_elements[0].text.strip()
                                district = li_elements[1].text.strip()
                                name = li_elements[2].text.strip()
                                bikes = int(li_elements[3].text.strip())
                                docks = int(li_elements[4].text.strip())

                                records.append((city, district, name, now, bikes, docks))

                                # 每 10 筆資料一次提交
                                if len(records) >= 100:
                                    cursor.executemany(
                                        insert_query,
                                        records
                                    )
                                    conn.commit()  # 批次提交
                                    logging.info(f"✅ 已寫入資料：{len(records)} 筆")
                                    records.clear()  # 清空當前批次資料

                            except Exception as e:
                                logging.warning(f"寫入 MySQL 發生錯誤: {e}")
                else:
                    logging.warning("找不到 ul.item-inner2")

            # 嘗試點擊下一頁按鈕
            try:
                next_button = driver.find_element(By.CLASS_NAME, "cdp_i.next")
                if "disabled" in next_button.get_attribute("class"):
                    logging.info("已到最後一頁")
                    break
                next_button.click()
                time.sleep(2)  # 等待頁面更新
            except Exception as e:
                logging.warning(f"分頁處理結束或發生錯誤: {e}")
                break

        # 如果還有未提交的資料，最後一次提交
        if records:
            cursor.executemany(
                insert_query,
                records
            )
            conn.commit()
            logging.info(f"✅ 最後提交資料：{len(records)} 筆")

    # 處理每個縣市
    for city_value, city_name in city_values:
        if switch_city(city_value):
            process_pagination()

    # 關閉資源
    driver.quit()
    cursor.close()
    conn.close()

    elapsed_time = time.time() - start_time
    logging.info(f"✅ 所有資料已寫入資料庫！耗時: {elapsed_time:.2f} 秒")

if __name__ == "__main__":
    while True:
        now = datetime.now()
        if now.minute in [7, 17, 27, 37, 47, 57] :
            threads = [
                threading.Thread(target=fetch_youbike_data, args=([("06", "台中市")],), name="台中市"),
            ]

            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()

            logging.info("等待下次執行...")
        else:
            time.sleep(10) # 每 10 秒檢查一次時間