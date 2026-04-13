import os
import json
import pandas as pd
import logging
import re
import tiktoken
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter

# --- CẤU HÌNH ---
ROOT_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG")
INPUT_DIR = ROOT_DIR / "Data" / "03_Markdown" / "3_Markdown_Normalized(2)"
METADATA_EXCEL = ROOT_DIR / "Data" / "Medical_Metadata_demo.xlsx"
OUTPUT_DIR = ROOT_DIR / "Data" / "04_Chunks" / "Header_Splitting(2)"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def count_tokens(text, model="gpt-4o"): # Hoặc cl100k_base cho hầu hết LLM hiện nay
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def load_metadata_map(excel_path):
    try:
        # Sử dụng .fillna(None) hoặc .replace để dọn dẹp NaN ngay khi đọc
        df = pd.read_excel(excel_path)
        df = df.where(pd.notnull(df), None) # Chuyển tất cả NaN thành None (JSON null)
        return df.set_index('Doc_ID').to_dict('index')
    except Exception as e:
        logging.error(f"Lỗi đọc metadata: {e}")
        return {}

def chunk_workflow():
    metadata_map = load_metadata_map(METADATA_EXCEL)
    
    headers_to_split_on = [("#", "Header_1"), ("##", "Header_2")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    md_files = list(INPUT_DIR.glob("*.md"))
    all_chunks_data = []

    for md_file in md_files:
        doc_id = md_file.stem
        file_meta = metadata_map.get(doc_id, {})

        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = markdown_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            # 1. Tính toán token
            token_count = count_tokens(chunk.page_content)
            
            # 2. Xây dựng ID duy nhất
            chunk_unique_id = f"{doc_id}_CH_{i:03d}"
            
            # 3. Kết hợp Metadata
            combined_metadata = {
                "chunk_id": chunk_unique_id,
                "source_file": md_file.name,
                "token_count": token_count,
                **file_meta,        # Đã xử lý NaN thành null
                **chunk.metadata    # Thông tin Header cấp 1, cấp 2
            }
            
            all_chunks_data.append({
                "chunk_id": chunk_unique_id,
                "content": chunk.page_content,
                "metadata": combined_metadata
            })

    # Lưu duy nhất 1 file tổng
    output_file = OUTPUT_DIR / "medical_master_chunks.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # ensure_ascii=False để đọc được tiếng Việt, indent=4 để dễ nhìn
        json.dump(all_chunks_data, f, ensure_ascii=False, indent=4)
    
    logging.info(f"Done! Tổng cộng {len(all_chunks_data)} chunks đã được lưu.")

if __name__ == "__main__":
    chunk_workflow()