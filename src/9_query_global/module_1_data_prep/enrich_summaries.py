# Script đọc file JSONL cũ, tính toán token_count, map level, và xuất ra summaries_checkpoint_enriched.jsonl
import json
import logging
from pathlib import Path
from tqdm import tqdm
from transformers import AutoTokenizer

# Cấu hình Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Khai báo đường dẫn tĩnh (Hardcoded paths theo project)
FILTERED_COMMUNITIES_PATH = r"C:\1. Project\ĐATN\Data\08_Communities_detecting\filtered_communities.json"
INPUT_JSONL_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_checkpoint.jsonl"
OUTPUT_JSONL_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"

# Lựa chọn model tokenizer (Dùng tokenizer của Llama-3 8B Instruct làm chuẩn cho họ Llama)
TOKENIZER_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

def load_level_mapping(json_path: str) -> dict:
    """Đọc file JSON và tạo Hash Map ánh xạ từ community_id -> level"""
    logger.info(f"Đang tải mapping từ: {json_path}")
    mapping = {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                # Đảm bảo ép kiểu int cho ID để đồng nhất khi so sánh
                mapping[int(item['community_id'])] = item['level']
        logger.info(f"Đã tải thành công {len(mapping)} keys vào Hash Map.")
        return mapping
    except Exception as e:
        logger.error(f"Lỗi khi đọc file filtered_communities.json: {e}")
        raise

def simulate_context_string(community_data: dict) -> str:
    """Giả lập chuỗi văn bản Markdown sẽ gửi cho LLM để đếm token chuẩn xác nhất"""
    title = community_data.get('title', '')
    summary = community_data.get('summary', '')
    findings = community_data.get('findings', [])
    
    context = f"# {title}\n**Tóm tắt:** {summary}\n**Phát hiện chính:**\n"
    for finding in findings:
        f_summary = finding.get('summary', '')
        f_exp = finding.get('explanation', '')
        context += f"- {f_summary}: {f_exp}\n"
        
    return context

def process_and_enrich_data():
    # 1. Tải Tokenizer
    logger.info(f"Đang khởi tạo Tokenizer từ model: {TOKENIZER_MODEL}...")
    try:
        # Nếu bị lỗi mạng hoặc thiếu token HuggingFace, có thể đổi sang các bộ tokenizer nhẹ hơn
        tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)
    except Exception as e:
        logger.warning(f"Không thể tải Llama Tokenizer ({e}). Đang chuyển sang xài GPT2 Tokenizer mặc định để ước lượng nhanh...")
        from transformers import GPT2TokenizerFast
        tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

    # 2. Tải Level Mapping
    level_map = load_level_mapping(FILTERED_COMMUNITIES_PATH)

    # 3. Đọc JSONL, xử lý và ghi ra file mới
    logger.info("Bắt đầu xử lý file summaries_checkpoint.jsonl...")
    
    missing_level_count = 0
    processed_count = 0

    with open(INPUT_JSONL_PATH, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_JSONL_PATH, 'w', encoding='utf-8') as outfile:
        
        # Đọc toàn bộ lines để đếm tổng số (hỗ trợ hiển thị thanh tiến trình)
        lines = infile.readlines()
        
        for line in tqdm(lines, desc="Enriching Summaries", unit=" community"):
            if not line.strip():
                continue
                
            data = json.loads(line)
            comm_id = int(data['community_id'])
            
            # --- Ánh xạ Level ---
            if comm_id in level_map:
                data['level'] = level_map[comm_id]
            else:
                data['level'] = -1 # Gán giá trị mặc định nếu ID bị khuyết
                missing_level_count += 1
                
            # --- Tính toán Token Count ---
            simulated_text = simulate_context_string(data)
            # Tokenize văn bản và đếm số lượng (không tạo tensor)
            tokens = tokenizer.encode(simulated_text, add_special_tokens=False)
            data['token_count'] = len(tokens)
            
            # --- Ghi ra file mới ---
            # dump đảm bảo format chuẩn jsonl không bị ngắt dòng
            outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
            processed_count += 1

    logger.info("=== KẾT QUẢ XỬ LÝ ===")
    logger.info(f"Tổng số community đã xử lý: {processed_count}")
    logger.info(f"Số community không tìm thấy level: {missing_level_count}")
    logger.info(f"File đầu ra đã lưu tại: {OUTPUT_JSONL_PATH}")

if __name__ == "__main__":
    process_and_enrich_data()