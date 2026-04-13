import os
import glob
import json
import logging
import io
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==========================================
# CẤU HÌNH HỆ THỐNG
# ==========================================
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = os.getenv("MODEL_ID")

PDF_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG\Data\03_Markdown\1_PDF_Pruning")
OUTPUT_JSON = Path(r"C:\1. Project\2. DoAn_GraphRAG\Data\abbreviations.json")
LOG_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG\logs\4_vlm_extraction")
MAX_PAGES_PER_DOC = 15 # Giới hạn cứng để bảo vệ token

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_DIR / "vlm_process.log", encoding='utf-8'), logging.StreamHandler()]
)

client = genai.Client(api_key=API_KEY)

# ==========================================
# PROMPT CHIẾN THUẬT CHO VLM
# ==========================================
SYSTEM_PROMPT = """
Bạn là chuyên gia số hóa tài liệu y khoa. Phân tích hình ảnh trang PDF và trích xuất danh mục từ viết tắt.

QUY TẮC TRÍCH XUẤT:
1. Nhận diện bảng:
   - Nếu bảng có 2 cột: [Từ viết tắt] | [Nghĩa].
   - Nếu bảng có 3 cột: [Từ viết tắt] | [Tiếng Anh] | [Nghĩa tiếng Việt] -> BỎ QUA cột tiếng Anh, chỉ lấy cột 1 và cột 3.
2. Tự động dừng (Stop Signal):
   - Nếu trang hiện tại KHÔNG chứa danh mục viết tắt (ví dụ: là mục lục, lời nói đầu, hoặc đã vào nội dung Chương 1).
   - Nếu đã hết danh sách bảng.
   - Khi đó, đặt "should_continue_scan": false.

ĐẦU RA JSON:
{
  "is_abbreviation_page": true/false,
  "should_continue_scan": true/false,
  "data": { "TỪ VIẾT TẮT": "Nghĩa tiếng Việt đầy đủ" }
}
"""

def process_single_pdf(pdf_path):
    """Xử lý một file PDF: Chuyển trang thành ảnh -> VLM -> Cập nhật Dict."""
    abbreviations = {}
    try:
        doc = fitz.open(pdf_path)
        logging.info(f">>> Bắt đầu: {pdf_path.name} ({doc.page_count} trang)")

        for page_num in range(min(MAX_PAGES_PER_DOC, doc.page_count)):
            page = doc.load_page(page_num)
            # Render ảnh 200 DPI để AI đọc rõ chữ nhỏ
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            
            logging.info(f"  - Đang phân tích trang {page_num + 1}...")
            
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    SYSTEM_PROMPT,
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text)
            
            if result.get("is_abbreviation_page"):
                page_data = result.get("data", {})
                abbreviations.update(page_data)
                logging.info(f"    + Tìm thấy {len(page_data)} từ.")

            if not result.get("should_continue_scan", True):
                logging.info(f"  ! Tín hiệu dừng nhận được tại trang {page_num + 1}. Chuyển file tiếp theo.")
                break
        
        doc.close()
    except Exception as e:
        logging.error(f"Lỗi khi xử lý {pdf_path.name}: {e}")
    
    return abbreviations

def main():
    final_dict = {}
    
    # Load dữ liệu cũ nếu có để chạy nối tiếp
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            final_dict = json.load(f)

    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        logging.error(f"Không tìm thấy file PDF nào tại {PDF_DIR}")
        return

    logging.info(f"Tìm thấy {len(pdf_files)} file. Bắt đầu quét VLM...")

    for pdf_file in pdf_files:
        file_results = process_single_pdf(pdf_file)
        final_dict.update(file_results)

    # Lưu kết quả cuối cùng
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_dict, f, ensure_ascii=False, indent=4)
    
    logging.info(f"=== HOÀN TẤT: Tổng cộng {len(final_dict)} thực thể trong Dictionary ===")

if __name__ == "__main__":
    main()