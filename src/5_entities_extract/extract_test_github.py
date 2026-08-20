import os
import json
import time
import re
import logging
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# --- CẤU HÌNH ---
ENV_PATH = r"C:\1. Project\ĐATN\.env"
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\src\6_entities_extract"
TARGET_CHUNK_ID = "DOC_030_chunk_0301"

load_dotenv(ENV_PATH)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cấu hình logging để theo dõi tiến trình
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Lấy Token và khởi tạo Client
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN không tồn tại trong file .env!")

client = ChatCompletionsClient(
    endpoint="https://models.inference.ai.azure.com",
    credential=AzureKeyCredential(GITHUB_TOKEN),
)

# Import Prompt (Đảm bảo file prompts.py ở cùng thư mục hoặc đúng đường dẫn)
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
    # 1. Load dữ liệu và tìm Chunk mục tiêu
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)
    
    target_chunk = next((c for c in all_chunks if c['chunk_id'] == TARGET_CHUNK_ID), None)
    if not target_chunk:
        logging.error(f"❌ Không tìm thấy chunk {TARGET_CHUNK_ID} trong file dữ liệu!")
        return

    content = target_chunk['content']
    logging.info(f"🚀 Bắt đầu test 10 model với chunk: {TARGET_CHUNK_ID}")

    # 2. Duyệt qua 10 model ID trong .env
    for i in range(1, 11):
        model_env_name = f"GITHUB_MODEL_ID_{i}"
        model_id = os.getenv(model_env_name)
        
        if not model_id:
            logging.warning(f"⚠️ {model_env_name} trống, bỏ qua.")
            continue

        logging.info(f"--- 🔄 Đang test Model {i}/10: {model_id} ---")
        
        full_prompt = GRAPH_EXTRACTION_PROMPT.format(
            entity_types="BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH",
            input_text=content,
            tuple_delimiter="<|>",
            record_delimiter="####",
            completion_delimiter="[DONE]"
        )

        try:
            start_time = time.time()
            response = client.complete(
                messages=[
                    SystemMessage(content="Bạn là chuyên gia trích xuất tri thức y khoa."),
                    UserMessage(content=full_prompt),
                ],
                model=model_id,
                temperature=0.1
            )
            
            raw_result = response.choices[0].message.content
            cleaned_result = clean_output(raw_result)
            duration = time.time() - start_time

            # 3. Lưu kết quả
            safe_name = model_id.split('/')[-1].replace('-', '_') # Lấy tên model cuối cho gọn
            output_file = os.path.join(OUTPUT_DIR, f"test_{i}_{safe_name}_{TARGET_CHUNK_ID}.json")
            
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
            logging.error(f" ❌ Lỗi khi test {model_id}: {str(e)}")
        
        # Nghỉ 10s để tránh dính Rate Limit ngay lập tức trong quá trình test
        time.sleep(10)

if __name__ == "__main__":
    main()