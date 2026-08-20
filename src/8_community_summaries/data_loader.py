import json
from pathlib import Path
from typing import List, Dict, Tuple
from config import INPUT_COMMUNITIES_PATH

def load_and_filter_communities(file_path: Path = INPUT_COMMUNITIES_PATH) -> Tuple[List[Dict], List[Dict]]:
    """
    Đọc dữ liệu communities từ file JSON (thường là file đã được lọc).
    Trả về dạng process_list và một skip_list rỗng (để giữ tương thích kiến trúc cũ).
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

    # File này đã được lọc sẵn ở Pipeline thứ 7
    return communities, []