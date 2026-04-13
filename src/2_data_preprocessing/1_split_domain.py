# # import pandas as pd
# # from google import genai
# # from google.genai import types
# # import os
# # import time
# # import json
# # import logging
# # from datetime import datetime
# # from dotenv import load_dotenv

# # # 1. Cấu hình đường dẫn và môi trường
# # load_dotenv()
# # BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
# # INPUT_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata.xlsx")
# # OUTPUT_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata.xlsx")
# # LOG_DIR = os.path.join(BASE_DIR, "logs")

# # # Tạo thư mục log nếu chưa có
# # if not os.path.exists(LOG_DIR):
# #     os.makedirs(LOG_DIR)

# # # 2. Thiết lập Logging
# # log_filename = f"normalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# # logging.basicConfig(
# #     level=logging.INFO,
# #     format='%(asctime)s - %(levelname)s - %(message)s',
# #     handlers=[
# #         logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8'),
# #         logging.StreamHandler()
# #     ]
# # )

# # # 3. Khởi tạo Gemini Client
# # client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# # MODEL_ID = "gemini-3.1-flash-lite-preview" # Cập nhật đúng ID model bạn sử dụng

# # SYSTEM_PROMPT = """
# # Bạn là chuyên gia phân loại dữ liệu y tế chuyên sâu. 
# # Dựa vào tiêu đề tài liệu, hãy phân loại chuyên khoa theo tiêu chuẩn y học:
# # - domain_l1: Chuyên khoa lớn (ví dụ: Nội khoa, Ngoại khoa, Nhi khoa, Sản khoa, Dược học, Truyền nhiễm, v.v.)
# # - domain_l2: Hệ cơ quan hoặc chuyên khoa sâu (ví dụ: Tim mạch, Thận - Tiết niệu, Hô hấp, Nội tiết, Da liễu, v.v.)

# # Yêu cầu: Trả về duy nhất định dạng JSON: {"domain_l1": "...", "domain_l2": "..."}
# # """

# # def process_title_with_gemini(title):
# #     """Gửi tiêu đề tới Gemini và nhận kết quả phân cấp."""
# #     try:
# #         response = client.models.generate_content(
# #             model=MODEL_ID,
# #             config=types.GenerateContentConfig(
# #                 system_instruction=SYSTEM_PROMPT,
# #                 response_mime_type='application/json',
# #                 temperature=0.1 # Để kết quả ổn định hơn
# #             ),
# #             contents=f"Tiêu đề: {title}"
# #         )
# #         return json.loads(response.text)
# #     except Exception as e:
# #         logging.error(f"Lỗi API khi xử lý tiêu đề '{title}': {str(e)}")
# #         return {"domain_l1": "Error", "domain_l2": "Error"}

# # def main():
# #     logging.info("--- BẮT ĐẦU QUÁ TRÌNH CHUẨN HÓA DOMAIN ---")
    
# #     if not os.path.exists(INPUT_PATH):
# #         logging.error(f"Không tìm thấy file Excel tại: {INPUT_PATH}")
# #         return

# #     # Đọc dữ liệu
# #     df = pd.read_excel(INPUT_PATH)
# #     logging.info(f"Đã nạp file thành công. Tổng số hàng: {len(df)}")

# #     l1_results = []
# #     l2_results = []

# #     # Vòng lặp xử lý
# #     for index, row in df.iterrows():
# #         title = str(row.get('title', ''))
# #         doc_id = row.get('Doc_ID', f"Line_{index}")
        
# #         if not title:
# #             logging.warning(f"Dòng {index}: Tiêu đề trống, bỏ qua.")
# #             l1_results.append("N/A")
# #             l2_results.append("N/A")
# #             continue

# #         logging.info(f"Đang xử lý {doc_id}: {title[:60]}...")
        
# #         # Gọi API
# #         start_time = time.time()
# #         result = process_title_with_gemini(title)
# #         elapsed_time = time.time() - start_time
        
# #         l1_results.append(result.get('domain_l1'))
# #         l2_results.append(result.get('domain_l2'))
        
# #         logging.info(f"Hoàn thành {doc_id} trong {elapsed_time:.2f}s. Kết quả: {result}")
        
# #         # Rate limiting: Nghỉ một chút để tránh overload API (tùy quota tài khoản)
# #         time.sleep(0.5)

# #     # Gán dữ liệu mới vào dataframe
# #     df['domain_l1'] = l1_results
# #     df['domain_l2'] = l2_results

# #     # Lưu kết quả
# #     try:
# #         df.to_excel(OUTPUT_PATH, index=False)
# #         logging.info(f"Đã lưu kết quả thành công vào: {OUTPUT_PATH}")
# #     except Exception as e:
# #         logging.error(f"Không thể lưu file kết quả: {str(e)}")

# #     logging.info("--- KẾT THÚC QUÁ TRÌNH ---")

# # if __name__ == "__main__":
# #     main()

# import pandas as pd
# from groq import Groq
# import os
# import time
# import json
# import logging
# from datetime import datetime
# from dotenv import load_dotenv

# # 1. Cấu hình đường dẫn và môi trường
# load_dotenv()
# BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
# INPUT_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata.xlsx")
# OUTPUT_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata.xlsx")
# LOG_DIR = os.path.join(BASE_DIR, "logs")

# # Tạo thư mục log nếu chưa có
# if not os.path.exists(LOG_DIR):
#     os.makedirs(LOG_DIR)

# # 2. Thiết lập Logging
# log_filename = f"normalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8'),
#         logging.StreamHandler()
#     ]
# )

# # 3. Khởi tạo Groq Client
# # Đảm bảo GROQ_API_KEY và GROQ_MODEL_ID có trong file .env
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# MODEL_ID = os.getenv("GROQ_MODEL_ID_1") 

# SYSTEM_PROMPT = """
# Bạn là chuyên gia phân loại dữ liệu y tế chuyên sâu. 
# Dựa vào tiêu đề tài liệu, hãy phân loại chuyên khoa theo tiêu chuẩn y học:
# - domain_l1: Chuyên khoa lớn (ví dụ: Nội khoa, Ngoại khoa, Nhi khoa, Sản khoa, Dược học, Truyền nhiễm, v.v.)
# - domain_l2: Hệ cơ quan hoặc chuyên khoa sâu (ví dụ: Tim mạch, Thận - Tiết niệu, Hô hấp, Nội tiết, Da liễu, v.v.)

# Yêu cầu: Trả về duy nhất định dạng JSON: {"domain_l1": "...", "domain_l2": "..."}
# """

# def process_title_with_groq(title):
#     """Gửi tiêu đề tới Groq và nhận kết quả phân cấp."""
#     try:
#         chat_completion = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "system",
#                     "content": SYSTEM_PROMPT,
#                 },
#                 {
#                     "role": "user",
#                     "content": f"Tiêu đề: {title}",
#                 }
#             ],
#             model=MODEL_ID,
#             # Chế độ JSON giúp output luôn tuân thủ định dạng
#             response_format={"type": "json_object"},
#             temperature=0.1
#         )
        
#         response_text = chat_completion.choices[0].message.content
#         return json.loads(response_text)
#     except Exception as e:
#         logging.error(f"Lỗi API Groq khi xử lý tiêu đề '{title}': {str(e)}")
#         return {"domain_l1": "Error", "domain_l2": "Error"}

# def main():
#     logging.info("--- BẮT ĐẦU QUÁ TRÌNH CHUẨN HÓA DOMAIN (GROQ) ---")
    
#     if not os.path.exists(INPUT_PATH):
#         logging.error(f"Không tìm thấy file Excel tại: {INPUT_PATH}")
#         return

#     # Đọc dữ liệu
#     try:
#         df = pd.read_excel(INPUT_PATH)
#         logging.info(f"Đã nạp file thành công. Tổng số hàng: {len(df)}")
#     except Exception as e:
#         logging.error(f"Lỗi khi đọc file Excel: {str(e)}")
#         return

#     l1_results = []
#     l2_results = []

#     # Vòng lặp xử lý
#     for index, row in df.iterrows():
#         title = str(row.get('title', ''))
#         doc_id = row.get('Doc_ID', f"Line_{index}")
        
#         if not title or title.lower() == 'nan':
#             logging.warning(f"Dòng {index}: Tiêu đề trống, bỏ qua.")
#             l1_results.append("N/A")
#             l2_results.append("N/A")
#             continue

#         logging.info(f"Đang xử lý {doc_id}: {title[:60]}...")
        
#         # Gọi API Groq
#         start_time = time.time()
#         result = process_title_with_groq(title)
#         elapsed_time = time.time() - start_time
        
#         l1_results.append(result.get('domain_l1', 'Unknown'))
#         l2_results.append(result.get('domain_l2', 'Unknown'))
        
#         logging.info(f"Hoàn thành {doc_id} trong {elapsed_time:.2f}s. Kết quả: {result}")
        
#         # Tốc độ xử lý của Groq rất nhanh, 
#         # nhưng vẫn nên để sleep ngắn nếu số lượng bản ghi cực lớn để tránh Rate Limit của gói Free
#         time.sleep(0.2)

#     # Gán dữ liệu mới vào dataframe
#     df['domain_l1'] = l1_results
#     df['domain_l2'] = l2_results

#     # Lưu kết quả
#     try:
#         df.to_excel(OUTPUT_PATH, index=False)
#         logging.info(f"Đã lưu kết quả thành công vào: {OUTPUT_PATH}")
#     except Exception as e:
#         logging.error(f"Không thể lưu file kết quả: {str(e)}")

#     logging.info("--- KẾT THÚC QUÁ TRÌNH ---")

# if __name__ == "__main__":
#     main()

import pandas as pd
from groq import Groq
import os
import time
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# 1. Cấu hình
load_dotenv()
BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
FILE_PATH = os.path.join(BASE_DIR, "Data", "Medical_Metadata.xlsx")
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_filename = f"normalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 2. Khởi tạo Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
PRIMARY_MODEL = os.getenv("GROQ_MODEL_ID_1")
BACKUP_MODEL = os.getenv("GROQ_MODEL_ID_2")

SYSTEM_PROMPT = """
Bạn là chuyên gia phân loại dữ liệu y tế chuyên sâu. 
Dựa vào tiêu đề tài liệu, hãy phân loại chuyên khoa theo tiêu chuẩn y học:
- domain_l1: Chuyên khoa lớn (ví dụ: Nội khoa, Ngoại khoa, Nhi khoa, Sản khoa, Dược học, Truyền nhiễm, v.v.)
- domain_l2: Hệ cơ quan hoặc chuyên khoa sâu (ví dụ: Tim mạch, Thận - Tiết niệu, Hô hấp, Nội tiết, Da liễu, v.v.)
Yêu cầu: Trả về duy nhất định dạng JSON: {"domain_l1": "...", "domain_l2": "..."}
"""

def call_groq_api(title, model_id):
    """Hàm gọi API dùng chung cho cả 2 model."""
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tiêu đề: {title}"}
        ],
        model=model_id,
        response_format={"type": "json_object"},
        temperature=0.1
    )
    return json.loads(chat_completion.choices[0].message.content)

def process_with_fallback(title):
    """Thử model chính, nếu lỗi quota/hệ thống thì thử model backup."""
    try:
        # Thử model chính
        return call_groq_api(title, PRIMARY_MODEL), PRIMARY_MODEL
    except Exception as e:
        error_msg = str(e).lower()
        if "rate_limit" in error_msg or "quota" in error_msg:
            logging.warning(f"Model chính hết quota, đang thử model backup {BACKUP_MODEL}...")
            try:
                return call_groq_api(title, BACKUP_MODEL), BACKUP_MODEL
            except Exception as e2:
                logging.error(f"Cả 2 model đều thất bại: {str(e2)}")
                return None, None
        else:
            logging.error(f"Lỗi không xác định: {str(e)}")
            return None, None

def main():
    logging.info("--- BẮT ĐẦU QUÁ TRÌNH (CHẾ ĐỘ GHI TRỰC TIẾP & BACKUP) ---")
    
    if not os.path.exists(FILE_PATH):
        logging.error(f"Không tìm thấy file: {FILE_PATH}")
        return

    # Đọc file
    df = pd.read_excel(FILE_PATH)
    
    # Khởi tạo cột nếu chưa có
    if 'domain_l1' not in df.columns:
        df['domain_l1'] = None
    if 'domain_l2' not in df.columns:
        df['domain_l2'] = None

    total_rows = len(df)
    processed_count = 0

    for index, row in df.iterrows():
        # Kiểm tra xem dòng này đã được xử lý chưa (Checkpoint)
        if pd.notna(row.get('domain_l1')) and row.get('domain_l1') != "Error" and row.get('domain_l1') != "N/A":
            continue

        title = str(row.get('title', ''))
        if not title or title.lower() == 'nan':
            df.at[index, 'domain_l1'] = "N/A"
            df.at[index, 'domain_l2'] = "N/A"
            continue

        logging.info(f"[{index+1}/{total_rows}] Đang xử lý: {title[:50]}...")
        
        start_time = time.time()
        result, used_model = process_with_fallback(title)
        elapsed = time.time() - start_time

        if result:
            df.at[index, 'domain_l1'] = result.get('domain_l1')
            df.at[index, 'domain_l2'] = result.get('domain_l2')
            logging.info(f"Thành công ({used_model}) trong {elapsed:.2f}s: {result}")
            
            # Ghi trực tiếp vào file sau mỗi dòng thành công
            try:
                df.to_excel(FILE_PATH, index=False)
            except Exception as e:
                logging.error(f"Lỗi khi ghi file (vui lòng đóng file Excel nếu đang mở): {e}")
        else:
            logging.error(f"Dòng {index} thất bại hoàn toàn. Dừng tiến trình để kiểm tra quota.")
            break # Dừng vòng lặp nếu cả 2 model đều lỗi để tránh lãng phí vòng lặp

        processed_count += 1
        time.sleep(0.3) # Tránh spam API quá nhanh

    logging.info(f"--- HOÀN THÀNH. Đã xử lý thêm {processed_count} dòng mới ---")

if __name__ == "__main__":
    main()