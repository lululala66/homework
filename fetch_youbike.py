import threading
import time
import logging
import gc
from datetime import datetime, timedelta
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("user-agent=Mozilla/5.0 ...")
    return webdriver.Chrome(options=options)

def connect_to_database():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1", user="root", password="lululala",
            database="youbike_data", port=3306
        )
        logging.info("成功連線到資料庫")
        return conn
    except mysql.connector.Error as e:
        logging.error(f"連線資料庫失敗: {e}")
        return None

def fetch_youbike_data(city_values):
    start_time = time.time()
    now = datetime.now() + timedelta(minutes=3)

    conn = connect_to_database()
    if not conn:
        return
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO Taichung_youbike_data 
        (city, district, station_name, record_time, bikes_available, docks_available)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    driver = setup_driver()
    driver.get("https://www.youbike.com.tw/region/i/stations/list/")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "stations-select-area"))
        )
    except Exception as e:
        logging.error(f"頁面加載失敗: {e}")
        driver.quit()
        del driver
        return

    def switch_city(city_value):
        try:
            select = Select(driver.find_element(By.ID, "stations-select-area"))
            select.select_by_value(city_value)
            time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"切換縣市失敗: {e}")
            return False

    def process_pagination():
        records = []

        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            station_forms = soup.find_all("div", class_="station-form")

            for station_form in station_forms:
                ul = station_form.find("ul", class_="item-inner2")
                if not ul:
                    continue
                for ol in ul.find_all("ol"):
                    li = ol.find_all("li")
                    if len(li) >= 5:
                        try:
                            records.append((
                                li[0].text.strip(), li[1].text.strip(), li[2].text.strip(),
                                now, int(li[3].text.strip()), int(li[4].text.strip())
                            ))
                            if len(records) >= 100:
                                cursor.executemany(insert_query, records)
                                conn.commit()
                                logging.info(f"✅ 已寫入 100 筆資料")
                                records.clear()
                        except Exception as e:
                            logging.warning(f"資料處理錯誤: {e}")
            try:
                next_button = driver.find_element(By.CLASS_NAME, "cdp_i.next")
                if "disabled" in next_button.get_attribute("class"):
                    break
                next_button.click()
                time.sleep(2)
            except Exception:
                break

            del soup

        if records:
            cursor.executemany(insert_query, records)
            conn.commit()
            logging.info(f"✅ 最後寫入 {len(records)} 筆資料")

    for city_value, city_name in city_values:
        if switch_city(city_value):
            process_pagination()
            # 清除 8 天前的資料
        try:
            eight_days_ago = datetime.now() - timedelta(days=8)
            delete_query = """
                DELETE FROM Taichung_youbike_data
                WHERE record_time < %s
            """
            cursor.execute(delete_query, (eight_days_ago,))
            conn.commit()
            logging.info(f"🧹 已清除 8 天前資料，共 {cursor.rowcount} 筆")
        except Exception as e:
            logging.error(f"❌ 清除舊資料失敗: {e}")

    driver.quit()
    del driver
    cursor.close()
    del cursor
    conn.close()
    del conn

    gc.collect()

    elapsed = time.time() - start_time
    logging.info(f"✅ 執行完成！耗時: {elapsed:.2f} 秒")

if __name__ == "__main__":
    while True:
        now = datetime.now()
        if now.minute in [7, 17, 27, 37, 47, 57]:
            threads = [
                threading.Thread(target=fetch_youbike_data, args=([("06", "台中市")],), name="台中市")
            ]

            for thread in threads:
                thread.start()
                
            for thread in threads:
                thread.join()

            logging.info("等待下次執行...")
        else:
            time.sleep(10)