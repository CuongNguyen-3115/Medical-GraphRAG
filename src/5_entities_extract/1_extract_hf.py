import os
import sys
import json
import logging
import time
import re
from datetime import datetime
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# --- CẤU HÌNH ĐƯỜNG DẪN TỔNG ---
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities"
LOG_DIR = r"C:\1. Project\ĐATN\logs\6_entities_extract"
ENV_PATH = r"C:\1. Project\ĐATN\.env"

# Load biến môi trường TỪ FILE .ENV (CRITICAL FIX)
load_dotenv(ENV_PATH)

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_file = os.path.join(LOG_DIR, f"mass_extraction_hf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

# Import prompt (Đảm bảo file prompts.py nằm cùng thư mục)
try:
    from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT
except ImportError:
    logging.warning("Cảnh báo: Không tìm thấy file prompts.py. Vui lòng kiểm tra lại đường dẫn.")

# --- CẤU HÌNH HF ---
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    logging.error("Không tìm thấy HF_TOKEN trong file .env!")
    sys.exit(1)

HF_MODELS = [os.getenv(f"HF_MODEL_ID_{i}") for i in range(1, 6) if os.getenv(f"HF_MODEL_ID_{i}")]
if not HF_MODELS:
    logging.error("Không tìm thấy HF_MODEL_ID nào trong file .env!")
    sys.exit(1)

client_hf = InferenceClient(token=HF_TOKEN)

ENTITY_TYPES = "BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH"

# --- HÀM LÕI ---

def clean_extraction_output(raw_text):
    """Loại bỏ toàn bộ nội dung trong thẻ <think> nếu model có sử dụng reasoning"""
    if not raw_text: return ""
    cleaned_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    return cleaned_text.strip()

def call_hf_with_failover(prompt, model_list):
    """Quét qua danh sách model Hugging Face khi gặp lỗi 429 hoặc 503"""
    for model_id in model_list:
        if not model_id: continue
        
        try:
            logging.info(f"  --> Thử gọi model HF: {model_id}")
            response = client_hf.chat_completion(
                model=model_id,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia trích xuất tri thức y khoa. Trả về kết quả trực tiếp, không bao gồm phần suy nghĩ (reasoning)."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
                temperature=0.1,
            )
            return response.choices[0].message.content, model_id
            
        except Exception as e:
            err_msg = str(e).lower()
            
            # Catch lỗi HF: 503 (Loading), 429 (Rate Limit)
            if "503" in err_msg or "loading" in err_msg or "overloaded" in err_msg:
                logging.warning(f"⚠️ Model {model_id} đang khởi động hoặc Server bận. Chuyển model...")
                time.sleep(2)
                continue
            elif "429" in err_msg or "rate limit" in err_msg:
                logging.warning(f"⚠️ Hết Quota (Rate Limit) HF cho model {model_id}. Chuyển model...")
                time.sleep(2)
                continue
            elif "400" in err_msg or "not supported" in err_msg:
                logging.error(f"❌ Model {model_id} không hỗ trợ dạng Chat API. Bỏ qua...")
                continue
            else:
                logging.error(f"❌ Lỗi nghiêm trọng với {model_id}: {err_msg}")
                continue
                
    # Nếu quét hết danh sách model mà vẫn không có kết quả
    logging.critical("🚨 Cạn kiệt mọi tài nguyên dự phòng trên Hugging Face! Báo lỗi để chuyển quyền (Master Script)...")
    sys.exit(1)

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
    
    initial_output, used_model = call_hf_with_failover(full_prompt, HF_MODELS)
    if not initial_output: return None, [] # Lỗi toàn tập -> return None để retry
    
    initial_clean = clean_extraction_output(initial_output)
    final_results.append(initial_clean)
    models_used_history.append(f"Extract: {used_model}")
    
    # BƯỚC 2: Kiểm tra sót thực thể (Gleaning)
    check_prompt = f"Dưới đây là kết quả đã trích xuất:\n{initial_clean}\n\n{LOOP_PROMPT}"
    check_val, check_model = call_hf_with_failover(check_prompt, HF_MODELS)

    if check_val and "YES" in check_val.upper():
        logging.info("  --> Hệ thống xác nhận có sót thực thể. Đang chạy Gleaning...")
        glean_prompt = f"Văn bản gốc: {chunk_text}\n\nKết quả hiện tại: {initial_clean}\n\n{CONTINUE_PROMPT}"
        glean_output, glean_model = call_hf_with_failover(glean_prompt, HF_MODELS)
        
        if glean_output:
            glean_clean = clean_extraction_output(glean_output)
            final_results.append(glean_clean)
            models_used_history.append(f"Glean: {glean_model}")

    return "\n####\n".join(final_results), models_used_history

def get_processed_chunk_ids(output_dir):
    """Quét thư mục đầu ra để lấy danh sách các file đã trích xuất thành công."""
    processed_ids = set()
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith(".json"):
                chunk_id = filename.replace("entity_graph_", "").replace(".json", "")
                processed_ids.add(chunk_id)
    return processed_ids

# --- CHƯƠNG TRÌNH CHÍNH ---

def main():
    logging.info("=== KHỞI ĐỘNG HỆ THỐNG TRÍCH XUẤT HÀNG LOẠT BẰNG HUGGING FACE ===")
    
    # 1. Đọc dữ liệu đầu vào
    try:
        with open(INPUT_PATH, 'r', encoding='utf-8') as f:
            all_chunks = json.load(f)
    except FileNotFoundError:
        logging.error(f"Không tìm thấy file tại {INPUT_PATH}")
        sys.exit(1)
        
    # 2. Xử lý Save Progress
    processed_ids = get_processed_chunk_ids(OUTPUT_DIR)
    pending_chunks = [c for c in all_chunks if c['chunk_id'] not in processed_ids]
    
    logging.info(f"Tổng số chunk trong file: {len(all_chunks)}")
    logging.info(f"Đã xử lý thành công: {len(processed_ids)}")
    logging.info(f"Cần xử lý đợt này: {len(pending_chunks)}")
    
    if not pending_chunks:
        logging.info("🎉 Tuyệt vời! Tất cả các chunk đã được trích xuất hoàn tất.")
        sys.exit(0) 

    # 3. Vòng lặp trích xuất
    for i, chunk in enumerate(pending_chunks):
        chunk_id = chunk['chunk_id']
        token_size = chunk.get('metadata', {}).get('token_count', 'N/A')
        
        logging.info(f"[{i+1}/{len(pending_chunks)}] Đang xử lý: {chunk_id} | Tokens: {token_size}")
        start_time = time.time()
        
        result = None
        models_info = []
        
        # Vòng lặp này sẽ bị ngắt bởi sys.exit(1) bên trong hàm call_hf_with_failover nếu hết sạch Quota
        while result is None:
            result, models_info = run_extraction_with_reflection(chunk['content'])
        
        # 4. Lưu kết quả
        output_data = {
            "chunk_id": chunk_id,
            "metadata": chunk.get('metadata', {}),
            "extraction_raw": result,
            "models_used": models_info,
            "extraction_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        output_file = os.path.join(OUTPUT_DIR, f"entity_graph_{chunk_id}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        logging.info(f"  --> Xong trong {time.time()-start_time:.2f}s. Lịch sử model: {models_info}")
        
        # Nghỉ nhẹ giữa các lượt (HF nên để khoảng 5-10s để ổn định)
        time.sleep(10)

    logging.info("✅ Đã hoàn thành toàn bộ danh sách chunk được giao trong lượt này.")
    sys.exit(0)

if __name__ == "__main__":
    main()