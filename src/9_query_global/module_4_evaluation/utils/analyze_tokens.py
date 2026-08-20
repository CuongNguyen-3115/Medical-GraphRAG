import os
import json
import statistics
import tiktoken

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\input\102_graphrag_results.jsonl"
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\input\token_statistics_report.txt"

def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Hàm đếm số lượng token của một đoạn văn bản dựa trên chuẩn BPE của OpenAI (tiktoken).
    Chuẩn cl100k_base là chuẩn chung được sử dụng rộng rãi, độ sai lệch so với Llama-3 là không đáng kể.
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"Lỗi khi đếm token: {e}")
        return 0

def analyze_tokens():
    if not os.path.exists(INPUT_FILE):
        print(f"Không tìm thấy file dữ liệu tại: {INPUT_FILE}")
        return

    total_tokens_list = []
    context_tokens_list = []
    
    max_tokens = 0
    heaviest_query = ""

    print("Đang quét và phân tích token của dữ liệu, vui lòng đợi...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line_idx, line in enumerate(f):
            try:
                # Đọc từng dòng JSONL
                data = json.loads(line.strip())
                
                query = data.get("query", "")
                # Parse danh sách raw json thành chuỗi để đếm token
                context = json.dumps(data.get("context", []), ensure_ascii=False)
                answer = data.get("answer", "")
                
                # Đếm token cho từng phần
                q_tokens = count_tokens(query)
                c_tokens = count_tokens(context)
                a_tokens = count_tokens(answer)
                
                total = q_tokens + c_tokens + a_tokens
                
                total_tokens_list.append(total)
                context_tokens_list.append(c_tokens)
                
                # Tìm kiếm câu hỏi tốn kém nhất
                if total > max_tokens:
                    max_tokens = total
                    heaviest_query = query
                    
            except json.JSONDecodeError:
                print(f"⚠️ Lỗi định dạng JSON ở dòng {line_idx + 1}")
                continue

    if not total_tokens_list:
        print("Không có dữ liệu hợp lệ để phân tích.")
        return
        
    # --- TÍNH TOÁN THỐNG KÊ (EDA) ---
    num_records = len(total_tokens_list)
    mean_tokens = statistics.mean(total_tokens_list)
    min_tokens = min(total_tokens_list)
    
    # Phương sai và Độ lệch chuẩn yêu cầu ít nhất 2 điểm dữ liệu
    variance_tokens = statistics.variance(total_tokens_list) if num_records > 1 else 0
    stdev_tokens = statistics.stdev(total_tokens_list) if num_records > 1 else 0
    
    mean_context = statistics.mean(context_tokens_list)

    # --- ĐÓNG GÓI BÁO CÁO ---
    report = []
    report.append("="*60)
    report.append("BÁO CÁO THỐNG KÊ TÀI NGUYÊN TOKEN (EDA)")
    report.append("="*60)
    report.append(f"Số lượng truy vấn đã phân tích: {num_records} câu")
    report.append(f"1. Token Trung bình / 1 truy vấn:   {mean_tokens:.2f} tokens")
    report.append(f"2. Trong đó, Token Context thô:      {mean_context:.2f} tokens")
    report.append(f"3. Token Nhỏ nhất (Min):             {min_tokens} tokens")
    report.append(f"4. Token Lớn nhất (Max):             {max_tokens} tokens")
    report.append(f"5. Phương sai (Variance):            {variance_tokens:.2f}")
    report.append(f"6. Độ lệch chuẩn (Std Dev):          {stdev_tokens:.2f}")
    report.append("-" * 60)
    report.append("🔥 CÂU HỎI TIÊU TỐN NHIỀU TÀI NGUYÊN NHẤT:")
    report.append(f"[{max_tokens} tokens] -> {heaviest_query}")
    report.append("="*60)

    report_text = "\n".join(report)
    
    # In ra màn hình console
    print("\n" + report_text)
    
    # Ghi ra file output đúng theo yêu cầu
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        out_f.write(report_text)
        
    print(f"\n✅ Đã lưu báo cáo chi tiết thành công tại:\n{OUTPUT_FILE}")

if __name__ == "__main__":
    analyze_tokens()