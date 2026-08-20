import json
from pathlib import Path
from typing import List, Dict, Tuple

# Cấu hình đường dẫn
BASE_DIR = Path(r"C:\1. Project\ĐATN")
DATA_DIR = BASE_DIR / "Data"
INPUT_COMMUNITIES_PATH = DATA_DIR / "08_Communities_detecting" / "communities.json"

# Ngưỡng cắt tỉa (Pruning thresholds)
MIN_NODES_MICRO_LEVEL = 4  # Ngưỡng số node tối thiểu cho Level 0 và 1

def filter_communities(file_path: Path = INPUT_COMMUNITIES_PATH) -> Tuple[List[Dict], List[Dict]]:
    """
    Đọc dữ liệu communities từ file JSON và phân loại lọc bớt các cộng đồng quá nhỏ.
    Các cộng đồng còn lại sẽ được lưu vào thư mục 09_Communities_4_summaries.
    """
    print(f"[*] Đang đọc dữ liệu từ: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            communities = json.load(f)
    except FileNotFoundError:
        print(f"[!] Lỗi: Không tìm thấy file {file_path}")
        return [], []
    except json.JSONDecodeError:
        print(f"[!] Lỗi: File {file_path} không đúng định dạng JSON")
        return [], []

    process_list = []
    skip_list = []

    for comm in communities:
        # Trích xuất thông tin
        level = comm.get("level", 0) 
        nodes = comm.get("nodes", [])
        node_count = len(nodes)
        
        # Phân loại: Skip các cộng đồng ở bất kỳ Level nào (0-4) nếu có ít hơn MIN_NODES_MICRO_LEVEL nodes
        if level in [0, 1, 2, 3, 4] and node_count < MIN_NODES_MICRO_LEVEL:
            skip_list.append(comm)
        else:
            process_list.append(comm)

    # Lấy danh sách các ID cộng đồng hợp lệ
    valid_community_ids = {comm.get("community_id") for comm in process_list if "community_id" in comm}

    # Cập nhật lại trường sub_communities, loại bỏ các cộng đồng đã bị filter
    for comm in process_list:
        if "sub_communities" in comm and comm["sub_communities"]:
            comm["sub_communities"] = [
                sub_id for sub_id in comm["sub_communities"] 
                if sub_id in valid_community_ids
            ]

    # Lưu file các cộng đồng đã lọc vào thư mục mới
    output_filtered_dir = DATA_DIR / "08_Communities_detecting"
    output_filtered_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_filtered_dir / "filtered_communities_hehe.json"
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(process_list, f, ensure_ascii=False, indent=4)
        
    print(f"[*] Đã lọc bỏ {len(skip_list)} cộng đồng siêu nhỏ (các Level và < {MIN_NODES_MICRO_LEVEL} nodes).")
    print(f"[*] LƯU THÀNH CÔNG {len(process_list)} cộng đồng cần xử lý vào: {out_file}\n")

    return process_list, skip_list

if __name__ == "__main__":
    filter_communities()
