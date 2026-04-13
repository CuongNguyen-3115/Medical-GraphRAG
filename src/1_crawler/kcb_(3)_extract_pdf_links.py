import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# --- Cấu hình đường dẫn ---
BASE_PATH = r"C:\1. Project\2. DoAn_GraphRAG"
EXCEL_FILE = os.path.join(BASE_PATH, "Data", "Medical_Metadata_demo.xlsx")
LOG_FILE = os.path.join(BASE_PATH, "logs", "download_log.txt")

def setup_driver(download_path):
    chrome_options = Options()
    # Cấu hình để tự động tải file vào thư mục chỉ định mà không hỏi lại
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True # Tự động tải thay vì mở preview
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument("--headless") # Chạy ẩn danh nếu muốn
    
    # Bạn cần có chromedriver phù hợp với phiên bản Chrome máy đang dùng
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def download_process():
    # Đọc file (giả định là CSV như file bạn gửi)
    df = pd.read_excel(EXCEL_FILE)
    
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        for _, row in df.iterrows():
            d1 = str(row['domain_l1']).strip()
            d2 = str(row['domain_l2']).strip()
            url = row['url']
            doc_id = row['Doc_ID']
            
            # 1. Tạo folder đích
            target_dir = os.path.join(BASE_PATH, "Data", "01_Raw_PDFs", d1, d2)
            os.makedirs(target_dir, exist_ok=True)
            
            # 2. Khởi tạo driver cho từng folder (để set download path)
            driver = setup_driver(target_dir)
            
            try:
                log.write(f"{time.ctime()}: Đang truy cập {doc_id} tại {url}\n")
                driver.get(url)
                time.sleep(5) # Đợi trang load
                
                # Tìm nút tải xuống (Dựa trên cấu trúc trang kcb.vn)
                # Lưu ý: Bạn cần inspect trang để lấy Selector chính xác của button
                # Ví dụ dưới đây tìm button có chứa chữ "Tải" hoặc icon download
                download_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'download') or contains(text(), 'Tải')]")
                download_btn.click()
                
                time.sleep(10) # Đợi tải xong
                log.write(f"{time.ctime()}: SUCCESS | {doc_id} đã tải về {target_dir}\n")
            except Exception as e:
                log.write(f"{time.ctime()}: ERROR | {doc_id} thất bại: {str(e)}\n")
            finally:
                driver.quit()

if __name__ == "__main__":
    download_process()