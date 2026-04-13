import pandas as pd
import json
import os
import logging
from datetime import datetime

# --- Cấu hình đường dẫn ---
BASE_PATH = r"C:\1. Project\2. DoAn_GraphRAG"
DATA_PATH = os.path.join(BASE_PATH, "Data")
LOG_PATH = os.path.join(BASE_PATH, "logs")
EXCEL_FILE = os.path.join(DATA_PATH, "Medical_Metadata.xlsx")

# Danh sách các file JSON cần đọc
JSON_FILES = [
    "(2026_1)_tcncyh_all_medical_urls.json",
    "(2026_2)_tcncyh_all_medical_urls.json",
    "(2026_3)_tcncyh_all_medical_urls.json"
]

# --- Khởi tạo Logging ---
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_PATH, "append_metadata.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def slugify_filename(title):
    """Tạo tên file đơn giản từ tiêu đề (không dấu, gạch dưới)"""
    import re
    # Chuyển thành chữ thường và thay thế ký tự đặc biệt
    name = title.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:50] # Giới hạn độ dài

def process_data():
    all_new_data = []
    
    # 1. Đọc dữ liệu từ các file JSON
    for file_name in JSON_FILES:
        full_path = os.path.join(DATA_PATH, file_name)
        if not os.path.exists(full_path):
            logging.warning(f"Không tìm thấy file: {full_path}")
            continue
            
        logging.info(f"Đang đọc dữ liệu từ: {file_name}")
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_new_data.extend(data)

    if not all_new_data:
        logging.error("Không có dữ liệu mới để chèn!")
        return

    # 2. Đọc file Excel hiện tại
    try:
        df_existing = pd.read_excel(EXCEL_FILE)
        logging.info(f"Đã mở file Excel thành công. Hiện có {len(df_existing)} dòng.")
    except Exception as e:
        logging.error(f"Lỗi khi đọc file Excel: {e}")
        return

    # 3. Chuẩn bị dữ liệu mới để append (bắt đầu tính từ dòng 67 - index 66)
    start_row = 66 
    new_rows = []
    
    # Tính toán ID tiếp theo (DOC_067, DOC_068...)
    current_id_count = start_row + 1

    for item in all_new_data:
        # Lấy năm từ trường published_date
        raw_date = item.get('published_date', '')
        year = raw_date[:4] if raw_date and len(raw_date) >= 4 else ""
        
        row = {
            'Doc_ID': f"DOC_{current_id_count:03d}",
            'title': item.get('title'),
            'publisher': item.get('publisher'),
            'domain': item.get('domain'),
            'source_type': item.get('source_type'),
            'Published_Date': year,
            'File_Name': slugify_filename(item.get('title', 'unnamed')),
            'url': item.get('url'),
            'status': 'Chưa xử lý',
            'notes': ''
        }
        new_rows.append(row)
        current_id_count += 1

    df_new = pd.DataFrame(new_rows)

    # 4. Thực hiện điền tiếp vào file (Ghi đè phần dữ liệu từ dòng 67 trở đi)
    # Lấy phần dữ liệu cũ từ dòng 1 đến 66 (index 0 đến 65)
    df_fixed = df_existing.iloc[:start_row]
    
    # Nối phần cũ và phần mới
    df_final = pd.concat([df_fixed, df_new], ignore_index=True)

    # 5. Lưu lại file Excel
    try:
        df_final.to_excel(EXCEL_FILE, index=False)
        logging.info(f"Đã cập nhật thành công {len(new_rows)} dòng vào {EXCEL_FILE}")
        logging.info(f"Dữ liệu mới bắt đầu từ DOC_{start_row + 1:03d}")
    except Exception as e:
        logging.error(f"Lỗi khi lưu file Excel: {e}")

if __name__ == "__main__":
    process_data()