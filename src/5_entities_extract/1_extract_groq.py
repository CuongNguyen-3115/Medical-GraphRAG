import os
import json
import logging
import sys
import time
import re
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Import prompt (Đảm bảo file prompts.py nằm cùng thư mục)
from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT

# --- CẤU HÌNH ĐƯỜNG DẪN TỔNG ---
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities"
LOG_DIR = r"C:\1. Project\ĐATN\logs\6_entities_extract"
ENV_PATH = r"C:\1. Project\ĐATN\.env"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_file = os.path.join(LOG_DIR, f"mass_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

# --- LOAD API KEY & CLIENT ---
load_dotenv(ENV_PATH)
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    max_retries=0  # Quan trọng: Đặt bằng 0 để catch được lỗi 429 ngay lập tức
)

# --- QUẢN LÝ TÀI NGUYÊN MODEL TỪ .ENV ---
# Danh sách model thông minh (Dùng cho trích xuất chính)
EXTRACTION_MODELS = [
    os.getenv("GROQ_MODEL_ID_1"), # 70B - Ưu tiên cao nhất
    os.getenv("GROQ_MODEL_ID_2"), # 120B
    os.getenv("GROQ_MODEL_ID_3"), # Qwen 32B
    os.getenv("GROQ_MODEL_ID_4"), # Llama 4 17B
    os.getenv("GROQ_MODEL_ID_5")  # 20B
]

# Danh sách model nhanh & quota lớn (Dùng cho bước check YES/NO)
CHECKING_MODELS = [
    os.getenv("GROQ_MODEL_ID_7"), # 8B Instant (500K tokens/day)
    os.getenv("GROQ_MODEL_ID_6")  # Compound
]

ENTITY_TYPES = "BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH"

# --- HÀM LÕI ---

def call_groq_with_failover(prompt, model_list):
    """Quét qua danh sách model khi gặp lỗi 429"""
    for model_id in model_list:
        if not model_id: continue
        
        try:
            logging.info(f"  --> Thử gọi model: {model_id}")
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_id,
                temperature=0.1,
                timeout=30.0 # Thêm timeout để tránh treo máy
            )
            return chat_completion.choices[0].message.content, model_id
            
        except Exception as e:
            err_msg = str(e).lower()
            # Catch lỗi 429 (Rate Limit) hoặc 503 (Overloaded)
            if "429" in err_msg or "rate_limit" in err_msg or "503" in err_msg:
                logging.warning(f"⚠️ {model_id} đang bận hoặc hết hạn mức. Chuyển sang model tiếp theo...")
                # Nghỉ ngắn 2s trước khi đổi sang model dự phòng
                time.sleep(2)
                continue 
            else:
                logging.error(f"❌ Lỗi nghiêm trọng: {err_msg}")
                continue
                
    # Nếu tất cả model đều lỗi, cho script nghỉ dài rồi thử lại từ đầu list
    logging.critical("🚨 Cạn kiệt mọi tài nguyên dự phòng. Nghỉ 60s...")
    # time.sleep(60)
    sys.exit(1)
    return None, None

def clean_extraction_output(raw_text):
    # Loại bỏ toàn bộ nội dung trong thẻ <think>
    cleaned_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    return cleaned_text.strip()

def run_extraction_with_reflection(chunk_text):
    final_results = []
    models_used_history = []
    
    # BƯỚC 1: Trích xuất thô
    full_prompt = GRAPH_EXTRACTION_PROMPT.format(
        entity_types=ENTITY_TYPES,
        input_text=chunk_text,
        tuple_delimiter="<|>",
        record_delimiter="####",
        completion_delimiter="[DONE]"
    )
    
    initial_output, used_model = call_groq_with_failover(full_prompt, EXTRACTION_MODELS)
    if not initial_output: return None, [] # Trả về None để loop ngoài cùng biết mà gọi lại
    
    final_results.append(initial_output)
    models_used_history.append(f"Extract: {used_model}")
    
    # BƯỚC 2: Kiểm tra sót thực thể (Gleaning)
    check_prompt = f"{initial_output}\n\n{LOOP_PROMPT}"
    check_val, check_model = call_groq_with_failover(check_prompt, CHECKING_MODELS)
    
    if check_val and "YES" in check_val.upper():
        logging.info("  --> Model xác nhận có sót thực thể. Đang chạy Gleaning...")
        glean_prompt = f"{initial_output}\n\n{CONTINUE_PROMPT}"
        glean_output, glean_model = call_groq_with_failover(glean_prompt, EXTRACTION_MODELS)
        
        if glean_output:
            final_results.append(glean_output)
            models_used_history.append(f"Glean: {glean_model}")

    return "\n####\n".join(final_results), models_used_history

def get_processed_chunk_ids(output_dir):
    """Quét thư mục đầu ra để lấy danh sách các file đã trích xuất thành công."""
    processed_ids = set()
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith(".json"):
                # Cấu trúc file: entity_graph_DOC_016_chunk_0000.json
                chunk_id = filename.replace("entity_graph_", "").replace(".json", "")
                processed_ids.add(chunk_id)
    return processed_ids

# --- CHƯƠNG TRÌNH CHÍNH ---

def main():
    logging.info("=== KHỞI ĐỘNG HỆ THỐNG TRÍCH XUẤT HÀNG LOẠT ===")
    
    # 1. Đọc dữ liệu đầu vào
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)
        
    # 2. Xử lý Save Progress
    processed_ids = get_processed_chunk_ids(OUTPUT_DIR)
    # pending_chunks = [c for c in all_chunks if c['chunk_id'] not in processed_ids]
    # pending_chunks = [c for i, c in enumerate(all_chunks) if c['chunk_id'] not in processed_ids and i % 2 != 0]#LẺ
    pending_chunks = [c for c in all_chunks if c['chunk_id'] not in processed_ids]
    
    logging.info(f"Tổng số chunk trong file: {len(all_chunks)}")
    logging.info(f"Đã xử lý trước đó: {len(processed_ids)}")
    logging.info(f"Cần xử lý đợt này: {len(pending_chunks)}")
    
    if len(pending_chunks) == 0:
        logging.info("Tuyệt vời! Tất cả các chunk đã được trích xuất hoàn tất.")
        return

    # 3. Vòng lặp trích xuất
    for i, chunk in enumerate(pending_chunks):
        chunk_id = chunk['chunk_id']
        token_size = chunk['metadata']['token_count']
        
        logging.info(f"[{i+1}/{len(pending_chunks)}] Đang xử lý: {chunk_id} | Tokens: {token_size}")
        
        start_time = time.time()
        
        # Vòng lặp While đảm bảo chunk được xử lý thành công kể cả khi phải ngủ chờ Quota
        result = None
        models_info = []
        while result is None:
            result, models_info = run_extraction_with_reflection(chunk['content'])
        
        # 4. Lưu kết quả dạng Chuẩn
        output_data = {
            "chunk_id": chunk_id,
            "metadata": chunk['metadata'],
            "extraction_raw": result,
            "models_used": models_info,
            "extraction_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        output_file = os.path.join(OUTPUT_DIR, f"entity_graph_{chunk_id}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        logging.info(f"  --> Xong trong {time.time()-start_time:.2f}s. Model sử dụng: {models_info}")
        
        # Ngủ nhẹ 2 giây để tránh đánh sập API Groq bằng request liên tục
        time.sleep(2)

if __name__ == "__main__":
    main()