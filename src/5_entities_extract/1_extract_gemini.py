import os
import json
import logging
import time
import re
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys

# Import prompt (Đảm bảo file prompts.py nằm cùng thư mục)
try:
    from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT
except ImportError:
    print("Cảnh báo: Không tìm thấy file prompts.py. Vui lòng kiểm tra lại đường dẫn.")

# --- CẤU HÌNH ĐƯỜNG DẪN TỔNG ---
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities"
LOG_DIR = r"C:\1. Project\ĐATN\logs\6_entities_extract"
ENV_PATH = r"C:\1. Project\ĐATN\.env"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_file = os.path.join(LOG_DIR, f"mass_extraction_gemini_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- QUẢN LÝ TÀI NGUYÊN MODEL TỪ .ENV ---
# Danh sách 3 model hỗ trợ backup chéo cho nhau
GEMINI_FAILOVER_MODELS = [
    os.getenv("MODEL_ID_3"), # gemini-3-flash-preview (Ưu tiên 1)
    os.getenv("MODEL_ID_4"), # gemini-2.5-flash-lite (Ưu tiên 2)
    os.getenv("MODEL_ID_5"),  # gemini-flash-latest (Ưu tiên 3)
    os.getenv("MODEL_ID_1"), # gemini-flash-latest (Ưu tiên 3)
    os.getenv("MODEL_ID_2")  # gemini-flash-latest (Ưu tiên 3)
]

ENTITY_TYPES = "BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH"

# --- HÀM LÕI ---

def clean_extraction_output(raw_text):
    """Loại bỏ toàn bộ nội dung trong thẻ <think> nếu model có sử dụng reasoning"""
    if not raw_text: return ""
    cleaned_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    return cleaned_text.strip()

def call_gemini_with_failover(prompt, model_list):
    """Quét qua danh sách model khi gặp lỗi API (đặc biệt là 429)"""
    for model_id in model_list:
        if not model_id: continue
        
        try:
            logging.info(f"  --> Thử gọi model: {model_id}")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="Bạn là chuyên gia trích xuất tri thức y khoa. Trả về kết quả trực tiếp, tuân thủ đúng định dạng, không bao gồm phần suy nghĩ (reasoning).",
                    temperature=0.1,
                    max_output_tokens=4096,
                )
            )
            return response.text, model_id
            
        except Exception as e:
            err_msg = str(e).lower()
            # Catch lỗi 429 (Rate Limit/Quota) hoặc 503 (Overloaded) của Google
            if "429" in err_msg or "rate" in err_msg or "quota" in err_msg or "503" in err_msg or "overloaded" in err_msg:
                logging.warning(f"⚠️ {model_id} đang bận hoặc hết hạn mức. Chuyển sang model dự phòng tiếp theo...")
                time.sleep(3) # Nghỉ 3s trước khi đổi sang model dự phòng để an toàn
                continue 
            else:
                logging.error(f"❌ Lỗi xử lý với {model_id}: {err_msg}")
                # Nếu là lỗi do Content Filter (Safety block) thì tiếp tục sang model khác xem có vượt được không
                continue
                
    # Nếu tất cả model đều lỗi, cho script nghỉ dài rồi trả về None để vòng lặp While bên ngoài gọi lại
    logging.critical("🚨 Cạn kiệt mọi tài nguyên dự phòng. Nghỉ 60s trước khi thử lại từ đầu...")
    sys.exit(1)
    # time.sleep(60)
    return None, None

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
    
    initial_output, used_model = call_gemini_with_failover(full_prompt, GEMINI_FAILOVER_MODELS)
    if not initial_output: return None, [] # Lỗi toàn tập -> return None để retry
    
    initial_clean = clean_extraction_output(initial_output)
    final_results.append(initial_clean)
    models_used_history.append(f"Extract: {used_model}")
    
    # BƯỚC 2: Kiểm tra sót thực thể (Gleaning)
    check_prompt = f"Dưới đây là kết quả đã trích xuất:\n{initial_clean}\n\n{LOOP_PROMPT}"
    check_val, check_model = call_gemini_with_failover(check_prompt, GEMINI_FAILOVER_MODELS)
    
    if check_val and "YES" in check_val.upper():
        logging.info("  --> Hệ thống xác nhận có sót thực thể. Đang chạy Gleaning...")
        glean_prompt = f"Văn bản gốc: {chunk_text}\n\nKết quả hiện tại: {initial_clean}\n\n{CONTINUE_PROMPT}"
        glean_output, glean_model = call_gemini_with_failover(glean_prompt, GEMINI_FAILOVER_MODELS)
        
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
                # Cấu trúc file: entity_graph_DOC_016_chunk_0000.json
                chunk_id = filename.replace("entity_graph_", "").replace(".json", "")
                processed_ids.add(chunk_id)
    return processed_ids

# --- CHƯƠNG TRÌNH CHÍNH ---

def main():
    logging.info("=== KHỞI ĐỘNG HỆ THỐNG TRÍCH XUẤT HÀNG LOẠT BẰNG GEMINI ===")
    
    # 1. Đọc dữ liệu đầu vào
    try:
        with open(INPUT_PATH, 'r', encoding='utf-8') as f:
            all_chunks = json.load(f)
    except FileNotFoundError:
        logging.error(f"Không tìm thấy file tại {INPUT_PATH}")
        return
        
    # 2. Xử lý Save Progress (Bỏ qua các chunk đã xử lý)
    processed_ids = get_processed_chunk_ids(OUTPUT_DIR)
    # pending_chunks = [c for i, c in enumerate(all_chunks) if c['chunk_id'] not in processed_ids and i % 2 == 0] #LẺ
    pending_chunks = [c for c in all_chunks if c['chunk_id'] not in processed_ids]
    
    logging.info(f"Tổng số chunk trong file: {len(all_chunks)}")
    logging.info(f"Đã xử lý thành công: {len(processed_ids)}")
    logging.info(f"Cần xử lý đợt này: {len(pending_chunks)}")
    
    if len(pending_chunks) == 0:
        logging.info("Tuyệt vời! Tất cả các chunk đã được trích xuất hoàn tất.")
        return

    # 3. Vòng lặp trích xuất
    for i, chunk in enumerate(pending_chunks):
        chunk_id = chunk['chunk_id']
        # Dùng .get() để tránh lỗi nếu metadata không có token_count
        token_size = chunk.get('metadata', {}).get('token_count', 'N/A')
        
        logging.info(f"[{i+1}/{len(pending_chunks)}] Đang xử lý: {chunk_id} | Tokens: {token_size}")
        
        start_time = time.time()
        
        # Vòng lặp While đảm bảo chunk được xử lý thành công kể cả khi API sập hoàn toàn
        result = None
        models_info = []
        while result is None:
            result, models_info = run_extraction_with_reflection(chunk['content'])
        
        # 4. Lưu kết quả dạng JSON
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
        
        # Ngủ nhẹ 3 giây giữa các lượt để đảm bảo token refill kịp, chống Rate Limit
        time.sleep(3)

if __name__ == "__main__":
    main()