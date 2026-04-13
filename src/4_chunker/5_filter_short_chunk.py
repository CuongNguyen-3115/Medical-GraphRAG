import json
import os

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks\Recursive_Splitting\medical_recursive_chunks.json"
OUTPUT_SHORT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks\Recursive_Splitting\short_chunks_audit.json"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\4_chunker"

def extract_short_chunks(threshold=30):
    if not os.path.exists(INPUT_FILE):
        print(f"Lỗi: Không tìm thấy file tại {INPUT_FILE}")
        return

    # 1. Load dữ liệu
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    # 2. Lọc các chunk có token_count < threshold
    # Lưu ý: Code này dùng trường 'token_count' có sẵn trong metadata của bạn
    short_chunks = [
        item for item in chunks 
        if item.get('metadata', {}).get('token_count', 0) < threshold
    ]

    # 3. Lưu ra file mới
    with open(OUTPUT_SHORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(short_chunks, f, ensure_ascii=False, indent=4)

    # 4. Ghi log nhanh
    log_msg = (
        f"--- BÁO CÁO TRÍCH XUẤT CHUNK NGẮN ---\n"
        f"Ngưỡng lọc: < {threshold} tokens\n"
        f"Tổng số chunk quét: {len(chunks)}\n"
        f"Số chunk ngắn tìm thấy: {len(short_chunks)}\n"
        f"Tỷ lệ: {(len(short_chunks)/len(chunks))*100:.2f}%\n"
        f"File kết quả: {OUTPUT_SHORT_FILE}\n"
    )
    
    print(log_msg)
    
    with open(os.path.join(LOG_DIR, "short_chunks_audit_log.txt"), 'w', encoding='utf-8') as f:
        f.write(log_msg)

if __name__ == "__main__":
    extract_short_chunks(30)