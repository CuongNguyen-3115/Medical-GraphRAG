# gọi Giám khảo chấm điểm 102 câu trả lời
# C:\1. Project\ĐATN\src\9_query\module_4_evaluation\2_evaluate_answers.py

import os
import json
import time
import warnings
from dotenv import load_dotenv
from groq import Groq
from transformers import AutoTokenizer
from judge_prompt import RAGAS_EVALUATION_PROMPT

# Tắt cảnh báo không cần thiết từ thư viện transformers để log sạch đẹp
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# 1. Cấu hình đường dẫn hệ thống
INPUT_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\input\20_retry_graphrag_results.jsonl"
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\output\20retry_evaluation_log.jsonl"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# 2. Khởi tạo danh sách API Keys
load_dotenv()
api_keys = [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4")
]
api_keys = [key for key in api_keys if key]
if not api_keys:
    raise ValueError("Không tìm thấy Groq API Key nào trong file .env!")

print(f"=== Đã kích hoạt hệ thống với {len(api_keys)} API Keys độc lập (Load Balancing) ===")

# 3. Khởi tạo bộ Tokenizer chuẩn của Llama-3
print("⏳ Đang tải Llama-3 Tokenizer (Vui lòng bật mạng trong lần chạy đầu tiên)...")
try:
    llama_tokenizer = AutoTokenizer.from_pretrained("NousResearch/Meta-Llama-3-8B")
    print("✅ Đã tải thành công bộ mã hóa Token của Meta Llama-3!")
except Exception as e:
    raise RuntimeError(f"Không thể tải Tokenizer từ Hugging Face. Lỗi: {e}")

# 4. Hàm lọc nhiễu Context (Chỉ trích xuất plain text từ description)
def extract_plain_context(context_data):
    descriptions = []
    for item in context_data:
        for point in item.get("points", []):
            desc = point.get("description", "").strip()
            if desc:
                descriptions.append(desc)
    return "\n".join(f"- {desc}" for desc in descriptions)

# 5. Hàm đếm số lượng Token chính xác bằng Meta Llama-3 Tokenizer
def count_tokens(text):
    try:
        return len(llama_tokenizer.encode(text))
    except Exception as e:
        # Cơ chế dự phòng (Fall-back) an toàn nếu phát sinh lỗi
        print(f"   ⚠️ Lỗi thư viện đếm token: {str(e)}. Dùng công thức dự phòng.")
        return int(len(text.split()) * 1.3)

# 6. Hàm tải dữ liệu đã chấm điểm trước đó (Cơ chế Resume thông minh)
def load_processed_queries(output_path):
    processed = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        processed.add(data["query"])
                    except Exception:
                        continue
    return processed

# 7. Luồng thực thi chính
def main():
    processed_queries = load_processed_queries(OUTPUT_FILE)
    if processed_queries:
        print(f"-> Phát hiện {len(processed_queries)} câu đã chấm điểm trước đó. Tiến hành chạy tiếp...")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    key_index = 0
    
    for idx, row in enumerate(rows, 1):
        query = row.get("query")
        
        if query in processed_queries:
            continue
            
        context_raw = row.get("context", [])
        answer = row.get("answer", "")
        
        # Tiền xử lý dữ liệu đầu vào
        clean_context = extract_plain_context(context_raw)
        formatted_prompt = RAGAS_EVALUATION_PROMPT.format(
            query=query,
            context=clean_context,
            answer=answer
        )
        
        # Đếm token chính xác 100% theo Llama-3
        input_tokens = count_tokens(formatted_prompt)
        print(f"\n[{idx}/61] Đang xử lý: {query[:60]}...")
        print(f"   -> Dung lượng prompt chính xác: {input_tokens} tokens")

        success = False
        retry_count = 0
        max_retries = 3
        judge_output = None
        
        # Vòng lặp gọi API có thiết lập cấu trúc xoay vòng Key
        while not success and retry_count < max_retries:
            # Liên tục luân phiên key cho mỗi lần gửi yêu cầu (kể cả gọi mới hay gọi lại khi lỗi)
            current_key = api_keys[key_index]
            current_key_id = key_index + 1  # Định dạng nhãn Key (1, 2, 3, 4) để theo dõi log
            key_index = (key_index + 1) % len(api_keys)
            
            try:
                print(f"   -> Đang gửi request bằng Tài khoản/Key #{current_key_id}...")
                client = Groq(api_key=current_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    temperature=0.1, 
                    response_format={"type": "json_object"}
                )
                
                judge_output = json.loads(response.choices[0].message.content)
                success = True
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                if "429" in error_msg:
                    print(f"   ⚠️ Key #{current_key_id} dính giới hạn Rate Limit (429). Đang chuyển sang tài khoản khác...")
                else:
                    print(f"   ⚠️ Phát sinh lỗi (Lần thử {retry_count}/{max_retries}): {error_msg}")
                time.sleep(3)  # Nghỉ ngắn trước khi xoay vòng sang key tiếp theo
        
        if not success or judge_output is None:
            print(f"❌ Hệ thống thất bại liên tiếp tại câu {idx}. Tạm dừng tiến trình để bảo toàn dữ liệu.")
            break

        # Đóng gói bản ghi dữ liệu đánh giá
        evaluation_record = {
            "query": query,
            "context_cleaned": clean_context,
            "answer": answer,
            "evaluation": judge_output
        }
        
        # Ghi nối dữ liệu dạng luồng (Stream writing) bảo vệ dữ liệu thời gian thực
        with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
            out_f.write(json.dumps(evaluation_record, ensure_ascii=False) + "\n")
        print("   ✅ Giám khảo đã hoàn thành chấm điểm và cập nhật vào file log.")

        # Lớp giáp bảo vệ Rate Limit động (Đã tối ưu thời gian vì có 4 accounts gánh tải)
        if idx < len(rows):
            if input_tokens < 3000:
                delay = 4  
            elif input_tokens < 6000:
                delay = 8
            else:
                delay = 15
            print(f"   ⏳ Kích hoạt Dynamic Delay: Nghỉ {delay}s...")
            time.sleep(delay)

    print("\n============================================================")
    print("🎉 HOÀN THÀNH QUÁ TRÌNH CHẤM ĐIỂM")
    print(f"Kết quả được lưu trữ an toàn tại: {OUTPUT_FILE}")
    print("============================================================")

if __name__ == "__main__":
    main()