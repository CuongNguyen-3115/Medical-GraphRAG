import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import os
import logging
from pathlib import Path
from datetime import datetime

# --- 1. CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
POPPLER_PATH = r'C:\Users\NGUYEN CUONG\AppData\Local\Programs\MiKTeX\miktex\bin\x64'

# --- 2. ĐƯỜNG DẪN DỰ ÁN ---
BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\01_Raw_PDFs"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs"
os.makedirs(LOG_DIR, exist_ok=True)

# --- 3. THIẾT LẬP LOGGING ---
log_file = os.path.join(LOG_DIR, f"ocr_digitalization_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def is_scanned_pdf(file_path):
    """Kiểm tra xem PDF có phải là ảnh quét hay không bằng cách lấy mẫu text."""
    try:
        doc = fitz.open(file_path)
        num_pages = len(doc)
        # Lấy mẫu trang đầu, trang giữa và trang cuối
        sample_indices = sorted(list(set([0, num_pages // 2, num_pages - 1])))
        
        is_scanned = True
        total_chars = 0
        
        for idx in sample_indices:
            if 0 <= idx < num_pages:
                text = doc[idx].get_text().strip()
                total_chars += len(text)
                if len(text) > 50: # Ngưỡng nhận diện PDF Digital
                    is_scanned = False
                    break
        doc.close()
        return is_scanned, total_chars
    except Exception as e:
        logging.error(f"Lỗi kiểm tra file {file_path}: {e}")
        return False, 0

def convert_to_digital(file_path):
    """Thực hiện OCR và ghi đè file gốc."""
    logging.info(f"⚙️ Đang thực hiện OCR cho: {file_path.name}")
    try:
        # Chuyển PDF thành ảnh với DPI cao để đảm bảo độ chính xác cho y tế
        images = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)
        pdf_writer = fitz.open()
        
        for i, img in enumerate(images):
            # OCR đa ngôn ngữ Việt + Anh
            page_pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, extension='pdf', lang='vie+eng')
            with fitz.open("pdf", page_pdf_bytes) as page_doc:
                pdf_writer.insert_pdf(page_doc)
            
            if (i + 1) % 10 == 0:
                logging.info(f"   [+] Đã xử lý {i+1}/{len(images)} trang...")

        # Ghi đè file gốc
        pdf_writer.save(file_path, incremental=False, encryption=fitz.PDF_ENCRYPT_KEEP)
        pdf_writer.close()
        logging.info(f"✅ Hoàn thành số hóa: {file_path.name}")
        return True
    except Exception as e:
        logging.error(f"❌ Lỗi khi OCR file {file_path.name}: {e}")
        return False

def main():
    root_path = Path(BASE_DIR)
    if not root_path.exists():
        logging.critical(f"Không tìm thấy thư mục: {BASE_DIR}")
        return

    all_pdfs = list(root_path.rglob("*.pdf"))
    logging.info(f"🚀 Tìm thấy {len(all_pdfs)} file PDF. Bắt đầu phân loại và xử lý...")
    
    scanned_count = 0
    digital_count = 0

    for pdf_file in all_pdfs:
        is_scanned, char_count = is_scanned_pdf(pdf_file)
        relative_path = pdf_file.relative_to(root_path.parent)
        
        if is_scanned:
            scanned_count += 1
            logging.warning(f"🔍 SCANNED detected: {relative_path} ({char_count} chars)")
            convert_to_digital(pdf_file)
        else:
            digital_count += 1
            logging.info(f"📄 DIGITAL (Skip): {relative_path}")

    logging.info("\n" + "="*50)
    logging.info("TỔNG KẾT QUY TRÌNH")
    logging.info(f"- Tổng số file quét: {len(all_pdfs)}")
    logging.info(f"- File Digital (Giữ nguyên): {digital_count}")
    logging.info(f"- File Scanned (Đã số hóa): {scanned_count}")
    logging.info(f"Chi tiết log: {log_file}")
    logging.info("="*50)

if __name__ == "__main__":
    main()