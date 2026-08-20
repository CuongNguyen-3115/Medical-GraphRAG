import os
import json
import re
import logging
import time
from groq import Groq
from dotenv import load_dotenv

# --- CẤU HÌNH ---
INPUT_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_final.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities"
ENV_PATH = r"C:\1. Project\ĐATN\.env"
TARGET_CHUNK_ID = "DOC_016_chunk_0033"

load_dotenv(ENV_PATH)
# Khởi tạo client với max_retries=0 để tự xử lý logic đổi model khi gặp lỗi 429
client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)

# Import prompts từ file prompt.py
from prompts import GRAPH_EXTRACTION_PROMPT, CONTINUE_PROMPT, LOOP_PROMPT

def clean_think_tags(text):
    """Xóa bỏ phần suy nghĩ trong thẻ <think> của các model như Qwen hoặc DeepSeek"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def call_groq_safe(prompt, model_id):
    """Hàm gọi API có xử lý lỗi 429"""
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia trích xuất tri thức y khoa. Trả về kết quả trực tiếp, không bao gồm phần suy nghĩ (reasoning)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4096
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Lỗi API ({model_id}): {e}")
        return None

def run_extraction_with_gleaning(chunk_content):
    """Quy trình 2 bước: Trích xuất thô + Kiểm tra sót (LOOP/CONTINUE)"""
    
    # BƯỚC 1: Trích xuất ban đầu
    primary_model = os.getenv("GROQ_MODEL_ID_4") # 70B
    full_prompt = GRAPH_EXTRACTION_PROMPT.format(
        entity_types="BỆNH_LÝ, TRIỆU_CHỨNG, HOẠT_CHẤT_THUỐC, PHƯƠNG_PHÁP_ĐIỀU_TRỊ, CƠ_QUAN_CƠ_THỂ, XÉT_NGHIỆM, TÁC_NHÂN_GÂY_BỆNH",
        input_text=chunk_content,
        tuple_delimiter="<|>",
        record_delimiter="####",
        completion_delimiter="[DONE]"
    )
    
    raw_output = call_groq_safe(full_prompt, primary_model)
    if not raw_output: return None
    
    initial_clean = clean_think_tags(raw_output)
    final_results = [initial_clean]
    
    # BƯỚC 2: Kiểm tra xem còn sót không (Sử dụng LOOP_PROMPT)
    # Dùng model nhỏ (8B) để check YES/NO cho tiết kiệm quota
    check_model = os.getenv("GROQ_MODEL_ID_7") 
    check_prompt = f"Dưới đây là kết quả đã trích xuất:\n{initial_clean}\n\n{LOOP_PROMPT}"
    
    check_response = call_groq_safe(check_prompt, check_model)
    
    if check_response and "YES" in check_response.upper():
        print(f"  --> Model xác nhận còn sót thông tin. Đang chạy CONTINUE_PROMPT...")
        
        # BƯỚC 3: Trích xuất bổ sung (Sử dụng CONTINUE_PROMPT)
        continue_prompt = f"Văn bản gốc: {chunk_content}\n\nKết quả đã có: {initial_clean}\n\n{CONTINUE_PROMPT}"
        additional_output = call_groq_safe(continue_prompt, primary_model)
        
        if additional_output:
            final_results.append(clean_think_tags(additional_output))

    return "\n####\n".join(final_results)

def main():
    # Load dữ liệu
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    chunk = next((c for c in chunks if c["chunk_id"] == TARGET_CHUNK_ID), None)
    if not chunk:
        print("Không tìm thấy chunk!")
        return

    result = run_extraction_with_gleaning(chunk['content'])
    
    if result:
        output_file = os.path.join(OUTPUT_DIR, f"debug_gleaning_{TARGET_CHUNK_ID}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "chunk_id": TARGET_CHUNK_ID,
                "extraction_raw": result,
                "metadata": chunk['metadata']
            }, f, ensure_ascii=False, indent=4)
        print(f"Hoàn thành! Kết quả lưu tại: {output_file}")

if __name__ == "__main__":
    main()