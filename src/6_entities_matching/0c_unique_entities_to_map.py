import os
import json

NODES_FILE = r"C:\1. Project\ĐATN\Data\07_Entities_matching\exact_matched_nodes.json"
EDGES_FILE = r"C:\1. Project\ĐATN\Data\07_Entities_matching\exact_matched_edges.json"
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\unique_entities_to_map.json"

def extract_unique_names():
    unique_names = set()
    
    # Lấy name từ Nodes
    print(f"Đang quét thực thể từ file {NODES_FILE}...")
    try:
        with open(NODES_FILE, 'r', encoding='utf-8') as f:
            nodes_data = json.load(f)
            for node in nodes_data:
                if node.get("entity_name"):
                    unique_names.add(node["entity_name"].strip().upper())
    except FileNotFoundError:
        print(f"[CẢNH BÁO] Không tìm thấy file {NODES_FILE}")

    # Lấy source và target từ Edges
    print(f"Đang quét thực thể từ file {EDGES_FILE}...")
    try:
        with open(EDGES_FILE, 'r', encoding='utf-8') as f:
            edges_data = json.load(f)
            for edge in edges_data:
                if edge.get("source"):
                    unique_names.add(edge["source"].strip().upper())
                if edge.get("target"):
                    unique_names.add(edge["target"].strip().upper())
    except FileNotFoundError:
        print(f"[CẢNH BÁO] Không tìm thấy file {EDGES_FILE}")
                    
    # Sắp xếp alphabet cho dễ nhìn
    sorted_names = sorted(list(unique_names))
    
    # Đảm bảo thư mục lưu tồn tại
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted_names, f, ensure_ascii=False, indent=4)
        
    print(f"Đã trích xuất {len(sorted_names)} thực thể duy nhất. Lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_unique_names()