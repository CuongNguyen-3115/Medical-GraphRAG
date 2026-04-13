# import os
# import json
# import re
# from dotenv import load_dotenv
# import fitz  # PyMuPDF
# import pymupdf4llm
# from pathlib import Path
# from datetime import datetime
# import sys
# from google import genai
# from google.genai import types

# # Setup Path
# ROOT_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG")
# sys.path.append(str(ROOT_DIR / "src"))

# from utils.evaluator_parser import evaluate_cleaning_quality, estimate_info_loss

# # Chỉ định đường dẫn tuyệt đối tới file .env để đảm bảo không bị nhầm lẫn
# env_path = Path(r"C:\1. Project\2. DoAn_GraphRAG\.env")
# load_dotenv(dotenv_path=env_path)

# # Cấu hình Gemini
# API_KEY = os.getenv("GEMINI_API_KEY")
# MODEL_ID = os.getenv("MODEL_ID")
# client = genai.Client(api_key=API_KEY)

# VLM_PROMPT = """
# Bạn là một trợ lý số hóa tài liệu y khoa. 
# Trang này chứa sơ đồ hoặc bảng biểu phức tạp. Hãy:
# 1. Mô tả chi tiết sơ đồ dưới dạng văn bản logic hoặc bảng Markdown.
# 2. Giữ nguyên các thuật ngữ chuyên môn y tế.
# 3. Không bao gồm số trang hay ghi chú ngoài lề.
# """

# def is_complex_page(page):
#     """
#     Kiểm tra trang có phức tạp không dựa trên số lượng ảnh và bản vẽ (vector).
#     Phù hợp để phát hiện sơ đồ flowchart.
#     """
#     img_list = page.get_images(full=True)
#     drawings = page.get_drawings()
#     # Nếu có hình ảnh hoặc quá nhiều nét vẽ vector (thường là sơ đồ)
#     return len(img_list) > 0 or len(drawings) > 20

# def clean_page_content(text):
#     """Xóa số trang rác nhưng giữ lại cấu trúc."""
#     # Xóa dòng chỉ chứa chữ số (thường là số trang ở đầu/cuối)
#     lines = text.split('\n')
#     cleaned_lines = [line for line in lines if not re.match(r'^\s*\d+\s*$', line)]
#     return '\n'.join(cleaned_lines)

# def process_workflow_hybrid(input_dir, output_dir, log_dir, threshold=80):
#     output_dir.mkdir(parents=True, exist_ok=True)
#     log_dir.mkdir(parents=True, exist_ok=True)

#     pdf_files = list(input_dir.glob("*.pdf"))
#     print(f"🚀 Chế độ Hybrid: Đang xử lý {len(pdf_files)} file...")

#     for pdf_path in pdf_files:
#         full_md_with_markers = []
#         try:
#             # Mở file bằng PyMuPDF để kiểm tra từng trang
#             doc = fitz.open(pdf_path)
            
#             for page_index in range(len(doc)):
#                 page = doc[page_index]
#                 page_num = page_index + 1
                
#                 if is_complex_page(page):
#                     print(f"  - {pdf_path.name} | Trang {page_num}: Phát hiện sơ đồ/ảnh -> Gọi Gemini VLM")
#                     # Render trang thành ảnh để gửi Gemini
#                     pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
#                     img_bytes = pix.tobytes("png")
                    
#                     response = client.models.generate_content(
#                         model=MODEL_ID,
#                         contents=[VLM_PROMPT, types.Part.from_bytes(data=img_bytes, mime_type="image/png")]
#                     )
#                     page_text = response.text
#                 else:
#                     # Trang bình thường -> Dùng pymupdf4llm cho nhẹ
#                     # page_chunks=True giúp lấy text của đúng trang đó
#                     md_data = pymupdf4llm.to_markdown(str(pdf_path), pages=[page_index])
#                     page_text = clean_page_content(md_data)

#                 # Chèn Page Marker ẩn để sau này chunking biết trang nào
#                 full_md_with_markers.append(f"{page_text}\n\n")

#             final_md_text = "\n\n".join(full_md_with_markers)

#             # Đánh giá chất lượng (Pipeline cũ của bạn)
#             quality_score, q_metrics = evaluate_cleaning_quality(final_md_text)
#             loss_metrics = estimate_info_loss(pdf_path, final_md_text)
            
#             # Ghi Log
#             log_data = {
#                 "timestamp": datetime.now().isoformat(),
#                 "filename": pdf_path.name,
#                 "strategy": "Hybrid_VLM_PyMuPDF",
#                 "quality_score": round(quality_score, 2),
#                 "metrics": q_metrics,
#                 "status": "PASSED" if quality_score >= threshold else "FAILED"
#             }
            
#             with open(log_dir / f"{pdf_path.stem}.json", "w", encoding="utf-8") as lf:
#                 json.dump(log_data, lf, ensure_ascii=False, indent=4)

#             # Lưu file đạt chuẩn
#             if quality_score >= threshold:
#                 output_file = output_dir / f"{pdf_path.stem}.md"
#                 with open(output_file, "w", encoding="utf-8") as f:
#                     f.write(final_md_text)
#                 print(f"✅ {pdf_path.name} - Hoàn tất (Score: {quality_score:.2f})")

#         except Exception as e:
#             print(f"⚠️ Lỗi xử lý {pdf_path.name}: {e}")

# if __name__ == "__main__":
#     INPUT = ROOT_DIR / "Data" / "03_Markdown" / "1_PDF_Pruning"
#     OUTPUT = ROOT_DIR / "Data" / "03_Markdown" / "2_Markdown_Normalized"
#     LOGS = ROOT_DIR / "logs" / "3_data_convert"
    
#     process_workflow_hybrid(INPUT, OUTPUT, LOGS)

import os
import json
import re
import time
from dotenv import load_dotenv
import fitz  # PyMuPDF
import pymupdf4llm
from pathlib import Path
from datetime import datetime
import sys
from google import genai
from google.genai import types

# Setup Path
ROOT_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG")
sys.path.append(str(ROOT_DIR / "src"))

from utils.evaluator_parser import evaluate_cleaning_quality, estimate_info_loss

# Load .env
env_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Cấu hình Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# Danh sách Model Rotation để backup
MODEL_POOL = [
    os.getenv("MODEL_ID_1", "gemini-3.1-flash-lite-preview"),
    os.getenv("MODEL_ID_2", "gemini-2.5-flash"),
    os.getenv("MODEL_ID_3", "gemini-3-flash-preview"),
    os.getenv("MODEL_ID_4", "gemini-2.5-flash-lite")
]

VLM_PROMPT = """
Bạn là một trợ lý số hóa tài liệu y khoa. 
Trang này chứa sơ đồ hoặc bảng biểu phức tạp. Hãy:
1. Mô tả chi tiết sơ đồ dưới dạng văn bản logic hoặc bảng Markdown.
2. Giữ nguyên các thuật ngữ chuyên môn y tế.
3. Không bao gồm số trang hay ghi chú ngoài lề.
"""

def is_complex_page(page):
    img_list = page.get_images(full=True)
    drawings = page.get_drawings()
    return len(img_list) > 0 or len(drawings) > 20

def clean_page_content(text):
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if not re.match(r'^\s*\d+\s*$', line)]
    return '\n'.join(cleaned_lines)

def call_gemini_with_fallback(img_bytes):
    """Thử lần lượt các model trong POOL nếu gặp lỗi Quota."""
    for model_id in MODEL_POOL:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[VLM_PROMPT, types.Part.from_bytes(data=img_bytes, mime_type="image/png")]
            )
            return response.text, model_id
        except Exception as e:
            if "429" in str(e) or "resource_exhausted" in str(e).lower():
                print(f"   ⚠️ Model {model_id} hết quota, đang chuyển sang model tiếp theo...")
                continue
            else:
                raise e # Nếu là lỗi khác (như API Key) thì dừng lại
    return None, None

def process_workflow_hybrid(input_dir, output_dir, log_dir, threshold=80):
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))
    print(f"🚀 Chế độ Hybrid Rotation: Đang xử lý {len(pdf_files)} file...")

    for pdf_path in pdf_files:
        full_md_with_markers = []
        used_models = set()
        
        try:
            doc = fitz.open(pdf_path)
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_num = page_index + 1
                
                if is_complex_page(page):
                    print(f"  - {pdf_path.name} | Trang {page_num}: Gọi VLM...")
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("png")
                    
                    page_text, model_used = call_gemini_with_fallback(img_bytes)
                    if not page_text:
                        print(f"   ❌ Thất bại: Tất cả model đều hết Quota tại trang {page_num}")
                        page_text = "[[LỖI TRÍCH XUẤT VLM]]"
                    else:
                        used_models.add(model_used)
                else:
                    md_data = pymupdf4llm.to_markdown(str(pdf_path), pages=[page_index])
                    page_text = clean_page_content(md_data)

                full_md_with_markers.append(f"{page_text}\n\n")

            final_md_text = "\n\n".join(full_md_with_markers)
            quality_score, q_metrics = evaluate_cleaning_quality(final_md_text)
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "filename": pdf_path.name,
                "strategy": "Hybrid_Rotation",
                "models_used": list(used_models),
                "quality_score": round(quality_score, 2),
                "status": "PASSED" if quality_score >= threshold else "FAILED"
            }
            
            with open(log_dir / f"{pdf_path.stem}.json", "w", encoding="utf-8") as lf:
                json.dump(log_data, lf, ensure_ascii=False, indent=4)

            if quality_score >= threshold:
                with open(output_dir / f"{pdf_path.stem}.md", "w", encoding="utf-8") as f:
                    f.write(final_md_text)
                print(f"✅ {pdf_path.name} - Xong (Score: {quality_score:.2f})")

        except Exception as e:
            print(f"⚠️ Lỗi nghiêm trọng {pdf_path.name}: {e}")

if __name__ == "__main__":
    INPUT = ROOT_DIR / "Data" / "03_Markdown" / "1_PDF_Pruning"
    OUTPUT = ROOT_DIR / "Data" / "03_Markdown" / "2_Markdown_Normalized"
    LOGS = ROOT_DIR / "logs" / "3_data_convert"
    
    process_workflow_hybrid(INPUT, OUTPUT, LOGS)