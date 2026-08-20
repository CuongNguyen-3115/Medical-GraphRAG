import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def save_jsonl_checkpoint(data: List[Dict], filepath: str):
    """
    Ghi danh sách các dictionary (ví dụ: Analyst Reports) ra file .jsonl.
    Tự động tạo thư mục nếu chưa tồn tại.
    """
    # Lấy đường dẫn thư mục chứa file và tạo nếu chưa có
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
        
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                # Ghi từng object thành 1 dòng, không xuống dòng trong object
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info(f"Đã lưu Checkpoint thành công tại: {filepath}")
    except Exception as e:
        logger.error(f"Lỗi khi ghi Checkpoint: {e}")

def load_jsonl_checkpoint(filepath: str) -> List[Dict]:
    """
    Đọc dữ liệu từ file checkpoint .jsonl trở lại thành danh sách dictionary.
    """
    data = []
    if not os.path.exists(filepath):
        logger.warning(f"Không tìm thấy Checkpoint tại: {filepath}")
        return data
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        logger.info(f"Đã tải thành công {len(data)} bản ghi từ Checkpoint.")
    except Exception as e:
        logger.error(f"Lỗi khi đọc Checkpoint: {e}")
        
    return data