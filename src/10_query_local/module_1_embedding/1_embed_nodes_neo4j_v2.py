# C:\1. Project\ĐATN\src\10_query_local\module_1_embedding\1_embed_nodes_neo4j_v2.py

import os
import time
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import warnings
import torch

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Tối ưu cho CPU Laptop của bạn
torch.set_num_threads(6)

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # <-- Điền mật khẩu

# Sử dụng mô hình chuẩn SOTA của Microsoft (Hỗ trợ 100 ngôn ngữ, cực nhẹ)
MODEL_NAME = 'intfloat/multilingual-e5-small'
EMBEDDING_DIM = 384 # Chú ý: Dòng E5-small tạo ra vector 384 chiều, giúp tăng tốc độ search lên gấp đôi!
BATCH_SIZE = 150    

# ==========================================
# 2. CÁC HÀM NEO4J
# ==========================================
def recreate_vector_index(tx):
    """Xóa Index cũ 768 chiều, tạo lại Index mới 384 chiều"""
    print("-> Đang cấu hình lại Vector Index (384 chiều)...")
    tx.run("DROP INDEX entity_embeddings IF EXISTS")
    
    query = f"""
    CREATE VECTOR INDEX entity_embeddings FOR (e:Entity) ON (e.embedding)
    OPTIONS {{indexConfig: {{
        `vector.dimensions`: {EMBEDDING_DIM},
        `vector.similarity_function`: 'cosine'
    }}}}
    """
    tx.run(query)

def fetch_nodes_with_1hop_context(tx):
    """
    [QUAN TRỌNG NHẤT] Kéo Node kèm theo thông tin của các Cạnh lân cận 
    để tạo ra một chuỗi 'Ngữ cảnh Đồ thị' hoàn chỉnh trước khi nhúng.
    """
    print("-> Đang quét Đồ thị và đóng gói Enriched Context...")
    query = """
    MATCH (n:Entity)
    // Kéo ngẫu nhiên tối đa 5 liên kết quan trọng nhất của Node này
    OPTIONAL MATCH (n)-[r:RELATED_TO]-(m:Entity)
    WITH n, collect(m.name + " (" + coalesce(r.description, "") + ")")[..5] AS neighbors
    RETURN n.id AS id, n.name AS name, n.description AS desc, neighbors
    """
    result = tx.run(query)
    return [{"id": record["id"], "name": record["name"], "desc": record["desc"], "neighbors": record["neighbors"]} for record in result]

def update_embeddings_in_db(tx, batch_data):
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
    print("="*70)
    print("🚀 BẮT ĐẦU NHÚNG ĐỒ THỊ V2 (ENRICHED CONTEXT + E5 MODEL)")
    print("="*70)
    
    print(f"⏳ Đang tải mô hình [{MODEL_NAME}]...")
    # Thêm tham số model_kwargs để đảm bảo load đúng định dạng
    embedder = SentenceTransformer(MODEL_NAME) 
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 1. Reset Index
            session.execute_write(recreate_vector_index)
            
            # 2. Lấy dữ liệu 1-hop
            nodes_to_process = session.execute_read(fetch_nodes_with_1hop_context)
            total_nodes = len(nodes_to_process)
            print(f"\n🔄 Bắt đầu tiến trình Embedding ({total_nodes} nodes). Vui lòng cắm sạc laptop...")
            
            # 3. Batch Processing
            for i in range(0, total_nodes, BATCH_SIZE):
                batch_nodes = nodes_to_process[i : i + BATCH_SIZE]
                texts_to_embed = []
                
                for n in batch_nodes:
                    name = n['name']
                    desc = n['desc'] if n['desc'] else "Không có mô tả"
                    
                    # Nối các liên kết lại thành 1 chuỗi
                    neighbors_str = ", ".join(n['neighbors']) if n['neighbors'] else "Không có"
                    
                    # CÚ PHÁP BẮT BUỘC CỦA DÒNG E5: Phải có chữ 'passage: ' ở đầu
                    rich_text = f"passage: Thực thể: {name}. Mô tả: {desc}. Liên kết với: {neighbors_str}"
                    texts_to_embed.append(rich_text)
                
                # Encode text thành Vector 384 chiều
                embeddings = embedder.encode(texts_to_embed, show_progress_bar=False)
                
                batch_update_data = [
                    {"id": n["id"], "embedding": emb.tolist()} 
                    for n, emb in zip(batch_nodes, embeddings)
                ]
                
                session.execute_write(update_embeddings_in_db, batch_update_data)
                
                processed = min(i + BATCH_SIZE, total_nodes)
                percent = (processed / total_nodes) * 100
                print(f"   [{processed}/{total_nodes}] Đã hoàn thành {percent:.1f}%")

        print("\n" + "="*70)
        print("🎉 HOÀN TẤT NÂNG CẤP VECTOR ĐỒ THỊ LÊN VERSION 2!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()