import json
import os

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_FILE = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_merged.json"
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"

def rename_chunk_ids(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Lỗi: Không tìm thấy file tại {input_path}")
        return

    # 1. Đọc dữ liệu từ file JSON
    print(f"Đang đọc dữ liệu từ: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    print(f"Tổng số chunk cần xử lý: {len(chunks)}")

    # 2. Thực hiện đổi tên chunk_id
    for chunk in chunks:
        # Lấy tên file từ metadata (ví dụ: DOC_016.md -> DOC_016)
        source_file = chunk.get('metadata', {}).get('source_file', 'UNKNOWN')
        file_base = os.path.splitext(source_file)[0]
        
        # Lấy thứ tự split (ví dụ: 0, 1, 2...)
        split_order = chunk.get('metadata', {}).get('split_order', 0)
        
        # Tạo ID mới theo format: [Tên_File]_chunk_[Thứ_tự_có_padding]
        # Padding 4 chữ số (0000) giúp các ID được sắp xếp đúng thứ tự alphabet
        new_id = f"{file_base}_chunk_{split_order:04d}"
        
        # Cập nhật chunk_id
        chunk['chunk_id'] = new_id

    # 3. Lưu kết quả ra file mới
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=4)
    
    print(f"Hoàn tất! Đã lưu file mới tại: {output_path}")

if __name__ == "__main__":
    rename_chunk_ids(INPUT_FILE, OUTPUT_FILE)