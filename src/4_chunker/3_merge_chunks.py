import json
import os
import logging
from datetime import datetime

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks(2)\medical_chunks.json"
OUTPUT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks(2)\medical_chunks_merged.json"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\4_chunker(2)"
MIN_TOKEN_THRESHOLD = 200  # Ngưỡng gộp

os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_filename = f"merging_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def merge_small_chunks(input_path, output_path, threshold):
    logging.info(f"Bắt đầu hậu xử lý gộp chunk từ: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    if not chunks:
        logging.warning("File JSON rỗng!")
        return

    merged_chunks = []
    temp_chunk = None

    for i, current_chunk in enumerate(chunks):
        # Nếu là chunk đầu tiên, khởi tạo temp_chunk
        if temp_chunk is None:
            temp_chunk = current_chunk
            continue

        current_token = current_chunk['metadata']['token_count']
        temp_token = temp_chunk['metadata']['token_count']
        
        # Kiểm tra nếu cùng một file nguồn
        same_file = temp_chunk['metadata']['source_file'] == current_chunk['metadata']['source_file']

        # ĐIỀU KIỆN GỘP: 
        # Nếu chunk hiện tại quá nhỏ VÀ cùng file nguồn
        if current_token < threshold and same_file:
            logging.info(f"Gộp chunk {current_chunk['chunk_id']} ({current_token} tk) vào chunk trước đó.")
            
            # Gộp nội dung
            temp_chunk['content'] += "\n" + current_chunk['content']
            # Cập nhật token_count
            temp_chunk['metadata']['token_count'] += current_token
            # Có thể giữ nguyên split_order của chunk chính
        
        # Nếu chunk trước đó quá nhỏ (thường xảy ra ở đầu file)
        elif temp_token < threshold and same_file:
            logging.info(f"Chunk trước đó quá nhỏ ({temp_token} tk). Gộp chunk hiện tại vào nó.")
            temp_chunk['content'] += "\n" + current_chunk['content']
            temp_chunk['metadata']['token_count'] += current_token
        
        else:
            # Nếu không thỏa mãn gộp, đẩy temp_chunk vào danh sách cuối và lấy current làm temp mới
            merged_chunks.append(temp_chunk)
            temp_chunk = current_chunk

    # Đẩy chunk cuối cùng vào list
    if temp_chunk:
        merged_chunks.append(temp_chunk)

    # Lưu kết quả
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_chunks, f, ensure_ascii=False, indent=4)
    
    logging.info(f"Hoàn tất! Số lượng chunk ban đầu: {len(chunks)}")
    logging.info(f"Số lượng chunk sau khi gộp: {len(merged_chunks)}")
    logging.info(f"Đã giảm bớt: {len(chunks) - len(merged_chunks)} chunks.")

if __name__ == "__main__":
    merge_small_chunks(INPUT_FILE, OUTPUT_FILE, MIN_TOKEN_THRESHOLD)