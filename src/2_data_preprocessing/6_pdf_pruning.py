import fitz  # PyMuPDF
import os
import logging
from pathlib import Path

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\02_PDF\Demo"
OUTPUT_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\03_Markdown\1_PDF_Pruning"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\2_data_preprocessing\6_pdf_pruning"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pdf_pruning.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Danh sách từ khóa nhận diện trang Danh mục viết tắt thực sự
ABBREV_KEYWORDS = [
    "TỪ VIẾT TẮT", "DANH MỤC CÁC TỪ VIẾT TẮT", "KÝ HIỆU CHỮ VIẾT TẮT", 
    "DANH MỤC TỪ VIẾT TẮT", "CÁC CHỮ VIẾT TẮT", "DANH MỤC KÝ HIỆU", 
    "DANH MỤC VIẾT TẮT", "BẢNG CÁC CHỮ VIẾT TẮT"
]

# Từ khóa nhận diện trang Mục lục (để bỏ qua)
INDEX_KEYWORDS = ["MỤC LỤC", "NỘI DUNG"]

def find_true_start_page(pdf_path):
    """
    Tìm trang bắt đầu:
    - Phải chứa ABBREV_KEYWORDS
    - KHÔNG ĐƯỢC chứa INDEX_KEYWORDS (để tránh dừng ở trang Mục lục)
    """
    doc = fitz.open(pdf_path)
    search_limit = min(50, len(doc)) # Tăng lên 20 trang vì mục lục có thể dài
    
    true_start = None
    
    for page_num in range(search_limit):
        text = doc[page_num].get_text().upper()
        
        # Kiểm tra xem có chứa từ khóa viết tắt không
        has_abbrev = any(kw in text for kw in ABBREV_KEYWORDS)
        # Kiểm tra xem có phải trang mục lục không
        is_index_page = any(idx in text for idx in INDEX_KEYWORDS)
        
        if has_abbrev:
            if is_index_page:
                logging.info(f"Đã tìm thấy từ khóa tại trang {page_num + 1} nhưng là TRANG MỤC LỤC. Tiếp tục tìm...")
                continue
            else:
                # Đây là trang danh mục viết tắt thực sự (không phải dòng liệt kê trong mục lục)
                true_start = page_num
                break
    
    doc.close()
    return true_start

def prune_pdf(pdf_file):
    input_path = os.path.join(INPUT_DIR, pdf_file)
    output_path = os.path.join(OUTPUT_DIR, pdf_file)
    
    start_page = find_true_start_page(input_path)
    
    doc = fitz.open(input_path)
    new_doc = fitz.open()
    
    if start_page is not None:
        logging.info(f"--- [SUCCESS] {pdf_file}: Cắt từ trang {start_page + 1} ---")
        new_doc.insert_pdf(doc, from_page=start_page, to_page=len(doc)-1)
    else:
        logging.info(f"--- [KEEP ALL] {pdf_file}: Không tìm thấy trang viết tắt thực sự. Giữ nguyên. ---")
        new_doc.insert_pdf(doc)

    new_doc.save(output_path)
    new_doc.close()
    doc.close()

def main():
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    logging.info(f"Bắt đầu quét {len(pdf_files)} file PDF...")

    for pdf_file in pdf_files:
        try:
            prune_pdf(pdf_file)
        except Exception as e:
            logging.error(f"Lỗi xử lý {pdf_file}: {str(e)}")

if __name__ == "__main__":
    main()