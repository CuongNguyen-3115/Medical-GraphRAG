import os
import json
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# 1. CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG
DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
INPUT_FILE = os.path.join(DATA_DIR, "3_fuzzy_out", "entities_after_fuzzy.json")
OUTPUT_DIR = os.path.join(DATA_DIR, "4_semantic_out")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "entities_after_semantic.json")
SEMANTIC_PAIRS_FILE = os.path.join(OUTPUT_DIR, "semantic_pairs_candidates.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# THAM SỐ ĐỊNH LƯỢNG (Chọn 85% làm ngưỡng an toàn tối ưu cho mô hình E5 trong y khoa)
COSINE_THRESHOLD = 85.0
BATCH_SIZE = 512  # Kích thước phân khối để tính toán vector

def run_semantic_matching():
    # Xác định thiết bị phần cứng
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️ Thiết bị xử lý phần cứng: {device.upper()}")

    # Nạp mô hình
    MODEL_ID = "intfloat/multilingual-e5-base"
    MODEL_CACHE_DIR = r"C:\1. Project\ĐATN\lib\models"
    os.environ["HF_HOME"] = MODEL_CACHE_DIR
    model = SentenceTransformer(MODEL_ID, device=device, cache_folder=MODEL_CACHE_DIR)

    # Đọc dữ liệu đầu vào sau khớp mờ
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        canonical_entities = json.load(f)
    
    num_entities = len(canonical_entities)
    print(f"📥 Đã nạp {num_entities:,} thực thể từ Giai đoạn 3.")

    # 2. VECTOR HÓA TOÀN BỘ DỮ LIỆU (Checklist 4.2)
    print("⏳ Đang tiến hành chuyển đổi thực thể thành không gian Vector (Embedding)...")
    e5_inputs = [f"query: {entity}" for entity in canonical_entities]
    
    # model.encode tự động chạy batching và tối ưu hóa bộ nhớ
    embeddings = model.encode(
        e5_inputs, 
        batch_size=BATCH_SIZE, 
        show_progress_bar=True, 
        convert_to_tensor=True, # Giữ nguyên dạng Tensor để tính toán đại số tuyến tính nhanh
        device=device
    )
    
    # Chuẩn hóa L2 cho toàn bộ Vector để đưa về Unit Length
    embeddings_norm = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    print("✅ Đã hoàn thành xây dựng Ma trận Vector chuẩn hóa.")

    # 3. TÍNH TOÁN TƯƠNG ĐỒNG TOÀN CỤC & TRÍCH XUẤT CẶP ĐỒNG NGHĨA (Checklist 4.3)
    print(f"⏳ Đang quét ma trận song song để tìm các cặp có điểm Cosine >= {COSINE_THRESHOLD}%...")
    
    semantic_pairs = []
    
    # Chia nhỏ ma trận để tính toán theo khối (Chống tràn RAM/VRAM)
    chunk_size = 2000
    for i in tqdm(range(0, num_entities, chunk_size), desc="Xử lý khối ma trận"):
        end_i = min(i + chunk_size, num_entities)
        
        # Lấy ra một lát cắt ma trận (Slice)
        slice_emb = embeddings_norm[i:end_i]
        
        # Phép nhân ma trận đại số tuyến tính: (Chunk_Size x 768) x (768 x Num_Entities) -> (Chunk_Size x Num_Entities)
        similarity_matrix = torch.matmul(slice_emb, embeddings_norm.T) * 100
        
        # Chuyển về CPU numpy để trích xuất chỉ mục
        sim_matrix_np = similarity_matrix.cpu().numpy()
        
        # Lọc các tọa độ vượt ngưỡng định lượng
        rows, cols = np.where(sim_matrix_np >= COSINE_THRESHOLD)
        
        for r, c in zip(rows, cols):
            global_row_idx = i + r
            # Điều kiện: global_row_idx < c để loại bỏ trùng lặp đối xứng (A,B) vs (B,A) và loại chính nó (A,A)
            if global_row_idx < c:
                semantic_pairs.append({
                    "entity_1": canonical_entities[global_row_idx],
                    "entity_2": canonical_entities[c],
                    "cosine_similarity": float(sim_matrix_np[r, c])
                })

    print(f"✨ Hệ thống phát hiện {len(semantic_pairs):,} cặp có sự tương đồng ngữ nghĩa cao.")

    # 4. GOM CỤM LIÊN THÔNG VÀ XUẤT ĐẦU RA KẾT QUẢ
    # Thiết lập cấu trúc cấu trúc dữ liệu ánh xạ (Disjoint Set Union)
    parent = {ent: ent for ent in canonical_entities}
    def find(idx):
        path = []
        while parent[idx] != idx:
            path.append(idx)
            idx = parent[idx]
        for node in path: parent[node] = idx
        return idx
    def union(idx1, idx2):
        root1 = find(idx1)
        root2 = find(idx2)
        if root1 != root2: parent[root1] = root2

    for pair in semantic_pairs:
        union(pair["entity_1"], pair["entity_2"])

    # Tổng hợp các cụm ngữ nghĩa
    clusters = {}
    for entity in canonical_entities:
        root = find(entity)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(entity)

    # Chọn Canonical Name cuối cùng (Chuỗi ngắn nhất trong cụm đồng nghĩa)
    final_semantic_entities = []
    for root, cluster_members in clusters.items():
        canonical = min(cluster_members, key=len)
        final_semantic_entities.append(canonical)

    # Lưu trữ dữ liệu
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(final_semantic_entities), f, ensure_ascii=False, indent=4)
        
    with open(SEMANTIC_PAIRS_FILE, 'w', encoding='utf-8') as f:
        json.dump(semantic_pairs, f, ensure_ascii=False, indent=4)

    print("\n📊 ==================== KẾT QUẢ ĐỊNH LƯỢNG GIAI ĐOẠN 4 ====================")
    print(f"🔹 Số lượng Node đầu vào: {num_entities:,}")
    print(f"🔹 Số lượng Node sau khi hợp nhất ngữ nghĩa: {len(final_semantic_entities):,}")
    print(f"📉 Tỷ lệ thu gọn đồ thị: {((num_entities - len(final_semantic_entities))/num_entities)*100:.2f}%")
    print("==========================================================================")
    print("💾 Đã xuất file entities_after_semantic.json và file danh sách cặp ứng viên.")

if __name__ == "__main__":
    run_semantic_matching()