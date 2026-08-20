import os
import re
import logging
from pathlib import Path
from datetime import datetime

# --- CẤU HÌNH ĐƯỜNG DẪN ---
SOURCE_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG\Data\03_Markdown\2_Markdown(2)")
OUTPUT_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG\Data\03_Markdown\3_Markdown_Normalized(2)")
LOG_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG\logs\2_data_convert(2)")

# Tạo thư mục nếu chưa có
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- CẤU HÌNH LOGGING ---
log_filename = f"convert_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = LOG_DIR / log_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def normalize_content(text, filename):
    """Xử lý lỗi font, ký hiệu và chuẩn hóa Header dựa trên logic linh hoạt."""
    
    # 1. Sửa lỗi font & ký hiệu
    corrections = {
        'Ƣ': 'Ư', 'ƣ': 'ư',
        '±': '±', '–': '-', '—': '-',
        '': '*', 
        '': 'x', 
    }
    for error, correct in corrections.items():
        text = text.replace(error, correct)

    lines = text.split('\n')
    new_lines = []
    
    # Regex cho các loại Header
    roman_regex = r'^[IVXLCDM]+\.'  # Ví dụ: I., II., IV.
    arabic_regex = r'^\d+\.'        # Ví dụ: 1., 2., 10.
    
    h2_roman_found = False
    h1_count = 0
    h2_count = 0

    for line in lines:
        clean_line = line.replace('#', '').replace('*', '').strip()
        
        if not clean_line:
            new_lines.append("")
            continue

        is_header = False

        # --- CHIẾN LƯỢC ĐÁNH HEADER CẬP NHẬT ---
        
        # 1. Kiểm tra Header 2 (Số La Mã + VIẾT HOA)
        if re.match(roman_regex, clean_line) and clean_line.isupper():
            new_lines.append(f"## {clean_line}")
            h2_roman_found = True
            h2_count += 1
            is_header = True
            
        # 2. Kiểm tra Header 2 (Số thường + VIẾT HOA) - Chỉ khi chưa có La Mã trước đó
        elif re.match(arabic_regex, clean_line) and clean_line.isupper() and not h2_roman_found:
            new_lines.append(f"## {clean_line}")
            h2_count += 1
            is_header = True
            
        # 3. Kiểm tra Header 1 (Chữ in hoa toàn bộ, không bắt đầu bằng số/La Mã đã xử lý ở trên)
        elif clean_line.isupper() and len(clean_line) > 3:
            new_lines.append(f"# {clean_line}")
            h1_count += 1
            is_header = True
            
        # 4. Nội dung bình thường
        if not is_header:
            new_lines.append(clean_line)

    logging.info(f"FILE: {filename} | H1: {h1_count} | H2: {h2_count} | RomanUsed: {h2_roman_found}")
    return '\n'.join(new_lines)

def main():
    logging.info("==========================================")
    logging.info("BẮT ĐẦU QUÁ TRÌNH CHUẨN HÓA DỮ LIỆU")
    logging.info(f"Nguồn: {SOURCE_DIR}")
    logging.info(f"Đích: {OUTPUT_DIR}")
    logging.info("==========================================")
    
    files = list(SOURCE_DIR.glob("*.md"))
    if not files:
        logging.warning("Không tìm thấy file .md nào!")
        return

    success_count = 0
    error_count = 0

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            normalized_content = normalize_content(content, file_path.name)
            
            output_path = OUTPUT_DIR / file_path.name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(normalized_content)
                
            success_count += 1
            logging.info(f"[OK] Đã lưu: {output_path.name}")
            
        except Exception as e:
            error_count += 1
            logging.error(f"[ERROR] Lỗi tại file {file_path.name}: {str(e)}")

    logging.info("==========================================")
    logging.info(f"HOÀN TẤT: Thành công {success_count}, Thất bại {error_count}")
    logging.info(f"Log chi tiết tại: {log_path}")
    logging.info("==========================================")

if __name__ == "__main__":
    main()