import os
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path

# 1. Setup môi trường
env_path = Path(r"C:\1. Project\2. DoAn_GraphRAG\.env")
load_dotenv(dotenv_path=env_path)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = os.getenv("MODEL_ID_1")

# 2. Đường dẫn file
pdf_path = r"C:\1. Project\2. DoAn_GraphRAG\Data\03_Markdown\1_PDF_Pruning\DOC_016.pdf"
page_index = 32  # Trang 53 trong PDF (index bắt đầu từ 0)

def demo_extract_flowchart():
    # 3. Mở PDF và trích xuất trang 53 dưới dạng ảnh
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Tăng độ nét
    img_bytes = pix.tobytes("png")

    # 4. Prompt chuyên dụng để chuyển sơ đồ thành Markdown logic
    prompt = """
    Phân tích sơ đồ trong trang tài liệu y tế này. 
    Hãy chuyển đổi sơ đồ thành định dạng Markdown theo quy tắc:
    1. Sử dụng các đề mục (###) cho các bước chính.
    2. Sử dụng danh sách có thứ tự hoặc các mũi tên (->) để thể hiện luồng quyết định (Decision Flow).
    3. Nếu có bảng trong sơ đồ, hãy trích xuất thành Markdown Table.
    4. Giữ nguyên thuật ngữ y khoa chuyên môn.
    """

    # 5. Gọi Gemini
    print(f"🚀 Đang gửi trang {page_index + 1} của DOC_016 tới Gemini...")
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[prompt, types.Part.from_bytes(data=img_bytes, mime_type="image/png")]
    )

    # 6. Hiển thị kết quả
    print("\n--- KẾT QUẢ MARKDOWN DỰ KIẾN ---")
    print(response.text)
    print("--------------------------------")

if __name__ == "__main__":
    demo_extract_flowchart()