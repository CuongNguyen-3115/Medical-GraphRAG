import pandas as pd
from groq import Groq
import os
import time
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# 1. Cấu hình
load_dotenv()
BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
FILE_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata.xlsx")
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_filename = f"normalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 2. Khởi tạo Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PRIMARY_MODEL = os.getenv("GROQ_MODEL_ID_1")
BACKUP_MODEL = os.getenv("GROQ_MODEL_ID_2")

SYSTEM_PROMPT = """
Bạn là chuyên gia phân loại dữ liệu y tế chuyên sâu. 
Dựa vào tiêu đề tài liệu, hãy phân loại chuyên khoa theo tiêu chuẩn y học:
- domain_l1: Chuyên khoa lớn (ví dụ: Nội khoa, Ngoại khoa, Nhi khoa, Sản khoa, Dược học, Truyền nhiễm, v.v.)
- domain_l2: Hệ cơ quan hoặc chuyên khoa sâu (ví dụ: Tim mạch, Thận - Tiết niệu, Hô hấp, Nội tiết, Da liễu, v.v.)
Yêu cầu: Trả về duy nhất định dạng JSON: {"domain_l1": "...", "domain_l2": "..."}
"""

def call_groq_api(title, model_id):
    """Hàm gọi API dùng chung cho cả 2 model."""
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tiêu đề: {title}"}
        ],
        model=model_id,
        response_format={"type": "json_object"},
        temperature=0.1
    )
    return json.loads(chat_completion.choices[0].message.content)

def process_with_fallback(title):
    """Thử model chính, nếu lỗi quota/hệ thống thì thử model backup."""
    try:
        # Thử model chính
        return call_groq_api(title, PRIMARY_MODEL), PRIMARY_MODEL
    except Exception as e:
        error_msg = str(e).lower()
        if "rate_limit" in error_msg or "quota" in error_msg:
            logging.warning(f"Model chính hết quota, đang thử model backup {BACKUP_MODEL}...")
            try:
                return call_groq_api(title, BACKUP_MODEL), BACKUP_MODEL
            except Exception as e2:
                logging.error(f"Cả 2 model đều thất bại: {str(e2)}")
                return None, None
        else:
            logging.error(f"Lỗi không xác định: {str(e)}")
            return None, None

def main():
    logging.info("--- BẮT ĐẦU QUÁ TRÌNH (CHẾ ĐỘ GHI TRỰC TIẾP & BACKUP) ---")
    
    if not os.path.exists(FILE_PATH):
        logging.error(f"Không tìm thấy file: {FILE_PATH}")
        return

    # Đọc file
    df = pd.read_excel(FILE_PATH)
    
    # Khởi tạo cột nếu chưa có
    if 'domain_l1' not in df.columns:
        df['domain_l1'] = None
    if 'domain_l2' not in df.columns:
        df['domain_l2'] = None

    total_rows = len(df)
    processed_count = 0

    for index, row in df.iterrows():
        # Kiểm tra xem dòng này đã được xử lý chưa (Checkpoint)
        if pd.notna(row.get('domain_l1')) and row.get('domain_l1') != "Error" and row.get('domain_l1') != "N/A":
            continue

        title = str(row.get('title', ''))
        if not title or title.lower() == 'nan':
            df.at[index, 'domain_l1'] = "N/A"
            df.at[index, 'domain_l2'] = "N/A"
            continue

        logging.info(f"[{index+1}/{total_rows}] Đang xử lý: {title[:50]}...")
        
        start_time = time.time()
        result, used_model = process_with_fallback(title)
        elapsed = time.time() - start_time

        if result:
            df.at[index, 'domain_l1'] = result.get('domain_l1')
            df.at[index, 'domain_l2'] = result.get('domain_l2')
            logging.info(f"Thành công ({used_model}) trong {elapsed:.2f}s: {result}")
            
            # Ghi trực tiếp vào file sau mỗi dòng thành công
            try:
                df.to_excel(FILE_PATH, index=False)
            except Exception as e:
                logging.error(f"Lỗi khi ghi file (vui lòng đóng file Excel nếu đang mở): {e}")
        else:
            logging.error(f"Dòng {index} thất bại hoàn toàn. Dừng tiến trình để kiểm tra quota.")
            break # Dừng vòng lặp nếu cả 2 model đều lỗi để tránh lãng phí vòng lặp

        processed_count += 1
        time.sleep(0.3) # Tránh spam API quá nhanh

    logging.info(f"--- HOÀN THÀNH. Đã xử lý thêm {processed_count} dòng mới ---")

if __name__ == "__main__":
    main()