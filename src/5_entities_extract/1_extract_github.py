import os
import json
import logging
import sys
import time
import re
from datetime import datetime
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from dotenv import load_dotenv

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

# --- LOAD API KEY & CLIENT ---
load_dotenv(ENV_PATH)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError(f"❌ KHÔNG TÌM THẤY GITHUB_TOKEN trong file .env tại: {ENV_PATH}")

# Danh sách 10 model dự phòng (Load tự động từ GITHUB_MODEL_ID_1 đến GITHUB_MODEL_ID_10)
GITHUB_FAILOVER_MODELS = [os.getenv(f"GITHUB_MODEL_ID_{i}") for i in range(1, 11) if os.getenv(f"GITHUB_MODEL_ID_{i}")]

# --- THIẾT LẬP LOGGING (Tên riêng biệt cho Github) ---
log_file = os.path.join(LOG_DIR, f"mass_extract_GITHUB_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

ENDPOINT = "https://models.inference.ai.azure.com"
client_gh = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(str(GITHUB_TOKEN)),
)

ENTITY_TYPES = "BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH"

# --- HÀM LÕI ---

def clean_extraction_output(raw_text):
    if not raw_text: return ""
    cleaned_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    # Loại bỏ code block ```json nếu model tự ý bọc lại
    cleaned_text = re.sub(r'```[a-zA-Z]*\n?', '', cleaned_text)
    cleaned_text = cleaned_text.replace('```', '')
    return cleaned_text.strip()

def call_github_api(prompt, model_id):
    try:
        response = client_gh.complete(
            messages=[
                SystemMessage(content="Bạn là chuyên gia trích xuất tri thức y khoa. Trả về kết quả trực tiếp, không bao gồm phần suy nghĩ (reasoning)."),
                UserMessage(content=prompt),
            ],
            model=model_id,
            temperature=0.1,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except HttpResponseError as e:
        if e.status_code in [429, 503]:
            logging.warning(f"  [!] Model {model_id} quá tải/hết quota (Lỗi {e.status_code}).")
        elif e.status_code == 400:
            logging.warning(f"  [!] Model {model_id} từ chối request (Lỗi 400 - Có thể do Content Filter).")
        else:
            logging.error(f"  [!] Lỗi API với {model_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"  [!] Lỗi không xác định với {model_id}: {e}")
        return None
    
def call_with_10_models_failover(prompt):
    for model_id in GITHUB_FAILOVER_MODELS:
        if not model_id: continue
        result = call_github_api(prompt, model_id)
        if result:
            return result, model_id
        
        # Nghỉ nhẹ 2s trước khi thử model dự phòng tiếp theo
        time.sleep(2) 
        
    logging.critical("🚨 Cạn kiệt 10 model GitHub! Nghỉ 60s để chờ Quota hồi phục...")
    # time.sleep(60)
    sys.exit(1)
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
    
    initial_output, used_model = call_with_10_models_failover(full_prompt)
    if not initial_output: return None, []
    
    initial_clean = clean_extraction_output(initial_output)
    final_results.append(initial_clean)
    models_used_history.append(f"Extract: {used_model}")
    
    # Giãn cách request tránh dính Spam Filter của API
    time.sleep(3)
    
    # BƯỚC 2: Kiểm tra sót (Gleaning)
    check_prompt = f"Dưới đây là kết quả đã trích xuất:\n{initial_clean}\n\n{LOOP_PROMPT}"
    check_val, check_model = call_with_10_models_failover(check_prompt)
    
    if check_val and "YES" in check_val.upper():
        logging.info("    --> Model xác nhận sót thực thể. Đang chạy bổ sung...")
        time.sleep(2) # Giãn cách trước khi gọi tiếp
        glean_prompt = f"Văn bản gốc: {chunk_text}\n\nKết quả hiện tại: {initial_clean}\n\n{CONTINUE_PROMPT}"
        glean_output, glean_model = call_with_10_models_failover(glean_prompt)
        
        if glean_output:
            final_results.append(clean_extraction_output(glean_output))
            models_used_history.append(f"Glean: {glean_model}")

    return "\n####\n".join(final_results), models_used_history

def get_processed_chunk_ids(output_dir):
    processed_ids = set()
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith(".json"):
                chunk_id = filename.replace("entity_graph_", "").replace(".json", "")
                processed_ids.add(chunk_id)
    return processed_ids

# --- CHƯƠNG TRÌNH CHÍNH ---

def main():
    logging.info("=== KHỞI ĐỘNG HỆ THỐNG TRÍCH XUẤT GITHUB MODELS (LUỒNG LẺ) ===")
    
    try:
        with open(INPUT_PATH, 'r', encoding='utf-8') as f:
            all_chunks = json.load(f)
    except Exception as e:
        logging.error(f"Lỗi đọc file input: {e}")
        return
        
    processed_ids = get_processed_chunk_ids(OUTPUT_DIR)
    
    # Lọc chunk: Chỉ lấy các chunk CHƯA xử lý VÀ có chỉ số chẵn (i % 2 == 0)
    # pending_chunks = [c for i, c in enumerate(all_chunks) if c['chunk_id'] not in processed_ids and i % 2 == 0]#CHẴN
    pending_chunks = [c for c in all_chunks if c['chunk_id'] not in processed_ids]

    logging.info(f"Tổng: {len(all_chunks)} | Đã xong: {len(processed_ids)} | GitHub (Luồng chẵn) nhận: {len(pending_chunks)}")
    
    if not pending_chunks:
        logging.info("Tất cả các chunk trong luồng này đã hoàn tất.")
        return

    for i, chunk in enumerate(pending_chunks):
        chunk_id = chunk['chunk_id']
        logging.info(f"[{i+1}/{len(pending_chunks)}] Xử lý: {chunk_id}")
        
        # Double-check: Kiểm tra xem luồng Gemini đã nhanh tay xử lý chunk này chưa
        output_file = os.path.join(OUTPUT_DIR, f"entity_graph_{chunk_id}.json")
        if os.path.exists(output_file):
            logging.info(f"  --> Chunk {chunk_id} đã được luồng khác xử lý. Bỏ qua.")
            continue

        start_time = time.time()
        result = None
        models_info = []
        
        # Vòng lặp kiên trì xử lý chunk
        while result is None:
            result, models_info = run_extraction_with_reflection(chunk['content'])
            if result is None:
                logging.warning("  --> Thử lại toàn bộ quy trình cho chunk này sau 30s...")
                time.sleep(30)
        
        output_data = {
            "chunk_id": chunk_id,
            "metadata": chunk.get('metadata', {}),
            "extraction_raw": result,
            "models_used": models_info,
            "extraction_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        logging.info(f"  --> OK ({time.time()-start_time:.1f}s). Models: {models_info}")
        
        # TĂNG LÊN 20s: Duy trì hạn mức Rate Limit cho chu kỳ 4 model
        time.sleep(20)

if __name__ == "__main__":
    main()