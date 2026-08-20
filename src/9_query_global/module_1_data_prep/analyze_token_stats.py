import json
import logging
import statistics
from collections import Counter

# Cấu hình Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"  # Format tối giản để in report cho đẹp
)
logger = logging.getLogger(__name__)

INPUT_JSONL_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"

def analyze_tokens():
    token_counts = []
    
    logger.info(f"Đang đọc dữ liệu từ: {INPUT_JSONL_PATH}...")
    
    try:
        with open(INPUT_JSONL_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if 'token_count' in data:
                    token_counts.append(data['token_count'])
    except Exception as e:
        logger.error(f"Lỗi khi đọc file: {e}")
        return

    if not token_counts:
        logger.warning("Không tìm thấy dữ liệu token_count trong file.")
        return

    # --- TÍNH TOÁN CÁC CHỈ SỐ THỐNG KÊ ---
    total_communities = len(token_counts)
    total_tokens = sum(token_counts)
    max_tokens = max(token_counts)
    min_tokens = min(token_counts)
    mean_tokens = statistics.mean(token_counts)
    median_tokens = statistics.median(token_counts)
    
    # --- PHÂN LOẠI THEO DẢI (BINS) ---
    # Phân dải để phục vụ cho thuật toán Packing
    bins = {
        "0 - 250": 0,
        "251 - 500": 0,
        "501 - 1000": 0,
        "1001 - 2000": 0,
        "> 2000": 0
    }
    
    for count in token_counts:
        if count <= 250:
            bins["0 - 250"] += 1
        elif count <= 500:
            bins["251 - 500"] += 1
        elif count <= 1000:
            bins["501 - 1000"] += 1
        elif count <= 2000:
            bins["1001 - 2000"] += 1
        else:
            bins["> 2000"] += 1

    # --- IN BÁO CÁO (REPORT) ---
    logger.info("\n" + "="*50)
    logger.info(" BÁO CÁO THỐNG KÊ TOKEN_COUNT (PHẦN MAP)")
    logger.info("="*50)
    logger.info(f"Tổng số cộng đồng (Chunks) : {total_communities:,}")
    logger.info(f"Tổng số Token dự kiến      : {total_tokens:,} tokens")
    logger.info("-" * 50)
    logger.info(f"Lớn nhất (Max)             : {max_tokens:,} tokens")
    logger.info(f"Nhỏ nhất (Min)             : {min_tokens:,} tokens")
    logger.info(f"Trung bình (Mean)          : {mean_tokens:.2f} tokens")
    logger.info(f"Trung vị (Median)          : {median_tokens:.2f} tokens")
    logger.info("-" * 50)
    logger.info("PHÂN BỐ CÁC DẢI TOKEN (DISTRIBUTION):")
    
    # Vẽ biểu đồ ASCII đơn giản
    max_bar_length = 30
    max_bin_value = max(bins.values()) if bins.values() else 1
    
    for bin_name, count in bins.items():
        percentage = (count / total_communities) * 100
        # Tính toán độ dài thanh biểu đồ
        bar_length = int((count / max_bin_value) * max_bar_length)
        bar = "█" * bar_length
        logger.info(f" {bin_name:<12} | {count:>5} ({percentage:>5.1f}%) | {bar}")
        
    logger.info("="*50)
    
    # --- ĐÁNH GIÁ NHANH CHI PHÍ THEO QUOTA ---
    quota_tpd = 500000 # 500K Tokens per Day
    days_required = total_tokens / quota_tpd
    logger.info("\n[ĐÁNH GIÁ QUOTA TỰ ĐỘNG]")
    logger.info(f"- Quota của bạn: 500,000 Tokens/Day.")
    if days_required <= 1:
        logger.info("- Tuyệt vời! Bạn có thể xử lý toàn bộ tập dữ liệu này trong MỘT NGÀY.")
    else:
        logger.info(f"- CẢNH BÁO: Với tổng {total_tokens:,} tokens, bạn sẽ cần ít nhất {days_required:.1f} ngày để chạy hết quá trình Map.")

if __name__ == "__main__":
    analyze_tokens()