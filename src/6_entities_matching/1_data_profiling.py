# Thống kê & khám phá dữ liệu
import json
import pandas as pd
import re
from collections import Counter
import os

# 1. ĐỊNH NGHĨA ĐƯỜNG DẪN (Phù hợp với cấu trúc của bạn)
DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
INPUT_FILE = os.path.join(DATA_DIR, "unique_entities_to_map.json")
REPORT_DIR = os.path.join(DATA_DIR, "1_profiling_reports")

# Tạo thư mục chứa báo cáo nếu chưa có
os.makedirs(REPORT_DIR, exist_ok=True)

def load_data(filepath):
    """Checkpoint 1.1: Load dữ liệu"""
    print("⏳ Đang tải dữ liệu...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Chuyển thành DataFrame, in hoa toàn bộ để đồng nhất chuẩn hóa
    df = pd.DataFrame(data, columns=['Entity'])
    df['Entity'] = df['Entity'].astype(str).str.upper().str.strip()
    df.drop_duplicates(inplace=True)
    
    print(f"✅ Đã tải thành công {len(df)} thực thể unique.")
    return df

def profile_special_characters(df):
    """Checkpoint 1.2: Thống kê ký tự đặc biệt"""
    print("⏳ Đang phân tích ký tự đặc biệt...")
    all_chars = "".join(df['Entity'].tolist())
    
    # Giữ lại các ký tự KHÔNG phải là chữ cái (A-Z, Tiếng Việt) và số (0-9)
    # \w bao gồm chữ cái, số và dấu gạch dưới. Ta đổi thành pattern chỉ định rõ hơn
    special_chars = re.sub(r'[A-Z0-9a-zÀ-ỹ\s]', '', all_chars)
    
    char_counts = Counter(special_chars)
    char_df = pd.DataFrame(char_counts.items(), columns=['Character', 'Frequency'])
    char_df = char_df.sort_values(by='Frequency', ascending=False)
    
    char_df.to_csv(os.path.join(REPORT_DIR, "char_frequencies.csv"), index=False, encoding='utf-8-sig')
    print("✅ Đã xuất báo cáo: char_frequencies.csv")

def profile_boundary_tokens(df):
    """Checkpoint 1.3: Thống kê từ vựng đầu/cuối"""
    print("⏳ Đang phân tích token đầu/cuối...")
    start_tokens = []
    end_tokens = []
    
    for entity in df['Entity']:
        tokens = str(entity).split()
        if len(tokens) > 0:
            start_tokens.append(tokens[0])
            end_tokens.append(tokens[-1])
            
    start_df = pd.DataFrame(Counter(start_tokens).items(), columns=['Token', 'Frequency']).sort_values(by='Frequency', ascending=False)
    end_df = pd.DataFrame(Counter(end_tokens).items(), columns=['Token', 'Frequency']).sort_values(by='Frequency', ascending=False)
    
    start_df.head(100).to_csv(os.path.join(REPORT_DIR, "top_start_tokens.csv"), index=False, encoding='utf-8-sig')
    end_df.head(100).to_csv(os.path.join(REPORT_DIR, "top_end_tokens.csv"), index=False, encoding='utf-8-sig')
    print("✅ Đã xuất báo cáo: top_start_tokens.csv & top_end_tokens.csv")

def profile_length_outliers(df):
    """Checkpoint 1.4: Phân tích độ dài và Outliers"""
    print("⏳ Đang phân tích độ dài chuỗi...")
    df['Length'] = df['Entity'].apply(len)
    
    # Thống kê mô tả (Mean, Min, Max)
    desc = df['Length'].describe()
    print("\n--- Thống kê độ dài chuỗi ---")
    print(desc)
    
    # Lọc ra các outliers (Ví dụ: Dưới 3 ký tự hoặc trên 60 ký tự)
    outliers = df[(df['Length'] < 3) | (df['Length'] > 60)]
    outliers.sort_values(by='Length').to_csv(os.path.join(REPORT_DIR, "length_outliers.csv"), index=False, encoding='utf-8-sig')
    print(f"✅ Tìm thấy {len(outliers)} thực thể có độ dài bất thường. Đã xuất báo cáo: length_outliers.csv\n")

if __name__ == "__main__":
    df_entities = load_data(INPUT_FILE)
    profile_special_characters(df_entities)
    profile_boundary_tokens(df_entities)
    profile_length_outliers(df_entities)
    print("🎉 Hoàn tất Giai đoạn 1! Hãy mở thư mục 1_profiling_reports để kiểm tra kết quả.")