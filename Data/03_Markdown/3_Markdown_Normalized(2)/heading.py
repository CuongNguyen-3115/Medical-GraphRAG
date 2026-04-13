# import os
# from pathlib import Path
# from dotenv import load_dotenv
# from google import genai
# from google.genai import types

# # 1. Cấu hình đường dẫn
# ROOT_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG")
# INPUT_FILE = ROOT_DIR / "Data" / "03_Markdown" / "3_Markdown_Normalized(2)" / "DOC_016.md"
# OUTPUT_FILE = ROOT_DIR / "Data" / "03_Markdown" / "3_Markdown_Normalized(2)" / "DOC_016_Structured.md"

# # 2. Load môi trường
# load_dotenv(dotenv_path=ROOT_DIR / ".env")
# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# MODEL_ID = os.getenv("MODEL_ID_2") # Sử dụng gemini-3.1-flash-lite-preview để có độ chính xác cao nhất

# # 3. Prompt "siêu chắc" để xác định Header
# SYSTEM_PROMPT = """
# Bạn là một chuyên gia cấu trúc tài liệu y khoa. Nhiệm vụ của bạn là đọc nội dung Markdown và chuẩn hóa hệ thống tiêu đề (Headers) lên đến cấp 4 (####).

# QUY TẮC XÁC ĐỊNH HEADER:
# 1. Header phải là một cụm từ ngắn gọn, mang tính chất tóm tắt cho nội dung phía dưới.
# 2. Cấu trúc Header y khoa thường là: 1. -> 1.1. -> 1.1.1. -> 1.1.1.1.
# 3. LOẠI TRỪ (CRITICAL): Nếu một dòng bắt đầu bằng số (ví dụ: "5. Khi bắt đầu...") nhưng là một câu dài, chứa nội dung hướng dẫn hoặc giải thích, thì ĐÓ LÀ NỘI DUNG, không phải tiêu đề. Tuyệt đối không thêm dấu # vào đầu những dòng này.
# 4. ĐỊNH DẠNG:
#    - Cấp 1 (Tên chương/bài): #
#    - Cấp 2 (Mục lớn): ## 
#    - Cấp 3 (Mục con): ###
#    - Cấp 4 (Chi tiết nhỏ): ####

# Hãy giữ nguyên toàn bộ nội dung văn bản, chỉ bổ sung hoặc sửa lại các dấu # ở đầu các dòng thực sự là tiêu đề.
# """

# def structure_markdown():
#     # Tạo thư mục output nếu chưa có
#     OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

#     if not INPUT_FILE.exists():
#         print(f"❌ Không tìm thấy file: {INPUT_FILE}")
#         return

#     print(f"📖 Đang đọc file: {INPUT_FILE.name}")
#     with open(INPUT_FILE, "r", encoding="utf-8") as f:
#         content = f.read()

#     print("🚀 Đang gửi dữ liệu tới Gemini để phân tích cấu trúc...")
    
#     try:
#         # Sử dụng mô hình có context window lớn để xử lý cả file
#         response = client.models.generate_content(
#             model=MODEL_ID,
#             config=types.GenerateContentConfig(
#                 system_instruction=SYSTEM_PROMPT,
#                 temperature=0.1, # Để kết quả ổn định, không sáng tạo quá mức
#             ),
#             contents=[content]
#         )

#         structured_content = response.text

#         with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#             f.write(structured_content)
        
#         print(f"✅ Đã lưu file cấu trúc mới tại: {OUTPUT_FILE}")

#     except Exception as e:
#         print(f"❌ Lỗi khi gọi API: {e}")

# if __name__ == "__main__":
#     structure_markdown()

import os
import time
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# 1. Cấu hình đường dẫn
ROOT_DIR = Path(r"C:\1. Project\2. DoAn_GraphRAG")
INPUT_FILE = ROOT_DIR / "Data" / "03_Markdown" / "3_Markdown_Normalized(2)" / "DOC_016.md"
OUTPUT_DIR = ROOT_DIR / "Data" / "03_Markdown" / "3_Markdown_Normalized(2)"
OUTPUT_FILE = OUTPUT_DIR / "DOC_016_Groq_Structured.md"

# 2. Load môi trường và cấu hình Groq
load_dotenv(dotenv_path=ROOT_DIR / ".env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_ID = "groq/compound-mini" 

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
Bạn là một chuyên gia cấu trúc tài liệu y khoa chuyên nghiệp.
Nhiệm vụ: Đọc văn bản Markdown và chuẩn hóa hệ thống tiêu đề (Headers) lên đến cấp 4 (####).

QUY TẮC CƠ BẢN:
1. Xác định Header dựa trên logic phân cấp y khoa: 1. -> 2. -> 2.1. -> 2.1.1. -> 2.1.1.1.
2. Cấp độ tương ứng:
   - # (Tiêu đề chính/Chương)
   - ## (Mục lớn - ví dụ: 2. ĐẶC ĐIỂM...)
   - ### (Mục con - ví dụ: 2.1. Thời kỳ...)
   - #### (Mục chi tiết - ví dụ: 2.1.1. Giai đoạn...)

QUY TẮC LOẠI TRỪ (QUAN TRỌNG):
- Chỉ đánh dấu # cho những dòng là TIÊU ĐỀ (ngắn gọn, tóm tắt ý chính).
- KHÔNG đánh dấu # cho các câu nội dung bắt đầu bằng số. 
  Ví dụ: "5. Khi bắt buộc phải đi khám... phải đặt lịch hẹn..." -> Đây là NỘI DUNG, giữ nguyên, KHÔNG thêm #.
- Giữ nguyên toàn bộ nội dung văn bản bên dưới, không tóm tắt hay lược bỏ.
"""

def split_and_group_content(text, max_chars=8000):
    """
    Chia nhỏ theo Header ## nhưng gộp lại thành các nhóm khoảng 15k ký tự (~4k-5k tokens)
    để tối ưu giới hạn 250 Requests/Day.
    """
    sections = re.split(r'(?=\n## )', text)
    batches = []
    current_batch = ""

    for section in sections:
        if len(current_batch) + len(section) < max_chars:
            current_batch += section
        else:
            if current_batch:
                batches.append(current_batch.strip())
            current_batch = section
            
    if current_batch:
        batches.append(current_batch.strip())
    return batches

def structure_with_groq_batch():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        print(f"❌ Không tìm thấy file: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Chia nhỏ nội dung thành các batch lớn (khoảng 4-5k tokens mỗi batch)
    batches = split_and_group_content(content)
    print(f"🚀 Model: {MODEL_ID} | Đã chia thành {len(batches)} batch để xử lý.")

    final_content = []
    start_time = time.time()

    for i, batch in enumerate(batches):
        print(f"⏳ Đang xử lý batch {i+1}/{len(batches)}... ({len(batch)} ký tự)")
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": batch}
                ],
                temperature=0.1,
                max_tokens=8192 # Tăng lên để chứa đủ kết quả của batch lớn
            )

            final_content.append(completion.choices[0].message.content)

            # Khống chế RPM (30) và TPM (70K)
            # Với batch lớn, nghỉ 10s là cực kỳ an toàn cho cả RPM và TPM
            if i < len(batches) - 1:
                print("💤 Nghỉ 5 giây để bảo vệ Quota...")
                time.sleep(5)

        except Exception as e:
            print(f"❌ Lỗi tại batch {i+1}: {e}")
            if "429" in str(e):
                print("🛑 Đã chạm ngưỡng Quota, nghỉ 60s...")
                time.sleep(60)

    # Lưu kết quả hợp nhất
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_content))
    
    end_time = time.time()
    print(f"✅ Hoàn tất! Thời gian: {end_time - start_time:.2f}s")
    print(f"📂 Kết quả: {OUTPUT_FILE}")

if __name__ == "__main__":
    structure_with_groq_batch()