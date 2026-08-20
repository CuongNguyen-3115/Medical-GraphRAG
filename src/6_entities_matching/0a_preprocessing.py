import os
import json
import re
import logging
import unicodedata
from datetime import datetime

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_DIR = r"C:\1. Project\ĐATN\Data\05_Entities"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\06_Entities_preprocessing"
ABBREVIATION_FILE = r"C:\1. Project\ĐATN\Data\1_abbreviations.json"
LOG_DIR = r"C:\1. Project\ĐATN\logs\7_preprocessing"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- THIẾT LẬP LOGGING ---
log_file = os.path.join(LOG_DIR, f"preprocessing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()])

# --- HÀM TIỀN XỬ LÝ ---

def load_abbreviations(filepath):
    """Đọc file viết tắt và sắp xếp theo độ dài giảm dần để tránh thay thế nhầm chuỗi con"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            abbrevs = json.load(f)
        # Sắp xếp key dài lên trước (VD: 'ĐTĐ' xử lý trước 'ĐT')
        sorted_abbrevs = dict(sorted(abbrevs.items(), key=lambda item: len(item[0]), reverse=True))
        logging.info(f"Đã tải {len(sorted_abbrevs)} từ viết tắt.")
        return sorted_abbrevs
    except Exception as e:
        logging.error(f"Lỗi đọc file abbreviations: {e}")
        return {}

def normalize_text(text, abbrevs_dict, is_entity_name=False):
    """Chuẩn hóa Unicode, xóa khoảng trắng thừa và thay thế từ viết tắt."""
    if not text: return ""
    
    # 1. Chuẩn hóa Unicode tiếng Việt (NFC)
    text = unicodedata.normalize('NFC', text)
    
    # 2. Xóa khoảng trắng thừa
    text = " ".join(text.split())
    
    # 3. Chuyển đổi từ viết tắt
    # Nếu là tên thực thể (is_entity_name = True), ưu tiên khớp chính xác toàn bộ tên
    if is_entity_name:
        # Ví dụ: Tên thực thể chỉ là "VMNM", đổi thẳng thành "VIÊM MÀNG NÃO MỦ"
        upper_text = text.upper()
        if upper_text in abbrevs_dict:
            text = abbrevs_dict[upper_text]
        else:
            # Nếu không khớp toàn bộ, thử thay thế ranh giới từ (word boundary)
            for short, long in abbrevs_dict.items():
                pattern = r'\b' + re.escape(short.upper()) + r'\b'
                text = re.sub(pattern, long.upper(), text, flags=re.IGNORECASE)
        # Tên thực thể luôn viết HOA để dễ Exact Match
        return text.upper()
    else:
        # Đối với Description, chỉ thay thế ranh giới từ và giữ nguyên Hoa/Thường
        for short, long in abbrevs_dict.items():
            pattern = r'\b' + re.escape(short) + r'\b'
            text = re.sub(pattern, long, text)
        return text

def parse_extraction_raw(raw_text, abbrevs_dict):
    """Dùng Regex để bóc tách raw_text thành 2 list: entities và relationships"""
    entities = []
    relationships = []
    
    logging.info("      -> [Debug] Bắt đầu tìm Entities qua Regex...")
    # Regex an toàn: Tìm nội dung bên trong ("entity" ... ) và không chứa ("entity" hay ("relationship" khác
    entity_blocks = re.finditer(r'\("entity"\s*<\|>\s*((?:(?!\("entity"|\("relationship").)*?)\)', raw_text, re.IGNORECASE | re.DOTALL)
    for match in entity_blocks:
        content = match.group(1)
        parts = re.split(r'\s*<\|>\s*', content)
        if len(parts) >= 3:
            name = normalize_text(parts[0], abbrevs_dict, is_entity_name=True)
            type_ = normalize_text(parts[1], {}, is_entity_name=True)
            desc = normalize_text(parts[2], abbrevs_dict, is_entity_name=False)
            entities.append({"name": name, "type": type_, "description": desc})

    logging.info(f"      -> [Debug] Tìm thấy {len(entities)} Entities. Bắt đầu tìm Relationships...")
    
    # Regex an toàn cho Relationships: Tìm nội dung bên trong ("relationship" ... )
    rel_blocks = re.finditer(r'\("relationship"\s*<\|>\s*((?:(?!\("entity"|\("relationship").)*?)\)', raw_text, re.IGNORECASE | re.DOTALL)
    for match in rel_blocks:
        content = match.group(1)
        parts = re.split(r'\s*<\|>\s*', content)
        if len(parts) >= 3:
            source = normalize_text(parts[0], abbrevs_dict, is_entity_name=True)
            target = normalize_text(parts[1], abbrevs_dict, is_entity_name=True)
            desc = normalize_text(parts[2], abbrevs_dict, is_entity_name=False)
            weight = 1
            if len(parts) >= 4:
                try:
                    # Loại bỏ các ký tự thừa nếu có trước khi parse int
                    w_str = re.sub(r'\D', '', parts[3]) 
                    weight = int(w_str) if w_str else 1
                except ValueError:
                    weight = 1
                    
            relationships.append({
                "source": source,
                "target": target,
                "description": desc,
                "weight": weight
            })
        
    logging.info(f"      -> [Debug] Hoàn tất Regex. Found {len(entities)} entities, {len(relationships)} relationships.")
    return entities, relationships

# --- CHƯƠNG TRÌNH CHÍNH ---

def main():
    logging.info("=== BẮT ĐẦU TIỀN XỬ LÝ (PREPROCESSING) CHUNKS ===")
    
    abbrevs_dict = load_abbreviations(ABBREVIATION_FILE)
    
    # Lấy danh sách các file đầu vào
    input_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    
    # CƠ CHẾ SAVE PROGRESS: Kiểm tra các file đã xử lý trong thư mục đích
    processed_files = set(os.listdir(OUTPUT_DIR))
    pending_files = [f for f in input_files if f not in processed_files]
    
    logging.info(f"Tổng số file cần xử lý: {len(pending_files)} / {len(input_files)}")
    
    if not pending_files:
        logging.info("Tất cả các file đã được tiền xử lý.")
        return

    # Giới hạn số lượng file để test
    # pending_files = pending_files[:2000]
    logging.info(f"Giới hạn xử lý {len(pending_files)} file để kiểm tra(test).")

    count = 0
    error_count = 0
    total_entities_fixed = 0
    total_relations_fixed = 0

    for filename in pending_files:
        logging.info(f"Đang bắt đầu xử lý file: {filename}")
        in_path = os.path.join(INPUT_DIR, filename)
        out_path = os.path.join(OUTPUT_DIR, filename)
        
        try:
            with open(in_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            raw_text = data.get("extraction_raw", "")
            
            # Thực hiện Parsing và Chuẩn hóa
            parsed_entities, parsed_relationships = parse_extraction_raw(raw_text, abbrevs_dict)
            
            file_entities_fixed = 0
            file_relations_fixed = 0

            # --- Logic thay thế ký tự "_" bằng khoảng trắng (từ step1_preprocessing_2.py) ---
            for entity in parsed_entities:
                if 'name' in entity and isinstance(entity['name'], str):
                    old_name = entity['name']
                    new_name = old_name.replace('_', ' ').strip()
                    if old_name != new_name:
                        entity['name'] = new_name
                        file_entities_fixed += 1
                    
            for rel in parsed_relationships:
                if 'source' in rel and isinstance(rel['source'], str):
                    old_src = rel['source']
                    new_src = old_src.replace('_', ' ').strip()
                    if old_src != new_src:
                        rel['source'] = new_src
                        file_relations_fixed += 1

                if 'target' in rel and isinstance(rel['target'], str):
                    old_tgt = rel['target']
                    new_tgt = old_tgt.replace('_', ' ').strip()
                    if old_tgt != new_tgt:
                        rel['target'] = new_tgt
                        file_relations_fixed += 1
            # -----------------------------------------------------------------------------
            
            total_entities_fixed += file_entities_fixed
            total_relations_fixed += file_relations_fixed

            # Tạo data cấu trúc mới (Xóa bỏ extraction_raw thô)
            processed_data = {
                "chunk_id": data.get("chunk_id"),
                "metadata": data.get("metadata"),
                "parsed_entities": parsed_entities,
                "parsed_relationships": parsed_relationships,
                "models_used": data.get("models_used"),
                "extraction_timestamp": data.get("extraction_timestamp")
            }
            
            # Lưu file
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=4)
                
            count += 1
            logging.info(f"[OK] {filename} | Sửa {file_entities_fixed} entities, {file_relations_fixed} relations.")
            
            if count % 50 == 0:
                logging.info(f"Đã xử lý {count}/{len(pending_files)} file...")
                
        except Exception as e:
            logging.error(f"[ERROR] Lỗi xử lý file {filename}: {e}")
            error_count += 1
            
    logging.info("-" * 50)
    logging.info(f"TỔNG KẾT:")
    logging.info(f"- Số file xử lý thành công: {count}/{len(pending_files)}")
    logging.info(f"- Số file bị lỗi: {error_count}")
    logging.info(f"- Tổng số entities đã được chuẩn hóa (bỏ dấu _): {total_entities_fixed}")
    logging.info(f"- Tổng số nguồn/đích trong relations đã được chuẩn hóa (bỏ dấu _): {total_relations_fixed}")
    logging.info(f"=== HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH TIỀN XỬ LÝ ===")

if __name__ == "__main__":
    main()