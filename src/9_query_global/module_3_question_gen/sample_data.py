import os
import json
import random
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Cấu hình đường dẫn
INPUT_FILE = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\10_query\eval_samples"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sampled_communities.jsonl")

# Cấu hình tham số Sampling
SAMPLE_SIZES = {
    2: 10,  # Lấy 10 communities ở Level 2
    3: 5    # Lấy 5 communities ở Level 3
}

def sample_communities():
    # 1. Khởi tạo kho chứa
    communities_by_level = {2: [], 3: []}
    
    logger.info(f"Đang đọc dữ liệu từ: {INPUT_FILE}")
    
    # 2. Đọc và phân loại dữ liệu theo Level
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                lvl = data.get('level')
                
                if lvl in communities_by_level:
                    communities_by_level[lvl].append(data)
    except FileNotFoundError:
        logger.error("Không tìm thấy file đầu vào. Vui lòng kiểm tra lại đường dẫn.")
        return

    # 3. Lấy mẫu ngẫu nhiên (Random Sampling)
    random.seed(42) # Cố định seed để nếu chạy lại vẫn ra đúng các bài này
    sampled_data = []
    
    for lvl, required_size in SAMPLE_SIZES.items():
        available = len(communities_by_level[lvl])
        logger.info(f"Level {lvl}: Có sẵn {available} communities.")
        
        # Lấy số lượng nhỏ hơn giữa yêu cầu và thực tế có sẵn
        actual_sample_size = min(required_size, available)
        
        if actual_sample_size > 0:
            sampled_items = random.sample(communities_by_level[lvl], actual_sample_size)
            sampled_data.extend(sampled_items)
            logger.info(f"--> Đã lấy mẫu ngẫu nhiên {actual_sample_size} communities từ Level {lvl}.")

    # 4. Ghi ra file JSONL mới
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for item in sampled_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        logger.info("\n" + "="*50)
        logger.info(f"THÀNH CÔNG! Đã lưu {len(sampled_data)} mẫu vào:\n{OUTPUT_FILE}")
        logger.info("="*50)
    except Exception as e:
        logger.error(f"Lỗi khi ghi file: {e}")

if __name__ == "__main__":
    sample_communities()