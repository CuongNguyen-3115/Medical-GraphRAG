import os
import json
import re
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CẤU HÌNH ---
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities"
ENV_PATH = r"C:\1. Project\ĐATN\.env"
TARGET_CHUNK_ID = "DOC_016_chunk_0033"

# Load biến môi trường
load_dotenv(ENV_PATH)
API_KEY = os.getenv("GEMINI_API_KEY")

# Khởi tạo Client GenAI mới
client = genai.Client(api_key=API_KEY)

# Danh sách 5 model để test
MODEL_IDS = [
    os.getenv("MODEL_ID_1"), # gemini-3.1-flash-lite-preview
    os.getenv("MODEL_ID_2"), # gemini-2.5-flash
    os.getenv("MODEL_ID_3"), # gemini-3-flash-preview
    os.getenv("MODEL_ID_4"), # gemini-2.5-flash-lite
    os.getenv("MODEL_ID_5")  # gemini-flash-latest
]

# Import prompts (Giữ nguyên logic prompt của bạn)
try:
    from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT
except ImportError:
    print("Lỗi: Không tìm thấy file prompts.py!")

def clean_think_tags(text):
    """Xóa bỏ phần reasoning nếu model tự ý trả về (đặc biệt là các dòng Flash 3.x)"""
    if not text: return ""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def call_gemini_sdk_safe(prompt, model_id):
    """Hàm gọi API sử dụng SDK google-genai mới"""
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Bạn là chuyên gia trích xuất tri thức y khoa. Trả về kết quả trực tiếp, không bao gồm phần suy nghĩ (reasoning).",
                temperature=0.1,
                max_output_tokens=4096,
            )
        )
        return response.text
    except Exception as e:
        print(f"   [!] Lỗi khi gọi model {model_id}: {e}")
        return None

def process_with_model(model_id, chunk_content):
    """Quy trình trích xuất + Gleaning cho một model cụ thể"""
    print(f"--- Đang test Model: {model_id} ---")
    
    # Bước 1: Trích xuất chính
    full_prompt = GRAPH_EXTRACTION_PROMPT.format(
        entity_types="BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH",
        input_text=chunk_content,
        tuple_delimiter="<|>",
        record_delimiter="####",
        completion_delimiter="[DONE]"
    )
    
    raw_output = call_gemini_sdk_safe(full_prompt, model_id)
    if not raw_output: return None
    
    initial_clean = clean_think_tags(raw_output)
    results = [initial_clean]
    
    # Bước 2: Kiểm tra sót (Gleaning)
    check_prompt = f"Dưới đây là kết quả đã trích xuất:\n{initial_clean}\n\n{LOOP_PROMPT}"
    check_res = call_gemini_sdk_safe(check_prompt, model_id)
    
    if check_res and "YES" in check_res.upper():
        print(f"   --> {model_id} phát hiện thông tin còn sót. Đang bổ sung...")
        cont_prompt = f"Văn bản gốc: {chunk_content}\n\nKết quả hiện tại: {initial_clean}\n\n{CONTINUE_PROMPT}"
        extra_output = call_gemini_sdk_safe(cont_prompt, model_id)
        if extra_output:
            results.append(clean_think_tags(extra_output))
            
    return "\n####\n".join(results)

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    chunk = next((c for c in chunks if c["chunk_id"] == TARGET_CHUNK_ID), None)
    if not chunk:
        print("Không tìm thấy chunk tiêu điểm!")
        return

    for m_id in MODEL_IDS:
        if not m_id: continue
        
        final_text = process_with_model(m_id, chunk['content'])
        
        if final_text:
            # Lưu file với tên model để dễ so sánh
            safe_model_name = m_id.replace("/", "_").replace("-", "_")
            out_path = os.path.join(OUTPUT_DIR, f"test_{safe_model_name}_{TARGET_CHUNK_ID}.json")
            
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "model": m_id,
                    "chunk_id": TARGET_CHUNK_ID,
                    "content": final_text,
                    "metadata": chunk.get('metadata', {})
                }, f, ensure_ascii=False, indent=4)
            print(f"   [OK] Đã lưu kết quả tại: {out_path}\n")
        
        # Nghỉ ngắn giữa các model để tránh rate limit nếu dùng bản Free
        time.sleep(2)

if __name__ == "__main__":
    main()