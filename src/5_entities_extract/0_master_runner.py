import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# --- CẤU HÌNH ---
LOG_DIR = r"C:\1. Project\ĐATN\logs\6_entities_extract"
os.makedirs(LOG_DIR, exist_ok=True)

# Ghi log riêng cho Master Script
log_file = os.path.join(LOG_DIR, f"MASTER_RUNNER_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [MASTER] - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

# Danh sách 3 file API theo thứ tự ưu tiên
SCRIPTS = [
    r"C:\1. Project\ĐATN\src\6_entities_extract\1_extract_gemini.py",
    r"C:\1. Project\ĐATN\src\6_entities_extract\1_extract_groq.py",
    r"C:\1. Project\ĐATN\src\6_entities_extract\1_extract_hf.py"
]

def run_master_loop():
    logging.info("Bắt đầu thực thi")
    
    cycle_count = 1
    
    while True:
        logging.info(f"==== BẮT ĐẦU VÒNG LẶP LỚN THỨ {cycle_count} ====")
        
        # Biến để kiểm tra xem có bất kỳ script nào thành công xử lý được file không
        all_apis_exhausted = True 
        
        for script_path in SCRIPTS:
            script_name = os.path.basename(script_path)
            logging.info(f"Đang cấp quyền thực thi cho: {script_name}")
            
            # Khởi chạy script con bằng subprocess (Dùng chính môi trường python hiện tại)
            # Dùng subprocess.call sẽ chặn chương trình lại cho đến khi script con chạy xong hoặc bị ngắt (sys.exit)
            try:
                result = subprocess.call([sys.executable, script_path])
                
                if result == 0:
                    # Script con trả về 0 (Thành công trọn vẹn, không dính sys.exit(1))
                    # Nghĩa là hàm main() của script con đã chạy hết danh sách pending_chunks
                    logging.info(f"TUYỆT VỜI! Hệ thống đã xử lý xong TOÀN BỘ dữ liệu tại {script_name}.")
                    logging.info("Dừng Master Script. Chúc mừng bạn đã hoàn thành trích xuất ĐATN!")
                    sys.exit(0)
                else:
                    # Script con bị ngắt ngang do gọi sys.exit(1) (Cạn quota)
                    logging.warning(f"{script_name} đã cạn kiệt tài nguyên (Exit Code: {result}).")
                    logging.info("⏳ Chờ 10 giây trước khi khởi động API tiếp theo...")
                    time.sleep(10)
                    
            except Exception as e:
                logging.error(f"❌ Lỗi khi khởi chạy {script_name}: {e}")
                time.sleep(10)
                
        # Nếu vòng for chạy qua cả 3 file mà không có file nào trả về result == 0
        # Nghĩa là TẤT CẢ 3 API đều đang hết hạn mức (Quá tải toàn hệ thống)
        logging.critical("🚨 BÁO ĐỘNG ĐỎ: CẢ 3 NỀN TẢNG (Gemini, Groq, HF) ĐỀU ĐÃ CẠN QUOTA!")
        
        # Ngủ một giấc dài (ví dụ: 60 phút) để các nền tảng hồi phục Rate Limit
        sleep_minutes = 20
        logging.info(f"💤 Master Script đi ngủ {sleep_minutes} phút. Sẽ tự động thức dậy lúc: {datetime.fromtimestamp(time.time() + sleep_minutes*60).strftime('%H:%M:%S')}")
        time.sleep(sleep_minutes * 60)
        
        cycle_count += 1

if __name__ == "__main__":
    run_master_loop()