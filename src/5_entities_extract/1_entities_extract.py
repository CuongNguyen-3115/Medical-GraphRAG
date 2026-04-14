# import os
# import json
# import random
# import logging
# import time
# from datetime import datetime
# from google import genai
# from dotenv import load_dotenv

# # --- CẤU HÌNH ĐƯỜNG DẪN ---
# INPUT_PATH = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks(2)\medical_chunks_merged.json"
# OUTPUT_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\05_Entities"
# LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\5_extraction"
# ENV_PATH = r"C:\1. Project\2. DoAn_GraphRAG\.env" # Đảm bảo đường dẫn tới file .env của bạn

# # Tạo thư mục nếu chưa có
# os.makedirs(OUTPUT_DIR, exist_ok=True)
# os.makedirs(LOG_DIR, exist_ok=True)

# # --- THIẾT LẬP LOGGING ---
# log_file = os.path.join(LOG_DIR, f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
# )

# # --- LOAD API KEY & CLIENT ---
# load_dotenv(ENV_PATH)
# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# # Import prompt từ file hoặc biến (Giả sử bạn đã lưu vào biến)
# # Chú ý: Đảm bảo các biến {entity_types}, {input_text}, {tuple_delimiter}, v.v. khớp với format của bạn
# from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT

# # Cấu hình thực thể y khoa
# ENTITY_TYPES = "BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH, TÁC_DỤNG_PHỤ, BIẾN_CHỨNG, CHỐNG_CHỈ_ĐỊNH, CHỈ_SỐ_SINH_HỌC, ĐỐI_TƯỢNG_BỆNH_NHÂN, PHÂN_LOẠI_BỆNH, THỜI_GIAN_DIỄN_TIẾN"

# # --- CÁC HÀM XỬ LÝ ---

# def get_sampled_chunks(path):
#     """Lấy 10 chunk mẫu theo yêu cầu: 2 nhỏ, 3 vừa, 5 lớn."""
#     logging.info("Đang đọc file chunks và lấy mẫu thử nghiệm...")
#     with open(path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     # Sắp xếp theo token_count
#     sorted_data = sorted(data, key=lambda x: x['metadata']['token_count'])
    
#     # Chia nhóm
#     small_pool = sorted_data[:50]              # 50 cái nhỏ nhất
#     large_pool = sorted_data[-50:]             # 50 cái lớn nhất
#     mid_index = len(sorted_data) // 2
#     medium_pool = sorted_data[mid_index-25 : mid_index+25] # 50 cái ở giữa
    
#     samples = (
#         random.sample(small_pool, 2) + 
#         random.sample(medium_pool, 3) + 
#         random.sample(large_pool, 5)
#     )
#     return samples

# def run_extraction_with_reflection(chunk_text):
#     """Quy trình trích xuất kèm Gleaning (Self-reflection)"""
#     results = []
    
#     # Bước 1: Trích xuất lần đầu (Initial Extraction)
#     full_prompt = GRAPH_EXTRACTION_PROMPT.format(
#         entity_types=ENTITY_TYPES,
#         input_text=chunk_text,
#         tuple_delimiter="<|>",
#         record_delimiter="####",
#         completion_delimiter="[DONE]"
#     )
    
#     response = client.models.generate_content(
#         model="gemini-2.5-flash-lite",
#         contents=full_prompt
#     )
#     initial_output = response.text.strip()
#     results.append(initial_output)
    
#     # Bước 2: Gleaning (Vòng lặp thu thập thêm - Self-reflection)
#     # Theo bài báo, ta có thể chạy nhiều lần, ở đây ta chạy 1 lần Gleaning để tối ưu
#     max_gleanings = 1 
#     current_iteration = 0
    
#     history = [
#         {"role": "user", "content": full_prompt},
#         {"role": "model", "content": initial_output}
#     ]
    
#     while current_iteration < max_gleanings:
#         # Hỏi xem còn sót không (LOOP_PROMPT)
#         check_response = client.models.generate_content(
#             model="gemini-2.0-flash-lite",
#             contents=LOOP_PROMPT
#         )
        
#         if "YES" in check_response.text.upper():
#             logging.info(f"  --> Phát hiện thông tin bị sót. Đang trích xuất thêm (Lần {current_iteration+1})...")
#             # Nếu còn sót, yêu cầu trích xuất tiếp (CONTINUE_PROMPT)
#             glean_response = client.models.generate_content(
#                 model="gemini-2.0-flash-lite",
#                 contents=CONTINUE_PROMPT
#             )
#             results.append(glean_response.text.strip())
#             current_iteration += 1
#         else:
#             logging.info("  --> Model xác nhận đã trích xuất đầy đủ.")
#             break
            
#     return "\n".join(results)

# # --- LUỒNG CHẠY CHÍNH ---

# def main():
#     time.sleep(30)
#     try:
#         samples = get_sampled_chunks(INPUT_PATH)
#         logging.info(f"Bắt đầu trích xuất cho {len(samples)} chunks mẫu.")
        
#         for i, chunk in enumerate(samples):
#             chunk_id = chunk['chunk_id']
#             token_size = chunk['metadata']['token_count']
#             file_name = chunk['metadata']['source_file']
            
#             logging.info(f"[{i+1}/10] Đang xử lý Chunk: {chunk_id} | File: {file_name} | Tokens: {token_size}")
            
#             start_time = time.time()
#             try:
#                 # Thực hiện trích xuất
#                 extraction_result = run_extraction_with_reflection(chunk['content'])
                
#                 # Save Progress: Lưu từng chunk thành file JSON để giữ cấu trúc và metadata
#                 output_data = {
#                     "chunk_id": chunk_id,
#                     "metadata": chunk['metadata'],
#                     "extraction_raw": extraction_result
#                 }
                
#                 output_file = os.path.join(OUTPUT_DIR, f"extracted_{chunk_id}.json")
#                 with open(output_file, 'w', encoding='utf-8') as f:
#                     json.dump(output_data, f, ensure_ascii=False, indent=4)
                
#                 elapsed = time.time() - start_time
#                 logging.info(f"  --> Hoàn thành trong {elapsed:.2f}s. Đã lưu tại {os.path.basename(output_file)}")
                
#             except Exception as e:
#                 logging.error(f"  --> LỖI tại chunk {chunk_id}: {str(e)}")
#                 continue # Tiếp tục với chunk tiếp theo
                
#     except Exception as e:
#         logging.critical(f"Lỗi hệ thống: {str(e)}")

# if __name__ == "__main__":
#     main()
import os
import json
import random
import logging
import time
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_PATH = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks(2)\medical_chunks_merged.json"
OUTPUT_DIR = r"C:\1. Project\2. DoAn_GraphRAG\Data\05_Entities"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\5_extraction"
ENV_PATH = r"C:\1. Project\2. DoAn_GraphRAG\.env"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_file = os.path.join(LOG_DIR, f"extraction_groq_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
)

# --- LOAD API KEY & CLIENT ---
load_dotenv(ENV_PATH)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Model ưu tiên (70B cho chất lượng cao) và Model backup (8B cho tốc độ/hết hạn mức ngày)
PRIMARY_MODEL = os.getenv("GROQ_MODEL_ID_1")  # llama-3.3-70b-versatile
BACKUP_MODEL = os.getenv("GROQ_MODEL_ID_2")   # llama-3.1-8b-instant

# Import prompt của bạn (đã chuẩn hóa y khoa)
from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT
ENTITY_TYPES = "BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH"

# --- HÀM GỌI API AN TOÀN ---

def call_groq_safe(prompt, model_id):
    """Gọi API Groq với cơ chế xử lý lỗi 429 (Rate Limit)"""
    while True:
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_id,
                temperature=0.1, # Thấp để trích xuất chính xác
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate_limit" in err_msg.lower():
                logging.warning(f"⚠️ Chạm ngưỡng Rate Limit của Groq ({model_id}). Đang nghỉ 20s...")
                time.sleep(20) # Nghỉ để reset TPM/RPM
                continue
            else:
                logging.error(f"❌ Lỗi API không xác định: {err_msg}")
                return None

# --- QUY TRÌNH TRÍCH XUẤT ---

def run_extraction_with_reflection(chunk_text):
    """Quy trình trích xuất kèm Gleaning (Self-reflection) dùng Groq"""
    # Sử dụng 70B cho bước trích xuất chính để đảm bảo chất lượng y khoa
    
    # Bước 1: Initial Extraction
    full_prompt = GRAPH_EXTRACTION_PROMPT.format(
        entity_types=ENTITY_TYPES,
        input_text=chunk_text,
        tuple_delimiter="<|>",
        record_delimiter="####",
        completion_delimiter="[DONE]"
    )
    
    initial_output = call_groq_safe(full_prompt, PRIMARY_MODEL)
    if not initial_output: return ""

    # Bước 2: Self-Reflection (Gleaning)
    # Kiểm tra xem còn sót không
    check_prompt = f"{initial_output}\n\n{LOOP_PROMPT}"
    check_val = call_groq_safe(check_prompt, BACKUP_MODEL) # Dùng 8B cho bước check YES/NO để tiết kiệm TPM cho 70B
    
    final_results = [initial_output]
    
    if check_val and "YES" in check_val.upper():
        logging.info("  --> Phát hiện thông tin bị sót. Đang trích xuất thêm...")
        glean_prompt = f"{initial_output}\n\n{CONTINUE_PROMPT}"
        glean_output = call_groq_safe(glean_prompt, PRIMARY_MODEL)
        if glean_output:
            final_results.append(glean_output)
            
    return "\n".join(final_results)

def get_sampled_chunks(path):
    """Lấy 10 chunk mẫu theo yêu cầu: 2 nhỏ, 3 vừa, 5 lớn."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    sorted_data = sorted(data, key=lambda x: x['metadata']['token_count'])
    
    samples = (
        random.sample(sorted_data[:50], 2) + 
        random.sample(sorted_data[len(sorted_data)//2-25 : len(sorted_data)//2+25], 3) + 
        random.sample(sorted_data[-50:], 5)
    )
    return samples

# --- CHƯƠNG TRÌNH CHÍNH ---

def main():
    samples = get_sampled_chunks(INPUT_PATH)
    logging.info(f"Bắt đầu chạy thử nghiệm 10 chunk với Groq.")

    for i, chunk in enumerate(samples):
        chunk_id = chunk['chunk_id']
        logging.info(f"[{i+1}/10] Xử lý: {chunk_id} | Tokens: {chunk['metadata']['token_count']}")
        
        start_time = time.time()
        result = run_extraction_with_reflection(chunk['content'])
        
        if result:
            # Save Progress
            output_data = {
                "chunk_id": chunk_id,
                "metadata": chunk['metadata'],
                "extraction_raw": result,
                "model_used": PRIMARY_MODEL
            }
            output_file = os.path.join(OUTPUT_DIR, f"extracted_{chunk_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            
            logging.info(f"  --> Xong trong {time.time()-start_time:.2f}s.")
        
        # Với giới hạn TPM của Groq (12K), ta nên nghỉ một chút sau mỗi chunk
        time.sleep(5) 

if __name__ == "__main__":
    main()