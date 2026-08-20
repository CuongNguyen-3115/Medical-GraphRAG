import os
import json
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv
from groq import Groq

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
# Neo4j
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # <-- Điền mật khẩu

# Groq
MODEL_NAME = "llama-3.1-8b-instant"
DATASET_SIZE = 50
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\12_query_local\golden_dataset.json"
# ==========================================
# 2. KHỞI TẠO CÁC HÀM XỬ LÝ
# ==========================================
def fetch_random_nodes(tx, limit=50):
    """
    Lấy ngẫu nhiên N nodes từ Neo4j có chứa Description.
    Sử dụng hàm rand() của Cypher để đảm bảo tính ngẫu nhiên.
    """
    query = """
    MATCH (n:Entity)
    WHERE n.description IS NOT NULL AND trim(n.description) <> ""
    WITH n, rand() AS r
    ORDER BY r
    LIMIT $limit
    RETURN n.name AS name, n.description AS description
    """
    result = tx.run(query, limit=limit)
    return [{"name": record["name"], "description": record["description"]} for record in result]

def generate_synthetic_query(client, node_name, node_desc):
    """
    Gọi API Groq để sinh câu hỏi. Được bọc trong vòng lặp Try-Catch 
    để xử lý lỗi 429 Rate Limit (8K TPM).
    """
    prompt = f"""
    Bạn là một chuyên gia y tế đang đóng vai bệnh nhân.
    Dưới đây là thông tin về một thực thể y khoa:
    - Tên thực thể: {node_name}
    - Mô tả: {node_desc}

    Nhiệm vụ: Hãy đặt MỘT câu hỏi tự nhiên mà người dùng thực tế sẽ hỏi để tìm kiếm thông tin này.
    
    Yêu cầu BẮT BUỘC (Tự hủy nếu vi phạm):
    1. KHÔNG BAO GIỜ được nhắc trực tiếp tên thực thể "{node_name}" trong câu hỏi.
    2. Câu hỏi phải dựa vào các đặc điểm, tính chất, tác dụng hoặc cơ chế trong phần Mô tả.
    3. Chỉ trả về duy nhất nội dung câu hỏi, KHÔNG giải thích, KHÔNG có dấu ngoặc kép.
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7, # Để mô hình sáng tạo cách đặt câu hỏi đa dạng
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                print(f"   ⚠️ Đạt giới hạn API (Rate Limit). Hệ thống tự động ngủ 60 giây... (Lần thử {attempt + 1}/{max_retries})")
                time.sleep(60) # Đợi 1 phút để API Groq reset dung lượng
            else:
                print(f"   ❌ Lỗi API không xác định: {e}")
                return None
    return None

# ==========================================
# 3. LUỒNG THỰC THI CHÍNH
# ==========================================
def main():
    print("="*60)
    print("🚀 BẮT ĐẦU TẠO GOLDEN DATASET TỰ ĐỘNG (SYNTHETIC QUERIES)")
    print("="*60)

    # 1. Kết nối Neo4j và lấy Nodes
    print(f"⏳ Đang trích xuất ngẫu nhiên {DATASET_SIZE} nodes từ Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            nodes = session.execute_read(fetch_random_nodes, limit=DATASET_SIZE)
    except Exception as e:
        print(f"❌ Lỗi kết nối Neo4j: {e}")
        return
    finally:
        driver.close()

    print(f"✅ Đã lấy thành công {len(nodes)} nodes hợp lệ.\n")

    # 2. Khởi tạo Groq Client
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Không tìm thấy API Key của Groq!")
        return
    client = Groq(api_key=api_key)

    golden_dataset = []

    # 3. Chạy vòng lặp sinh câu hỏi
    for idx, node in enumerate(nodes, 1):
        name = node["name"]
        desc = node["description"]
        print(f"[{idx}/{DATASET_SIZE}] Đang tạo câu hỏi cho: {name}")
        
        # Mẹo: Sleep nhẹ 1.5s giữa mỗi request để trải đều tải, tránh kích hoạt Rate Limit đột ngột
        time.sleep(1.5) 
        
        query = generate_synthetic_query(client, name, desc)
        
        if query:
            print(f"   -> Câu hỏi sinh ra: {query}")
            golden_dataset.append({
                "id": idx,
                "query": query,
                "expected_node": name,
                "description": desc
            })
        else:
            print(f"   -> Bỏ qua node này do lỗi sinh câu hỏi.")

    # 4. Lưu ra file JSON
    print("\n" + "="*60)
    print("💾 ĐANG LƯU DỮ LIỆU...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(golden_dataset, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 Hoàn tất! Đã lưu {len(golden_dataset)} cặp Query - Node vào file '{OUTPUT_FILE}'.")
    print("="*60)

if __name__ == "__main__":
    main()