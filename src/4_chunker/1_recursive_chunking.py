import os
import json
import pandas as pd
import tiktoken
import logging
import uuid
from datetime import datetime
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\03_Markdown\3_Markdown_Normalized(2)"
METADATA_PATH = r"C:\1. Project\2. DoAn_GraphRAG\Data\Medical_Metadata_demo.xlsx"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\4_chunker(2)"
OUTPUT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks(2)\medical_chunks.json"

# Tạo thư mục log nếu chưa có
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_filename = f"chunking_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- HÀM HỖ TRỢ ---
def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Đếm số lượng token trong một chuỗi văn bản."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))

# 1. Load Metadata từ Excel
logging.info("Đang tải dữ liệu metadata từ Excel...")
try:
    df_meta = pd.read_excel(METADATA_PATH)
    # Chuyển đổi File_Name thành string để lookup dễ dàng
    df_meta['File_Name'] = df_meta['File_Name'].astype(str)
    metadata_dict = df_meta.set_index('File_Name').to_dict(orient='index')
    logging.info(f"Đã tải metadata cho {len(metadata_dict)} tài liệu.")
except Exception as e:
    logging.error(f"Lỗi khi tải Excel: {e}")
    exit()

# 2. Cấu hình Splitter
# Header 2 cấp
headers_to_split_on = [
    ("#", "Header_L1"),
    ("##", "Header_L2"),
]

markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

# Recursive splitter để kiểm soát token (1500 token là trung bình của 1200-1800)
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    model_name="gpt-4", # Sử dụng cl100k_base
    chunk_size=1500,
    chunk_overlap=200, # Khoảng gối đầu 200 token (~13%)
)

final_chunks = []

# --- XỬ LÝ CHÍNH ---
logging.info("Bắt đầu quá trình chunking...")

files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".md")]

for file_name in files:
    file_path = os.path.join(INPUT_DIR, file_name)
    base_name = os.path.splitext(file_name)[0] # Ví dụ: DOC_016
    
    logging.info(f"Đang xử lý file: {file_name}")
    
    # Lấy metadata từ Excel
    file_meta = metadata_dict.get(base_name, {})
    if not file_meta:
        logging.warning(f"Không tìm thấy metadata cho {base_name}. Sẽ sử dụng dữ liệu rỗng.")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Bước A: Split theo Header để lấy context
        sections = markdown_splitter.split_text(raw_text)
        
        split_order = 0
        for section in sections:
            # Tạo header context từ metadata của section
            h1 = section.metadata.get("Header_L1", "")
            h2 = section.metadata.get("Header_L2", "")
            header_context = f"{h1} > {h2}".strip(" > ")

            # Bước B: Split section nhỏ hơn nếu vượt quá token limit
            sub_chunks = text_splitter.split_text(section.page_content)
            
            for content in sub_chunks:
                token_count = num_tokens_from_string(content)
                
                chunk_obj = {
                    "chunk_id": str(uuid.uuid4()),
                    "content": content,
                    "metadata": {
                        "source_file": file_name,
                        "token_count": token_count,
                        "header_context": header_context,
                        "title": file_meta.get("title", "N/A"),
                        "publisher": file_meta.get("publisher", "N/A"),
                        "domain_l1": file_meta.get("domain_l1", "N/A"),
                        "domain_l2": file_meta.get("domain_l2", "N/A"),
                        "source_type": file_meta.get("source_type", "N/A"),
                        "Published_Date": file_meta.get("Published_Date", "N/A"),
                        "File_Name": base_name,
                        "url": file_meta.get("url", "N/A"),
                        "split_order": split_order
                    }
                }
                final_chunks.append(chunk_obj)
                split_order += 1

    except Exception as e:
        logging.error(f"Lỗi khi xử lý file {file_name}: {e}")

# 3. Xuất kết quả
logging.info(f"Tổng cộng đã tạo ra {len(final_chunks)} chunks.")
try:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_chunks, f, ensure_ascii=False, indent=4)
    logging.info(f"Đã lưu kết quả tại: {OUTPUT_FILE}")
except Exception as e:
    logging.error(f"Lỗi khi lưu file JSON: {e}")

logging.info("Hoàn tất.")