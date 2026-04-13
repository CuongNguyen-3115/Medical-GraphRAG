import os
import pandas as pd
import requests
import logging
from pathlib import Path

# 1. Cấu hình đường dẫn
BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
EXCEL_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata_demo.xlsx")
OUTPUT_DIR = os.path.join(BASE_DIR, "Data", "01_Raw_PDFs")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Tạo thư mục log nếu chưa có
os.makedirs(LOG_DIR, exist_ok=True)

# 2. Cấu hình Logging
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "download_process.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def download_medical_data():
    try:
        # Đọc dữ liệu (Sử dụng pandas để đọc Excel/CSV)
        df = pd.read_excel(EXCEL_PATH) # Hoặc pd.read_excel nếu là file .xlsx
        
        for index, row in df.iterrows():
            doc_id = row['Doc_ID']
            url = row['url']
            domain1 = str(row['domain_l1']).strip()
            domain2 = str(row['domain_l2']).strip()
            
            # Tạo đường dẫn thư mục theo domain_l1/domain_l2
            folder_path = os.path.join(OUTPUT_DIR, domain1, domain2)
            os.makedirs(folder_path, exist_ok=True)
            
            # Đặt tên file: DocID_Tên (Rút gọn)
            file_name = f"{doc_id}_{row['File_Name'][:50]}.pdf"
            file_path = os.path.join(folder_path, file_name)
            
            # Tiến hành tải file
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    logging.info(f"Thành công: {doc_id} -> {file_path}")
                else:
                    logging.error(f"Lỗi {response.status_code}: {doc_id} tại URL {url}")
            except Exception as e:
                logging.error(f"Ngoại lệ khi tải {doc_id}: {str(e)}")
                
    except Exception as e:
        print(f"Lỗi đọc file Excel: {e}")
        logging.critical(f"Không thể khởi động tiến trình: {e}")

if __name__ == "__main__":
    download_medical_data()