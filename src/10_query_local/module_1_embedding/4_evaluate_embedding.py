# C:\1. Project\ĐATN\src\10_query_local\module_1_embedding\4_evaluate_embedding.py

import os
import json
import logging
import warnings
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# Tắt cảnh báo
warnings.filterwarnings("ignore")
logging.getLogger("neo4j").setLevel(logging.ERROR)

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # <-- Sửa mật khẩu
DATASET_FILE = r"C:\1. Project\ĐATN\Data\12_query_local\golden_dataset.json"

MODEL_NAME = 'intfloat/multilingual-e5-small'
TOP_K_EVAL = 10 # Quét top 10 để tính toán cho rộng

# ==========================================
# 2. HÀM TRUY XUẤT TỪ NEO4J
# ==========================================
def search_vector_in_neo4j(tx, query_vector, top_k=10):
    """Sử dụng Vector Index hiện tại để tìm Top K nodes giống nhất"""
    query = """
    CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $query_vector)
    YIELD node AS center, score
    RETURN center.name AS name, score
    ORDER BY score DESC
    """
    result = tx.run(query, query_vector=query_vector, top_k=top_k)
    return [record["name"] for record in result]

# ==========================================
# 3. LUỒNG ĐÁNH GIÁ CHÍNH
# ==========================================
def main():
    print("="*60)
    print("📊 HỆ THỐNG ĐÁNH GIÁ CHẤT LƯỢNG EMBEDDING (IR METRICS)")
    print("="*60)

    # 1. Load Dataset
    if not os.path.exists(DATASET_FILE):
        print(f"❌ Không tìm thấy file {DATASET_FILE}!")
        return
        
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    total_queries = len(dataset)
    print(f"-> Đã tải {total_queries} câu hỏi từ Golden Dataset.")

    # 2. Khởi tạo Model
    print(f"-> Đang tải mô hình nhúng [{MODEL_NAME}]...")
    embedder = SentenceTransformer(MODEL_NAME)

    # 3. Khởi tạo kết nối DB
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # 4. Các biến lưu trữ kết quả
    hits_at_1 = 0
    hits_at_5 = 0
    hits_at_10 = 0
    reciprocal_ranks = []
    
    print("\n⏳ Đang tiến hành quét Vector Search và Chấm điểm...")
    print("-" * 60)
    
    try:
        with driver.session() as session:
            for item in dataset:
                query_text = item['query']
                expected_node = item['expected_node'].upper() # Format chuẩn in hoa
                
                # Bơm câu hỏi qua Model để lấy Vector
                query_text_for_e5 = f"query: {query_text}"
                query_vector = embedder.encode(query_text_for_e5, show_progress_bar=False).tolist()
                
                # Truy xuất Top 10 từ DB
                retrieved_nodes = session.execute_read(search_vector_in_neo4j, query_vector, TOP_K_EVAL)
                retrieved_nodes = [node.upper() for node in retrieved_nodes] # Chuyển in hoa để so sánh
                
                # Tìm vị trí (Rank) của expected_node trong danh sách trả về
                rank = 0
                if expected_node in retrieved_nodes:
                    rank = retrieved_nodes.index(expected_node) + 1 # Index bắt đầu từ 0 nên phải +1
                
                # Cập nhật Metrics
                if rank > 0:
                    reciprocal_ranks.append(1.0 / rank)
                    if rank == 1: hits_at_1 += 1
                    if rank <= 5: hits_at_5 += 1
                    if rank <= 10: hits_at_10 += 1
                else:
                    reciprocal_ranks.append(0.0)
                
                # In log 1 số câu bị sai để debug
                if rank == 0 or rank > 5:
                    print(f"[THẤT BẠI] Câu: '{query_text[:50]}...'")
                    print(f"   -> Kỳ vọng: {expected_node}")
                    print(f"   -> Thực tế máy tìm thấy (Top 3): {retrieved_nodes[:3]}")

    except Exception as e:
        print(f"❌ Lỗi trong quá trình truy xuất: {e}")
    finally:
        driver.close()

    # 5. Tính toán tổng kết
    hr_1 = (hits_at_1 / total_queries) * 100
    hr_5 = (hits_at_5 / total_queries) * 100
    hr_10 = (hits_at_10 / total_queries) * 100
    mrr_10 = sum(reciprocal_ranks) / total_queries

    # 6. In Báo cáo
    print("\n" + "="*60)
    print("🏆 BÁO CÁO KẾT QUẢ ĐÁNH GIÁ (EVALUATION REPORT)")
    print(f"Mô hình sử dụng : {MODEL_NAME}")
    print(f"Tổng số mẫu test: {total_queries}")
    print("="*60)
    print(f"Hit Rate @ 1 (HR@1)  : {hr_1:.2f}% (Tỷ lệ top 1 chính xác luôn)")
    print(f"Hit Rate @ 5 (HR@5)  : {hr_5:.2f}% (Tỷ lệ lọt top 5 - Mức chuẩn RAG)")
    print(f"Hit Rate @ 10 (HR@10): {hr_10:.2f}%")
    print(f"Mean Reciprocal Rank (MRR@10): {mrr_10:.4f}")
    print("="*60)
    
    # 7. Nhận xét tự động
    if hr_5 >= 70.0 and mrr_10 >= 0.6:
        print("✅ KẾT LUẬN: Mô hình hoạt động RẤT TỐT. Đủ tiêu chuẩn Production.")
    elif hr_5 >= 50.0:
        print("⚠️ KẾT LUẬN: Mô hình ở mức TRUNG BÌNH. Sẽ gặp khó với câu hỏi phức tạp.")
        print("   -> Đề xuất: Cần thử nghiệm thêm kỹ thuật HyDE hoặc đổi model.")
    else:
        print("❌ KẾT LUẬN: Mô hình hoạt động KÉM so với dữ liệu. Vector bị mù ngữ nghĩa.")
        print("   -> Đề xuất BẮT BUỘC: Đổi sang model 'multilingual-e5' hoặc nhúng thêm context cho node.")

if __name__ == "__main__":
    main()