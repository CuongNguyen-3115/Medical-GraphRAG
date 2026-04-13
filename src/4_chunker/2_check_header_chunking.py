import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# --- CẤU HÌNH ---
JSON_PATH = Path(r"C:\1. Project\2. DoAn_GraphRAG\Data\04_Chunks\Header_Splitting(2)\medical_master_chunks.json")
REPORT_PATH = JSON_PATH.parent / "token_statistics_report.txt"

def run_token_analysis():
    if not JSON_PATH.exists():
        print(f"Lỗi: Không tìm thấy file tại {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Trích xuất dữ liệu metadata của từng chunk
    df = pd.DataFrame([item['metadata'] for item in data])
    
    # 1. Tính toán các chỉ số thống kê mô tả
    stats = df['token_count'].describe()
    
    # 2. Phân tích các phân khúc (Bins)
    bins = [0, 50, 200, 500, 1000, 2000, 5000]
    labels = ['Siêu ngắn (<50)', 'Ngắn (50-200)', 'Vừa (200-500)', 'Lý tưởng (500-1000)', 'Dài (1000-2000)', 'Quá tải (>2000)']
    df['category'] = pd.cut(df['token_count'], bins=bins, labels=labels)
    category_counts = df['category'].value_counts().sort_index()

    # 3. Tạo báo cáo văn bản
    report = [
        "===================================================",
        "      BÁO CÁO THỐNG KÊ TOKEN - GRAPH RAG PROJECT   ",
        "===================================================",
        f"Ngày thực hiện: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Tổng số chunk: {int(stats['count'])}",
        f"Tổng số token: {df['token_count'].sum():,}",
        "---------------------------------------------------",
        f"Token lớn nhất (Max): {int(stats['max'])}",
        f"Token nhỏ nhất (Min): {int(stats['min'])}",
        f"Trung bình (Mean):    {stats['mean']:.2f}",
        f"Độ lệch chuẩn (Std):  {stats['std']:.2f}",
        "---------------------------------------------------",
        "PHÂN PHỐI THEO PHÂN KHÚC:",
    ]
    for cat, count in category_counts.items():
        percentage = (count / stats['count']) * 100
        report.append(f" - {cat:20}: {count:4} chunks ({percentage:.2f}%)")
    
    report_text = "\n".join(report)
    print(report_text)

    # Lưu báo cáo vào file txt
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # 4. Trực quan hóa dữ liệu (Visualization)
    plt.style.use('seaborn-v0_8') # Hoặc 'ggplot'
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Biểu đồ Histogram
    sns.histplot(df['token_count'], bins=30, kde=True, ax=ax1, color='teal')
    ax1.set_title('Phân phối số lượng Token', fontsize=14)
    ax1.set_xlabel('Số lượng Token')
    ax1.set_ylabel('Tần suất (Số chunk)')

    # Biểu đồ Tròn (Cơ cấu phân khúc)
    category_counts.plot(kind='pie', autopct='%1.1f%%', ax=ax2, startangle=140, cmap='viridis')
    ax2.set_title('Tỷ lệ các phân khúc Chunk', fontsize=14)
    ax2.set_ylabel('')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_token_analysis()