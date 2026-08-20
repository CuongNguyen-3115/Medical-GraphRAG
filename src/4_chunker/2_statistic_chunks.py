import json
import pandas as pd
import os

# --- CẤU HÌNH ĐƯỜNG DẪN ---
CHUNK_FILE_PATH = r"C:\1. Project\ĐATN\Data\04_Chunks\medical_chunks_merged.json"

def analyze_chunks(file_path):
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại {file_path}")
        return

    # 1. Tải dữ liệu từ file JSON
    print(f"Đang đọc dữ liệu từ: {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. Trích xuất thông tin token_count từ metadata
    # Dùng list comprehension để lấy dữ liệu nhanh
    token_counts = [chunk['metadata']['token_count'] for chunk in data if 'metadata' in chunk]
    
    if not token_counts:
        print("Không tìm thấy thông tin token_count trong file.")
        return

    # 3. Chuyển sang Pandas Series để tính toán thống kê
    s = pd.Series(token_counts)

    # 4. Tính toán các chỉ số
    stats = {
        "Tổng số chunk": len(s),
        "Tổng số token": s.sum(),
        "Token nhỏ nhất": s.min(),
        "Token lớn nhất": s.max(),
        "Trung bình (Mean)": round(s.mean(), 2),
        "Trung vị (Median)": s.median(),
        "Độ lệch chuẩn (Std)": round(s.std(), 2),
        # "Phân vị 25% (Q1)": s.quantile(0.25),
        # "Phân vị 75% (Q3)": s.quantile(0.75)
    }

    # 5. Hiển thị kết quả
    print("\n" + "="*40)
    print("BÁO CÁO THỐNG KÊ CHUNKS")
    print("="*40)
    for key, value in stats.items():
        print(f"{key:.<25}: {value:,}")
    print("="*40)

    # 6. Kiểm tra các chunk "bất thường" (Outliers)
    # Ví dụ: Chunk nhỏ hơn 100 token có thể là header rác hoặc nội dung quá ngắn
    short_chunks = s[s < 200].count()
    long_chunks = s[s > 2000].count()
    
    print(f"Số chunk < 200 token: {short_chunks} ")
    print(f"Số chunk > 2000 token: {long_chunks} ")

if __name__ == "__main__":
    analyze_chunks(CHUNK_FILE_PATH)