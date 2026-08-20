# Lớp chứa các câu lệnh Cypher (Vector Search, Lấy Node, Lấy Edge 1-hop)

import os
from neo4j import GraphDatabase
import warnings
import logging

# Tắt cảnh báo
warnings.filterwarnings("ignore")

# Tắt cảnh báo "deprecation" khó chịu của driver Neo4j
logging.getLogger("neo4j").setLevel(logging.ERROR)

class GraphRetriever:
    """
    Trái tim của Local Search: Kết hợp Vector Retrieval và Graph Traversal.
    """
    def __init__(self, uri="neo4j://localhost:7687", user="neo4j", password="12345678"): # <-- Sửa mật khẩu
        print("⏳ Đang kết nối tới CSDL Đồ thị Neo4j...")
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Kiểm tra kết nối
            self.driver.verify_connectivity()
            print("✅ Đã kết nối Neo4j thành công (Graph Retriever Ready)!")
        except Exception as e:
            raise RuntimeError(f"❌ Không thể kết nối Neo4j: {e}")

    def close(self):
        self.driver.close()

    def retrieve_context(self, query_vector: list, search_term: str = "", top_k: int = 5) -> list:
        """
        [CẬP NHẬT HYBRID SEARCH] 
        Kết hợp Tìm kiếm chính xác (Keyword Exact Match) và Tìm kiếm ngữ nghĩa (Vector Search).
        Giải quyết triệt để lỗi "mù" từ khóa tiếng Latinh/Tiếng Anh chuyên ngành.
        """
        # Câu lệnh Cypher Hybrid sử dụng UNION để gộp 2 nhánh tìm kiếm
        cypher_query = """
        CALL {
            // NHÁNH 1: TÌM KIẾM KEYWORD (Full-text / Substring Match)
            // Bắt chặt các từ khóa chuyên ngành, tên thuốc Latinh
            MATCH (n:Entity)
            WHERE $search_term <> "" AND toLower(n.name) CONTAINS toLower($search_term)
            RETURN n AS center, 1.0 AS score  // Cho điểm tuyệt đối (1.0) nếu khớp tên
            LIMIT 3
            
            UNION
            
            // NHÁNH 2: TÌM KIẾM VECTOR (Semantic Match)
            // Bắt ngữ nghĩa tiếng Việt (triệu chứng, mô tả, cơ chế)
            CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $query_vector)
            YIELD node AS center, score
            RETURN center, score
        }
        // Gộp kết quả, ưu tiên điểm cao nhất (để loại bỏ trùng lặp nếu 1 node xuất hiện ở cả 2 nhánh)
        WITH center, max(score) AS final_score
        ORDER BY final_score DESC
        LIMIT $top_k
        
        // --- PHẦN DƯỚI GIỮ NGUYÊN: KÉO 1-HOP VÀ ĐÓNG GÓI ---
        OPTIONAL MATCH (center)-[r:RELATED_TO]-(neighbor:Entity)
        WITH center, final_score, r, neighbor
        ORDER BY r.weight DESC
        
        WITH center, final_score, collect({
            neighbor_name: neighbor.name,
            relation_desc: r.description,
            weight: r.weight
        })[..15] AS relationships
        
        RETURN center.name AS entity_name,
               center.description AS entity_desc,
               final_score AS score,
               relationships
        ORDER BY final_score DESC
        """
        
        results = []
        try:
            with self.driver.session() as session:
                # Truyền thêm biến $search_term vào Neo4j
                records = session.run(cypher_query, top_k=top_k, query_vector=query_vector, search_term=search_term)
                
                for record in records:
                    raw_rels = record["relationships"]
                    clean_rels = [rel for rel in raw_rels if rel.get("neighbor_name") is not None]
                    
                    results.append({
                        "entity": record["entity_name"],
                        "description": record["entity_desc"],
                        "similarity_score": round(record["score"], 4),
                        "relationships": clean_rels
                    })
            return results
            
        except Exception as e:
            print(f"❌ Lỗi khi truy vấn Đồ thị: {e}")
            return []

# ==========================================
# KHỐI KIỂM TRA ĐỘC LẬP (UNIT TEST)
# ==========================================
if __name__ == "__main__":
    import sys
    import json
    
    # Mẹo để import được file từ thư mục khác ngang hàng
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    try:
        from module_1_embedding.embedding_client import EmbeddingClient
    except ImportError:
        print("⚠️ Không tìm thấy module_1_embedding. Đảm bảo bạn chạy code đúng thư mục.")
        sys.exit(1)

    print("="*60)
    print("🧪 KIỂM TRA TÍCH HỢP: EMBEDDING + GRAPH RETRIEVAL (TOP K=5)")
    print("="*60)

    # 1. Khởi tạo 2 Clients
    embedder = EmbeddingClient()
    retriever = GraphRetriever() # Đừng quên sửa pass Neo4j ở hàm __init__

    # 2. Câu hỏi test
    test_query = "Tác dụng phụ của Bạch cầu là gì?"
    print(f"\n🗣️ Câu hỏi: '{test_query}'")

    # 3. Chạy luồng
    print("-> Đang nhúng câu hỏi...")
    query_vec = embedder.embed_query(test_query)
    
    print("-> Đang truy vấn Neo4j...")
    retrieved_data = retriever.retrieve_context(query_vec, top_k=5)
    
    # 4. In kết quả đẹp mắt
    print("\n" + "="*40)
    print("📊 KẾT QUẢ TRUY XUẤT ĐỒ THỊ")
    print("="*40)
    
    for idx, data in enumerate(retrieved_data, 1):
        print(f"\n[{idx}] THỰC THỂ: {data['entity']} (Độ trùng khớp Vector: {data['similarity_score']})")
        
        # In tóm tắt description (Cắt ngắn nếu quá dài)
        desc = data['description']
        short_desc = (desc[:100] + "...") if desc and len(desc) > 100 else desc
        print(f"    - Mô tả: {short_desc}")
        
        # In các mối quan hệ
        rels = data['relationships']
        print(f"    - Tìm thấy {len(rels)} mối quan hệ liên kết (Đã lọc top).")
        if rels:
            print(f"      + Ví dụ lân cận: Liên kết với [{rels[0]['neighbor_name']}] (Weight: {rels[0]['weight']})")

    # Đóng kết nối
    retriever.close()
    print("\n🎉 Khối truy xuất Đồ thị hoạt động hoàn hảo!")