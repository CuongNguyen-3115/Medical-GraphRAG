import json
import os
import pandas as pd
import tiktoken
import matplotlib.pyplot as plt

# --- CẤU HÌNH ---
INPUT_FILE = r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks\Recursive_Splitting\medical_recursive_chunks.json"
LOG_DIR = r"C:\1. Project\2. DoAn_GraphRAG\logs\4_chunker"
os.makedirs(LOG_DIR, exist_ok=True)

def analyze_chunks():
    # 1. Load dữ liệu
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    # Khởi tạo tokenizer (dùng o200k_base cho Gemini hoặc cl100k_base)
    enc = tiktoken.get_encoding("cl100k_base")

    stats = []
    for item in chunks:
        content = item['content']
        tokens = enc.encode(content)
        
        stats.append({
            "chunk_id": item['chunk_id'],
            "token_count": len(tokens),
            "char_count": len(content),
            "parent_id": item['metadata'].get('parent_chunk_id'),
            "has_h1": 1 if item['metadata'].get('Header_1') else 0,
            "has_h2": 1 if item['metadata'].get('Header_2') else 0
        })

    df = pd.DataFrame(stats)

    # 2. Tính toán các chỉ số quan trọng
    report = {
        "Tổng số chunks": len(df),
        "Số token trung bình": round(df['token_count'].mean(), 2),
        "Số token lớn nhất": df['token_count'].max(),
        "Số token nhỏ nhất": df['token_count'].min(),
        "Độ lệch chuẩn (Std Dev)": round(df['token_count'].std(), 2),
        "Tổng số token hệ thống": df['token_count'].sum(),
        "Tỷ lệ chunk có đủ Metadata (H1 & H2)": f"{(df['has_h1'] & df['has_h2']).mean()*100:.2f}%"
    }

    # 3. Lưu log chi tiết
    report_path = os.path.join(LOG_DIR, "chunking_statistics_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=== BÁO CÁO THỐNG KÊ CHUNKING ===\n")
        for key, value in report.items():
            f.write(f"{key}: {value}\n")
        
        f.write("\n=== TOP 5 CHUNKS DÀI NHẤT (Cần kiểm tra) ===\n")
        f.write(df.nlargest(5, 'token_count').to_string())

    # 4. In ra màn hình để xem nhanh
    print("-" * 30)
    for key, value in report.items():
        print(f"{key}: {value}")
    print("-" * 30)
    print(f"Báo cáo chi tiết đã được lưu tại: {report_path}")

    # (Tùy chọn) Vẽ biểu đồ phân phối nếu bạn muốn trực quan hóa
    # df['token_count'].hist(bins=20)
    # plt.title("Phân phối độ dài Token")
    # plt.show()

if __name__ == "__main__":
    analyze_chunks()