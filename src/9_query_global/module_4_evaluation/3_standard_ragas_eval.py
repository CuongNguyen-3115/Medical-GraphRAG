# C:\1. Project\ĐATN\src\9_query\module_4_evaluation\2_evaluate_answers.py

import os
import json
import time
import warnings
import pandas as pd
from dotenv import load_dotenv
from transformers import AutoTokenizer
from datasets import Dataset

# Import các thành phần của RAGAS và Langchain
from ragas.metrics import Faithfulness, AnswerRelevance
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from langchain_groq import ChatGroq

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

INPUT_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\input\20_retry_graphrag_results.jsonl"
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\output\20_ragas_evaluation_log.jsonl"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# 1. Khởi tạo danh sách API Keys
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

# 2. Khởi tạo Tokenizer
print("⏳ Đang tải Llama-3 Tokenizer...")
try:
    llama_tokenizer = AutoTokenizer.from_pretrained("NousResearch/Meta-Llama-3-8B")
except Exception as e:
    raise RuntimeError(f"Lỗi tải Tokenizer: {e}")

def extract_plain_context_list(context_data):
    """RAGAS yêu cầu Context phải là một list các chuỗi, không phải một chuỗi gộp."""
    descriptions = []
    for item in context_data:
        for point in item.get("points", []):
            desc = point.get("description", "").strip()
            if desc:
                descriptions.append(desc)
    return descriptions if descriptions else [""]

def count_tokens(text):
    try:
        return len(llama_tokenizer.encode(text))
    except Exception:
        return int(len(text.split()) * 1.3)

def load_processed_queries(output_path):
    processed = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        processed.add(json.loads(line)["query"])
                    except Exception:
                        continue
    return processed

def main():
    processed_queries = load_processed_queries(OUTPUT_FILE)
    if processed_queries:
        print(f"-> Phát hiện {len(processed_queries)} câu đã chấm điểm. Tiến hành chạy tiếp...")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    key_index = 0
    
    for idx, row in enumerate(rows, 1):
        query = row.get("query")
        
        if query in processed_queries:
            continue
            
        answer = row.get("answer", "")
        clean_context_list = extract_plain_context_list(row.get("context", []))
        
        # Đếm token tổng quan để tính toán Sleep Dynamic
        combined_text = query + " " + " ".join(clean_context_list) + " " + answer
        input_tokens = count_tokens(combined_text)
        
        print(f"\n[{idx}/{len(rows)}] Đang xử lý: {query[:60]}...")
        print(f"   -> Ước tính dung lượng Text: {input_tokens} tokens")

        success = False
        retry_count = 0
        max_retries = 3
        judge_output = None
        
        # Vòng lặp gọi API có thiết lập cấu trúc xoay vòng Key
        while not success and retry_count < max_retries:
            current_key = api_keys[key_index]
            current_key_id = key_index + 1
            key_index = (key_index + 1) % len(api_keys)
            
            try:
                print(f"   -> Đang sử dụng Tài khoản/Key #{current_key_id} để chạy RAGAS...")
                
                # 1. Khởi tạo LLM với Key hiện tại (Tắt tự động retry của Langchain để tự quản lý)
                chat_model = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    groq_api_key=current_key,
                    temperature=0.1,
                    max_retries=0 
                )
                judge_llm = LangchainLLMWrapper(chat_model)
                
                # 2. Khởi tạo Metrics với LLM hiện tại
                metric_faithfulness = Faithfulness(llm=judge_llm)
                metric_relevance = AnswerRelevance(llm=judge_llm)
                
                # 3. Tạo Dataset 1 dòng cho RAGAS
                single_dataset = Dataset.from_dict({
                    "question": [query],
                    "answer": [answer],
                    "contexts": [clean_context_list]
                })
                
                # 4. Thực thi đánh giá (ẩn thanh tiến trình mặc định)
                result = evaluate(
                    dataset=single_dataset,
                    metrics=[metric_faithfulness, metric_relevance],
                    show_progress=False
                )
                
                # Trích xuất kết quả từ pandas dataframe nội bộ của RAGAS
                df_res = result.to_pandas()
                f_score = df_res['faithfulness'].iloc[0]
                ar_score = df_res['answer_relevance'].iloc[0]
                
                # Quy đổi thang 1 (RAGAS) sang thang 10 cho dễ nhìn
                judge_output = {
                    "faithfulness_score": round(f_score * 10, 2) if not pd.isna(f_score) else 0,
                    "answer_relevance_score": round(ar_score * 10, 2) if not pd.isna(ar_score) else 0
                }
                success = True
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e).lower()
                if "429" in error_msg or "rate limit" in error_msg:
                    print(f"   ⚠️ Key #{current_key_id} dính giới hạn Rate Limit. Đang xoay vòng key...")
                else:
                    print(f"   ⚠️ Phát sinh lỗi (Lần thử {retry_count}/{max_retries}): {e}")
                time.sleep(3)
        
        if not success or judge_output is None:
            print(f"❌ Hệ thống thất bại liên tiếp tại câu {idx}. Tạm dừng tiến trình.")
            break

        # Đóng gói và ghi dữ liệu
        evaluation_record = {
            "query": query,
            "context_extracted": clean_context_list,
            "answer": answer,
            "evaluation": judge_output
        }
        
        with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
            out_f.write(json.dumps(evaluation_record, ensure_ascii=False) + "\n")
        print(f"   ✅ Đã chấm xong! Điểm: Faithfulness={judge_output['faithfulness_score']}, Relevance={judge_output['answer_relevance_score']}")

        # Lớp giáp bảo vệ Rate Limit động
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
    print("🎉 HOÀN THÀNH QUÁ TRÌNH CHẤM ĐIỂM (RAGAS STANDARD)")
    print(f"Kết quả được lưu trữ an toàn tại: {OUTPUT_FILE}")
    print("============================================================")

if __name__ == "__main__":
    main()