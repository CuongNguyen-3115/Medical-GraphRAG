import pandas as pd
from rapidfuzz import process, utils
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 1. Cấu hình đường dẫn
file_path = r'C:\1. Project\2. DoAn_GraphRAG\Data\Medical_Metadata.xlsx'
output_path = r'C:\1. Project\2. DoAn_GraphRAG\Data\Domain_Standardization_Suggestions.xlsx'

def suggest_standard_domain():
    # Đọc dữ liệu từ cột M (Cột 12 nếu tính từ 0, hoặc dùng tên 'domain')
    df = pd.read_excel(file_path)
    # Lấy danh sách duy nhất và loại bỏ NaN
    raw_domains = df.iloc[:, 12].dropna().unique().tolist() 
    
    # Load model ngôn ngữ (hỗ trợ tiếng Việt tốt cho y tế)
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(raw_domains)
    
    suggestions = []
    processed = set()

    for i, domain in enumerate(raw_domains):
        if domain in processed:
            continue
            
        # Tìm các domain tương đồng dựa trên Cosine Similarity (Ngữ nghĩa)
        similarities = cosine_similarity([embeddings[i]], embeddings)[0]
        
        # Lấy các index có độ tương đồng > 0.82 (ngưỡng an toàn cho y tế)
        related_indices = [idx for idx, score in enumerate(similarities) if score > 0.8]
        
        group = [raw_domains[idx] for idx in related_indices]
        
        if len(group) > 1:
            # Gợi ý nhãn chuẩn: Ưu tiên nhãn ngắn gọn hoặc phổ biến nhất
            # Ở đây ta chọn nhãn có độ dài trung bình để tránh quá vắn tắt hoặc quá dài
            suggested_label = min(group, key=len) 
            
            suggestions.append({
                "Nhóm tương đồng": ", ".join(group),
                "Gợi ý nhãn chuẩn": suggested_label,
                "Ghi chú": "Cần kiểm tra thủ công"
            })
            processed.update(group)
        else:
            suggestions.append({
                "Nhóm tương đồng": domain,
                "Gợi ý nhãn chuẩn": domain,
                "Ghi chú": "Duy nhất"
            })
            processed.add(domain)

    # Xuất ra file Excel để bạn xử lý thủ công
    result_df = pd.DataFrame(suggestions)
    result_df.to_excel(output_path, index=False)
    print(f"Đã xuất file gợi ý tại: {output_path}")

if __name__ == "__main__":
    suggest_standard_domain()