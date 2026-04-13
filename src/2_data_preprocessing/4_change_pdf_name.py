import os
import pandas as pd
import logging
from datetime import datetime
from urllib.parse import unquote
from pathlib import Path

# --- 1. CẤU HÌNH ĐƯỜNG DẪN ---
BASE_PATH = r"C:\1. Project\2. DoAn_GraphRAG"
# Nếu file của bạn là Excel (.xlsx), hãy đổi tên và dùng pd.read_excel
EXCEL_FILE = os.path.join(BASE_PATH, "Data", "Medical_Metadata_demo.xlsx")
PDF_ROOT = os.path.join(BASE_PATH, "Data", "01_Raw_PDFs")
LOG_DIR = os.path.join(BASE_PATH, "logs")

# Tạo thư mục log nếu chưa có
os.makedirs(LOG_DIR, exist_ok=True)

# --- 2. CẤU HÌNH LOGGING ---
log_filename = f"rename_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(LOG_DIR, log_filename)
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def get_filename_from_url(url):
    """Trích xuất tên file từ URL và giải mã các ký tự đặc biệt (nếu có)"""
    if not isinstance(url, str): return ""
    # Lấy phần cuối của URL và loại bỏ đuôi .pdf để so khớp
    base_name = url.split('/')[-1].replace('.pdf', '')
    return unquote(base_name)

def rename_files_recursive():
    try:
        # 3. ĐỌC DỮ LIỆU METADATA
        # Nếu là file .xlsx thực tế, dùng: df = pd.read_excel(EXCEL_FILE)
        # Ở đây tôi giả định dùng file CSV bạn đã cung cấp
        df = pd.read_excel(os.path.join(BASE_PATH, "Data", "Medical_Metadata_demo.xlsx"))
        
        logging.info("=== BẮT ĐẦU TIẾN TRÌNH ĐỔI TÊN FILE ĐỆ QUY ===")
        print(f"Đang quét thư mục: {PDF_ROOT}")

        # Tạo dictionary ánh xạ: {tên_file_gốc_từ_url: doc_id} để tìm kiếm nhanh
        mapping = {}
        for _, row in df.iterrows():
            clean_name = get_filename_from_url(row['url'])
            if clean_name:
                mapping[clean_name] = str(row['Doc_ID']).strip()

        success_count = 0
        error_count = 0
        not_found_in_excel = 0

        # 4. QUÉT MỌI TẦNG THƯ MỤC (RECURSIVE WALK)
        for root, dirs, files in os.walk(PDF_ROOT):
            for filename in files:
                if not filename.lower().endswith('.pdf'):
                    continue
                
                # Tên file hiện tại (loại bỏ đuôi để so khớp)
                current_file_base = filename.replace('.pdf', '')
                old_file_path = os.path.join(root, filename)
                
                # Kiểm tra xem tên file này có trong mapping từ Excel không
                if current_file_base in mapping:
                    new_doc_id = mapping[current_file_base]
                    new_filename = f"{new_doc_id}.pdf"
                    new_file_path = os.path.join(root, new_filename)
                    
                    # Tránh đổi tên nếu file đã mang tên Doc_ID rồi
                    if filename == new_filename:
                        logging.info(f"SKIP: File {filename} đã đúng định dạng Doc_ID.")
                        continue

                    try:
                        os.rename(old_file_path, new_file_path)
                        logging.info(f"SUCCESS: [{filename}] -> [{new_filename}] tại {root}")
                        success_count += 1
                    except Exception as e:
                        logging.error(f"ERROR: Không thể đổi tên {filename} - {str(e)}")
                        error_count += 1
                else:
                    logging.warning(f"UNKNOWN: File [{filename}] không tìm thấy ánh xạ trong Excel.")
                    not_found_in_excel += 1

        # 5. TỔNG KẾT
        summary = (f"\nHOÀN TẤT TIẾN TRÌNH!\n"
                   f"- Thành công: {success_count}\n"
                   f"- Lỗi: {error_count}\n"
                   f"- File không nằm trong danh sách Excel: {not_found_in_excel}\n"
                   f"Chi tiết log tại: {log_path}")
        print(summary)
        logging.info(summary)

    except Exception as e:
        logging.critical(f"LỖI HỆ THỐNG: {str(e)}")
        print(f"Lỗi nghiêm trọng: {e}")

if __name__ == "__main__":
    rename_files_recursive()