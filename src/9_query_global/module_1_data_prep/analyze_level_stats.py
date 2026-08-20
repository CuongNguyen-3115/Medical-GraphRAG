import json
import logging
from collections import defaultdict

# Cấu hình Logging tối giản để in report
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)

INPUT_JSONL_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"

def analyze_levels():
    # Sử dụng defaultdict để tự động khởi tạo dict chứa count và tokens cho mỗi level mới
    level_stats = defaultdict(lambda: {'count': 0, 'total_tokens': 0})
    total_communities = 0
    total_tokens_all = 0
    
    logger.info(f"Đang phân tích cấu trúc Level từ: {INPUT_JSONL_PATH}...\n")
    
    try:
        with open(INPUT_JSONL_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                
                # Lấy level và token_count, mặc định là -1 và 0 nếu thiếu
                lvl = data.get('level', -1)
                tokens = data.get('token_count', 0)
                
                level_stats[lvl]['count'] += 1
                level_stats[lvl]['total_tokens'] += tokens
                total_communities += 1
                total_tokens_all += tokens
                
    except Exception as e:
        logger.error(f"Lỗi khi đọc file: {e}")
        return

    if total_communities == 0:
        logger.warning("Không có dữ liệu để thống kê.")
        return

    # --- IN BÁO CÁO (REPORT) ---
    logger.info("="*70)
    logger.info(" BÁO CÁO THỐNG KÊ THEO TẦNG CỘNG ĐỒNG (HIERARCHICAL LEVELS)")
    logger.info("="*70)
    
    # Sắp xếp các level tăng dần (Level 0, 1, 2...). Đưa level -1 (lỗi/thiếu) xuống cuối.
    sorted_levels = sorted(level_stats.keys(), key=lambda x: float('inf') if x == -1 else x)
    
    # Header bảng
    logger.info(f" {'Level':<10} | {'Số lượng Cộng đồng':<20} | {'Tổng Tokens':<15} | {'Trung bình Token/Cộng đồng':<25}")
    logger.info("-" * 70)
    
    for lvl in sorted_levels:
        stats = level_stats[lvl]
        count = stats['count']
        tokens = stats['total_tokens']
        avg_tokens = tokens / count if count > 0 else 0
        
        # Format tên level để hiển thị đẹp hơn
        lvl_name = f"Level {lvl}" if lvl != -1 else "Chưa gán (-1)"
        
        # Tính phần trăm
        pct_count = (count / total_communities) * 100
        pct_tokens = (tokens / total_tokens_all) * 100
        
        logger.info(f" {lvl_name:<10} | {count:>5} ({pct_count:>5.1f}%)         | {tokens:>10,} ({pct_tokens:>4.1f}%) | {avg_tokens:>8.0f} tokens")

    logger.info("="*70)
    logger.info(f" TỔNG CỘNG  | {total_communities:>5} communities        | {total_tokens_all:>10,} tokens |")
    logger.info("="*70)

    # --- GỢI Ý CHIẾN LƯỢC TỰ ĐỘNG ---
    logger.info("\n[GỢI Ý CHIẾN LƯỢC TỪ HỆ THỐNG]")
    logger.info("- Hãy nhìn vào cột 'Tổng Tokens'.")
    logger.info("- Quota API Llama-4-scout của bạn: 30K Tokens/Min | 500K Tokens/Day.")
    for lvl in sorted_levels:
        if lvl == -1: continue
        tokens = level_stats[lvl]['total_tokens']
        
        # FIX LOGIC: Tạo lại tên hiển thị cho từng vòng lặp
        current_lvl_name = f"Level {lvl}" 
        
        if tokens < 500000:
            logger.info(f"   -> {current_lvl_name}: Rất TỐT. Chạy Map toàn bộ Level này tốn dưới 1 ngày quota.")
        else:
            days = tokens / 500000
            logger.info(f"   -> {current_lvl_name}: CẢNH BÁO. Chạy Map toàn bộ Level này tốn {days:.1f} ngày quota.")

if __name__ == "__main__":
    analyze_levels()