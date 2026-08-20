import os
import json
import logging
import pickle
from collections import defaultdict, Counter
from datetime import datetime

# --- CẤU HÌNH ĐƯỜNG DẪN ---
# Chú ý: Nên kiểm tra lại đường dẫn xem có khớp với thư mục C:\1. Project\ĐATN\Data\06_Entities_preprocessing 
# mà bạn đã lưu ở bước trước không nhé.
INPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities_preprocessing" 
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching\0_exact_matched"
LOG_DIR = r"C:\1. Project\ĐATN\logs\07_exact_matching"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "exact_match_checkpoint.pkl")

# Thiết lập Logging
log_file = os.path.join(LOG_DIR, f"exact_matching_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()])

def load_and_aggregate(input_dir):
    """Đọc file và gom nhóm trực tiếp để tiết kiệm RAM, có Save Progress bằng Pickle"""
    files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    # Khởi tạo Cấu trúc dữ liệu
    processed_files = set()
    groups = defaultdict(lambda: {
        "entity_types": set(),
        "descriptions": set(),
        "source_chunks": set(),
        "occurrence_count": 0
    })
    rel_groups = defaultdict(lambda: {
        "descriptions": set(),
        "weight": 0,
        "source_chunks": set()
    })

    # CƠ CHẾ SAVE PROGRESS (LOAD CHECKPOINT)
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                checkpoint = pickle.load(f)
                processed_files = checkpoint.get('processed_files', set())
                groups.update(checkpoint.get('groups', {}))
                rel_groups.update(checkpoint.get('rel_groups', {}))
            logging.info(f"Đã phục hồi tiến trình: Tiếp tục từ {len(processed_files)} file đã xử lý.")
        except Exception as e:
            logging.error(f"[ERROR] Không thể đọc checkpoint: {e}")

    pending_files = [f for f in files if f not in processed_files]
    logging.info(f"Cần xử lý {len(pending_files)}/{len(files)} files...")

    for i, filename in enumerate(pending_files):
        filepath = os.path.join(input_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                chunk_id = data.get("chunk_id")
                
                # Gom Entity Trực Tiếp
                for ent in data.get("parsed_entities", []):
                    name = ent.get("name", "").strip().upper()
                    etype = ent.get("type", "").strip().upper()
                    if not name: continue
                    
                    if etype: groups[name]["entity_types"].add(etype)
                    if ent.get("description"): groups[name]["descriptions"].add(ent["description"])
                    groups[name]["source_chunks"].add(chunk_id)
                    groups[name]["occurrence_count"] += 1
                    
                # Gom Relationship Trực Tiếp
                for rel in data.get("parsed_relationships", []):
                    source = rel.get("source", "").strip().upper()
                    target = rel.get("target", "").strip().upper()
                    if not source or not target: continue
                    if source == target: continue # Bỏ tự trỏ
                    
                    rel_key = (source, target)
                    if rel.get("description"): rel_groups[rel_key]["descriptions"].add(rel["description"])
                    rel_groups[rel_key]["weight"] += rel.get("weight", 1)
                    rel_groups[rel_key]["source_chunks"].add(chunk_id)

            processed_files.add(filename)
        except Exception as e:
            logging.error(f"[ERROR] Lỗi khi đọc file {filename}: {e}")
            
        # Lưu Checkpoint mỗi 200 file
        if (i + 1) % 200 == 0:
            logging.info(f"  -> Đã xử lý thêm {i + 1}/{len(pending_files)} files. Đang lưu Checkpoint...")
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump({
                    "processed_files": processed_files,
                    "groups": dict(groups),
                    "rel_groups": dict(rel_groups)
                }, f)
                
    # Lưu Checkpoint lần cuối khi xong vòng lặp
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump({
            "processed_files": processed_files,
            "groups": dict(groups),
            "rel_groups": dict(rel_groups)
        }, f)

    return groups, rel_groups

def build_final_nodes(groups):
    """
    Chuyển đổi sang định dạng danh sách để lưu trữ
    """
    logging.info("--- BẮT ĐẦU XUẤT FORMAT FINAL NODES ---")
    final_nodes = []
    for index, (name, info) in enumerate(groups.items()): 
        final_nodes.append({
            "id": index + 1,
            "entity_name": name,
            "entity_types": list(info["entity_types"]),
            "descriptions": list(info["descriptions"]),
            "source_chunks": list(info["source_chunks"]),
            "occurrence_count": info["occurrence_count"]
        })
    logging.info(f"Kết quả: {len(final_nodes)} thực thể duy nhất.")
    return final_nodes

def build_final_edges(rel_groups):
    """
    Chuyển đổi sang định dạng danh sách để lưu trữ
    """
    logging.info("--- BẮT ĐẦU XUẤT FORMAT FINAL EDGES ---")
    final_edges = []
    for index, ((src, tgt), info) in enumerate(rel_groups.items()):
        final_edges.append({
            "id": index + 1,
            "source": src,
            "target": tgt,
            "descriptions": list(info["descriptions"]),
            "weight": info["weight"],
            "source_chunks": list(info["source_chunks"])
        })
    logging.info(f"Kết quả: {len(final_edges)} quan hệ duy nhất.")
    return final_edges

def main():
    start_time = datetime.now()
    logging.info("=== KHỞI CHẠY STEP 2: EXACT MATCHING (GLOBAL AGGREGATION) ===")
    
    # 1. Đọc và gom nhóm song song
    groups, rel_groups = load_and_aggregate(INPUT_DIR)
    
    if not groups and not rel_groups:
        logging.error("Không tìm thấy dữ liệu để xuất file/Không thể khởi chạy!")
        return

    # 2. Xây dựng Nodes và Edges
    exact_nodes = build_final_nodes(groups)
    exact_edges = build_final_edges(rel_groups)
    
    nodes_output = os.path.join(OUTPUT_DIR, "exact_matched_nodes.json")
    edges_output = os.path.join(OUTPUT_DIR, "exact_matched_edges.json")
    
    with open(nodes_output, 'w', encoding='utf-8') as f:
        json.dump(exact_nodes, f, ensure_ascii=False, indent=4)
        
    with open(edges_output, 'w', encoding='utf-8') as f:
        json.dump(exact_edges, f, ensure_ascii=False, indent=4)
        
    duration = datetime.now() - start_time
    logging.info(f"=== HOÀN THÀNH GIAI ĐOẠN EXACT MATCHING TRONG {duration} ===")
    logging.info(f"File Nodes: {nodes_output}")
    logging.info(f"File Edges: {edges_output}")

if __name__ == "__main__":
    main()