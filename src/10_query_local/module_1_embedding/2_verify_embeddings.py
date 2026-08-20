# C:\1. Project\ĐATN\src\10_query_local\module_1_embedding\2_verify_embeddings.py

from neo4j import GraphDatabase

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # <-- Điền mật khẩu của bạn

# Kích thước vector chuẩn của mô hình vietnamese-sbert
EXPECTED_DIM = 385

# ==========================================
# 2. HÀM KIỂM TRA CHUYÊN SÂU
# ==========================================
def verify_embeddings(tx):
    print("⏳ Đang quét cơ sở dữ liệu Neo4j...\n")
    
    # 1. Đếm tổng số Node
    total_query = "MATCH (e:Entity) RETURN count(e) AS total"
    total_nodes = tx.run(total_query).single()["total"]
    
    # 2. Đếm số Node ĐÃ CÓ embedding
    embedded_query = "MATCH (e:Entity) WHERE e.embedding IS NOT NULL RETURN count(e) AS embedded"
    embedded_nodes = tx.run(embedded_query).single()["embedded"]
    
    # 3. Đếm số Node CHƯA CÓ embedding
    missing_query = "MATCH (e:Entity) WHERE e.embedding IS NULL RETURN count(e) AS missing"
    missing_nodes = tx.run(missing_query).single()["missing"]

    # In kết quả thống kê cơ bản
    print("="*40)
    print("📊 BÁO CÁO TOÀN VẸN DỮ LIỆU VECTOR")
    print("="*40)
    print(f"Tổng số Entities   : {total_nodes:,}")
    print(f"Đã nhúng Vector    : {embedded_nodes:,}")
    print(f"Chưa nhúng Vector  : {missing_nodes:,}")
    print("-"*40)

    # 4. Kiểm tra chất lượng (Quality Check) - Kiểm tra ngẫu nhiên 1 Node xem số chiều vector có đúng không
    if embedded_nodes > 0:
        sample_query = """
        MATCH (e:Entity) 
        WHERE e.embedding IS NOT NULL 
        RETURN e.name AS name, size(e.embedding) AS dimension 
        LIMIT 1
        """
        sample = tx.run(sample_query).single()
        actual_dim = sample["dimension"]
        sample_name = sample["name"]
        
        print("\n🔍 KIỂM TRA CHẤT LƯỢNG VECTOR:")
        print(f"-> Entity mẫu: '{sample_name}'")
        print(f"-> Kích thước Vector: {actual_dim} chiều")
        
        if actual_dim == EXPECTED_DIM:
            print("-> Trạng thái: ✅ CHUẨN (Khớp với mô hình vietnamese-sbert)")
        else:
            print(f"-> Trạng thái: ❌ CẢNH BÁO LỖI (Kỳ vọng {EXPECTED_DIM} nhưng thực tế là {actual_dim})")

    # 5. Kết luận chung
    print("\n========================================")
    if total_nodes == embedded_nodes and missing_nodes == 0:
        print("🎉 KẾT LUẬN: THÀNH CÔNG TỐI ĐA (100%)")
        print("Hệ thống Neo4j hoàn toàn sạch và sẵn sàng cho Vector Search!")
    else:
        print(f"⚠️ KẾT LUẬN: CÓ LỖI XẢY RA ({missing_nodes} nodes bị thiếu)")
        print("Vui lòng chạy lại file '1_embed_nodes_neo4j.py' để hệ thống tự động nhúng bù các node còn thiếu.")
    print("========================================")

# ==========================================
# 3. LUỒNG THỰC THI CHÍNH
# ==========================================
def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            session.execute_read(verify_embeddings)
    except Exception as e:
        print(f"\n❌ Không thể kết nối tới Neo4j: {e}")
        print("Hãy đảm bảo bạn đã bấm nút 'Start' Database trên Neo4j Desktop.")
    finally:
        driver.close()

if __name__ == "__main__":
    main()