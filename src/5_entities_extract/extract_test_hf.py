import os
import json
import time
import re
import logging
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# --- CẤU HÌNH ---
ENV_PATH = r"C:\1. Project\ĐATN\.env"
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\src\6_entities_extract"
TARGET_CHUNK_ID = "DOC_016_chunk_0655"

load_dotenv(ENV_PATH)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Lấy Token và khởi tạo Client
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("❌ Không tìm thấy HF_TOKEN trong file .env!")

client = InferenceClient(token=HF_TOKEN)

# Import Prompt
try:
    from prompts import GRAPH_EXTRACTION_PROMPT
except ImportError:
    logging.error("❌ Không tìm thấy file prompts.py!")
    exit()

def clean_output(text):
    """Lọc bỏ tag <think> và markdown thừa"""
    if not text: return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'```[a-zA-Z]*\n?', '', text)
    return text.replace('```', '').strip()

def main():
    # 1. Load dữ liệu và tìm Chunk
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)
    
    target_chunk = next((c for c in all_chunks if c['chunk_id'] == TARGET_CHUNK_ID), None)
    if not target_chunk:
        logging.error(f"❌ Không tìm thấy chunk {TARGET_CHUNK_ID}!")
        return

    content = target_chunk['content']
    logging.info(f"🚀 Bắt đầu test 5 model Hugging Face với chunk: {TARGET_CHUNK_ID}")

    # 2. Duyệt qua 5 model HF
    for i in range(1, 6):
        model_env_name = f"HF_MODEL_ID_{i}"
        model_id = os.getenv(model_env_name)
        
        if not model_id:
            logging.warning(f"⚠️ {model_env_name} trống, bỏ qua.")
            continue

        logging.info(f"--- 🔄 Đang test HF Model {i}/5: {model_id} ---")
        
        full_prompt = GRAPH_EXTRACTION_PROMPT.format(
            entity_types="BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH",
            input_text=content,
            tuple_delimiter="<|>",
            record_delimiter="####",
            completion_delimiter="[DONE]"
        )

        try:
            start_time = time.time()
            
            # Sử dụng API chat_completion (OpenAI-compatible)
            response = client.chat_completion(
                model=model_id,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia trích xuất tri thức y khoa. Trả về kết quả trực tiếp."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            raw_result = response.choices[0].message.content
            cleaned_result = clean_output(raw_result)
            duration = time.time() - start_time

            # 3. Lưu kết quả
            safe_name = model_id.split('/')[-1].replace('-', '_').replace('.', '_')
            output_file = os.path.join(OUTPUT_DIR, f"test_HF_{i}_{safe_name}_{TARGET_CHUNK_ID}.json")
            
            output_data = {
                "model_index": i,
                "model_id": model_id,
                "chunk_id": TARGET_CHUNK_ID,
                "execution_time_sec": round(duration, 2),
                "extraction_raw": cleaned_result
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            
            logging.info(f" ✅ Thành công! Lưu tại: {os.path.basename(output_file)} ({duration:.2f}s)")

        except Exception as e:
            err_msg = str(e)
            if "503" in err_msg:
                logging.error(f" ❌ Model {model_id} đang khởi động (Loading). Hãy thử lại sau 1-2 phút.")
            elif "429" in err_msg:
                logging.error(f" ❌ Hết Quota (Rate Limit) cho model {model_id} trên HF.")
            else:
                logging.error(f" ❌ Lỗi khi test {model_id}: {err_msg}")
        
        # Nghỉ 15s giữa các model để ổn định Quota
        time.sleep(15)

if __name__ == "__main__":
    main()