# C:\1. Project\ĐATN\src\10_query_local\module_1_embedding\1_embed_nodes_neo4j.py

import os
import time
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import warnings
import torch  # Bổ sung thư viện torch để quản lý CPU

# Tắt các cảnh báo không cần thiết từ thư viện
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==========================================
# TỐI ƯU HÓA PHẦN CỨNG (CPU 4 Core / 8 Thread)
# ==========================================
# Cấp cho mô hình AI 6 luồng, giữ lại 2 luồng cho HĐH và Neo4j để tránh treo máy
torch.set_num_threads(6) 

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # <-- THAY BẰNG MẬT KHẨU CỦA BẠN

MODEL_NAME = 'Keepitreal/vietnamese-sbert'
EMBEDDING_DIM = 768
BATCH_SIZE = 200    # Hạ xuống 200 để phù hợp với laptop Aspire 3

# ==========================================
# 2. CÁC HÀM TƯƠNG TÁC NEO4J & NHÚNG
# ==========================================
def create_vector_index(tx):
    """Tạo Vector Index trong Neo4j (Chỉ chạy 1 lần)"""
    print("-> Đang kiểm tra và khởi tạo Vector Index...")
    tx.run("DROP INDEX entity_embeddings IF EXISTS")
    
    query = f"""
    CREATE VECTOR INDEX entity_embeddings FOR (e:Entity) ON (e.embedding)
    OPTIONS {{indexConfig: {{
        `vector.dimensions`: {EMBEDDING_DIM},
        `vector.similarity_function`: 'cosine'
    }}}}
    """
    tx.run(query)
    print("   ✅ Khởi tạo Vector Index 'entity_embeddings' thành công!")

def fetch_unembedded_nodes(tx):
    """Lấy danh sách các nodes CHƯA có vector embedding"""
    print("-> Đang quét cơ sở dữ liệu để tìm các Node cần xử lý...")
    query = """
    MATCH (e:Entity) 
    WHERE e.embedding IS NULL 
    RETURN e.id AS id, e.name AS name, e.description AS desc
    """
    result = tx.run(query)
    nodes = [{"id": record["id"], "name": record["name"], "desc": record["desc"]} for record in result]
    print(f"   🔎 Tìm thấy {len(nodes)} nodes cần được nhúng Vector.")
    return nodes

def update_embeddings_in_db(tx, batch_data):
    """Cập nhật mảng Vector ngược lại vào Neo4j theo lô"""
    query = """
    UNWIND $batch AS data
    MATCH (e:Entity {id: data.id})
    SET e.embedding = data.embedding
    """
    tx.run(query, batch=batch_data)

# ==========================================
# 3. LUỒNG THỰC THI CHÍNH
# ==========================================
def main():
    print("="*60)
    print("🚀 BẮT ĐẦU TIẾN TRÌNH NHÚNG GRAPH (TỐI ƯU CHO LAPTOP 8 THREADS)")
    print("="*60)
    
    # 3.1. Tải mô hình
    print(f"⏳ Đang tải mô hình NLP [{MODEL_NAME}] (Vui lòng chờ)...")
    start_time = time.time()
    embedder = SentenceTransformer(MODEL_NAME)
    print(f"✅ Tải mô hình thành công! (Mất {round(time.time() - start_time, 1)}s)")

    # 3.2. Kết nối Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Khởi tạo Index
            session.execute_write(create_vector_index)
            
            # Lấy dữ liệu cần nhúng
            nodes_to_process = session.execute_read(fetch_unembedded_nodes)
            
            if not nodes_to_process:
                print("🎉 Mọi Entity đều đã có Vector. Hệ thống hoàn toàn sẵn sàng!")
                return
            
            total_nodes = len(nodes_to_process)
            print(f"\n🔄 Bắt đầu tiến trình Embedding ({total_nodes} nodes). Sẽ mất một lúc trên CPU...")
            
            # 3.3. Xử lý chia lô (Batch Processing) để bảo vệ RAM
            for i in range(0, total_nodes, BATCH_SIZE):
                batch_nodes = nodes_to_process[i : i + BATCH_SIZE]
                
                texts_to_embed = [
                    f"Thực thể: {n['name']}. Mô tả: {n['desc']}" if n['desc'] else f"Thực thể: {n['name']}" 
                    for n in batch_nodes
                ]
                
                embeddings = embedder.encode(texts_to_embed, show_progress_bar=False)
                
                batch_update_data = [
                    {"id": n["id"], "embedding": emb.tolist()} 
                    for n, emb in zip(batch_nodes, embeddings)
                ]
                
                session.execute_write(update_embeddings_in_db, batch_update_data)
                
                processed = min(i + BATCH_SIZE, total_nodes)
                percent = (processed / total_nodes) * 100
                print(f"   [{processed}/{total_nodes}] Đã hoàn thành {percent:.1f}%")

        print("\n============================================================")
        print("🎉 HOÀN TẤT QUÁ TRÌNH NHÚNG DỮ LIỆU ĐỒ THỊ!")
        print("Hệ thống Neo4j hiện đã sẵn sàng để thực hiện Graph-Augmented Vector Retrieval.")
        print("============================================================")
        
    except Exception as e:
        print(f"\n❌ Phát sinh lỗi nghiêm trọng: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()