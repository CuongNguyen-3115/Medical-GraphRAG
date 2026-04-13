import json
import os
import logging
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks\Header_Splitting(2)\medical_master_chunks.json"
OUTPUT_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks\Recursive_Splitting"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\4_chunker"

# Tạo thư mục nếu chưa có
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "chunking_log.txt"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def recursive_chunking_process():
    # 1. Load dữ liệu từ Header Splitting
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f"Đã load {len(data)} chunks từ Header Splitting.")
    except Exception as e:
        logging.error(f"Lỗi khi đọc file input: {e}")
        return

    # 2. Cấu hình Splitter
    # Thường chọn chunk_size từ 500-1000 tokens cho GraphRAG
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    final_chunks = []
    
    # 3. Thực hiện split tiếp trên từng chunk cũ
    for idx, item in enumerate(data):
        content = item['content']
        parent_metadata = item['metadata']
        
        # Cắt nhỏ nội dung
        sub_chunks = text_splitter.split_text(content)
        
        for sub_idx, sub_content in enumerate(sub_chunks):
            new_id = f"{parent_metadata['chunk_id']}_S{sub_idx:03d}"
            
            # Tạo bản sao metadata và cập nhật thông tin mới
            new_metadata = parent_metadata.copy()
            new_metadata.update({
                "chunk_id": new_id,
                "parent_chunk_id": parent_metadata['chunk_id'], # Lưu vết cha
                "token_count": len(sub_content.split()), # Đếm từ cơ bản hoặc dùng tiktoken
                "split_order": sub_idx
            })
            
            final_chunks.append({
                "chunk_id": new_id,
                "content": sub_content,
                "metadata": new_metadata
            })
        
        if (idx + 1) % 100 == 0:
            logging.info(f"Đã xử lý {idx + 1}/{len(data)} header chunks...")

    # 4. Lưu kết quả
    output_path = os.path.join(OUTPUT_DIR, "medical_recursive_chunks.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_chunks, f, ensure_ascii=False, indent=4)
    
    logging.info(f"Hoàn thành! Tổng số chunk mới: {len(final_chunks)}")
    logging.info(f"File lưu tại: {output_path}")

if __name__ == "__main__":
    recursive_chunking_process()