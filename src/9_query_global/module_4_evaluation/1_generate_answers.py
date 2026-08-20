# File chạy vòng lặp trả lời 102 câu hỏi
import os
import json
import asyncio
import logging
import sys

# Điều chỉnh sys.path để có thể import từ các module khác trong project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các thành phần của Engine (Từ thư mục module_2_engine)
from module_2_engine.state_manager import ContextPacker
from module_2_engine.llm_client import AsyncLLMClient, ServerError
from module_2_engine.map_phase import MapPhaseEngine
from module_2_engine.reduce_phase import ReducePhaseEngine

# Cấu hình log chuyên nghiệp cho quá trình sinh dữ liệu hàng loạt
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - [BatchGenerator] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ĐƯỜNG DẪN ---
# Đường dẫn đọc dữ liệu
# QUERIES_INPUT_PATH = r"C:\1. Project\ĐATN\Data\10_query\question_gen\medical_global_questions.jsonl"

QUERIES_INPUT_PATH = r"C:\1. Project\ĐATN\Data\10_query\retry_queries\failed_queries_retry.jsonl"

COMMUNITIES_INPUT_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"

# Đường dẫn ghi dữ liệu (Output)
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\11_evaluation\input"

# OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, "61_graphrag_results.jsonl")

OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, "20_retry_graphrag_results.jsonl")

# Ngoại lệ tùy chỉnh để bắt lỗi hết hạn mức ngày
class QuotaExhaustedError(Exception):
    pass

async def process_single_query(query_data: dict, chunks: list, llm_client: AsyncLLMClient) -> dict:
    """
    Thực thi pipeline GraphRAG cho một truy vấn duy nhất.
    Trả về Dictionary chứa {query, context (analyst reports), answer}.
    """
    query_text = query_data.get("question", "")
    logger.info(f"\n{'='*60}\nĐANG XỬ LÝ: {query_text[:80]}...\n{'='*60}")
    
    try:
        # --- PHA MAP ---
        map_engine = MapPhaseEngine(llm_client=llm_client)
        analyst_reports = await map_engine.execute(query_text, chunks)
        
        if not analyst_reports:
            logger.warning("Pha Map không thu được thông tin hữu ích nào.")
            return {
                "query": query_text,
                "context": [],
                "answer": "Hệ thống không tìm thấy dữ liệu phù hợp trong Graph để trả lời câu hỏi này."
            }

        # --- PHA REDUCE ---
        reduce_engine = ReducePhaseEngine(llm_client=llm_client)
        final_answer = await reduce_engine.execute(query_text, analyst_reports)
        
        # Đóng gói dữ liệu chuẩn bị lưu
        return {
            "query": query_text,
            "context": analyst_reports, # Lưu lại toàn bộ Analyst Reports làm Context cho RAGAS
            "answer": final_answer
        }
        
    except ServerError as e:
        # Bắt lỗi HTTP 429 hoặc các lỗi nghiêm trọng từ Server (đã được định nghĩa trong llm_client)
        error_msg = str(e).lower()
        if "insufficient_quota" in error_msg or "rate limit" in error_msg:
             logger.error("🚨 PHÁT HIỆN LỖI QUOTA MẠNG LƯỚI!")
             raise QuotaExhaustedError("Tài khoản đã cạn kiệt Quota ngày/tháng hoặc bị khóa Rate Limit vĩnh viễn.")
        else:
             logger.error(f"Lỗi Server cục bộ: {e}")
             return None
    except Exception as e:
        logger.error(f"Lỗi không mong muốn khi xử lý câu hỏi: {e}")
        return None

def load_processed_queries() -> set:
    """Đọc file Output (nếu có) để lấy danh sách các câu hỏi đã xử lý thành công (Save Progress)."""
    processed = set()
    if os.path.exists(OUTPUT_FILE_PATH):
        with open(OUTPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if "query" in data:
                        processed.add(data["query"])
                except json.JSONDecodeError:
                    continue
    return processed

async def main_batch_generation():
    # 1. Đảm bảo thư mục Output tồn tại
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 2. Đọc danh sách câu hỏi
    if not os.path.exists(QUERIES_INPUT_PATH):
        logger.error(f"Không tìm thấy file câu hỏi tại: {QUERIES_INPUT_PATH}")
        return
        
    all_queries = []
    with open(QUERIES_INPUT_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            all_queries.append(json.loads(line))
            
    # 3. Lọc bỏ các câu hỏi đã làm (Resume Capability)
    processed_queries = load_processed_queries()
    pending_queries = [q for q in all_queries if q.get("question") not in processed_queries]
    
    logger.info(f"Tổng số câu hỏi: {len(all_queries)}")
    logger.info(f"Đã xử lý trước đó: {len(processed_queries)}")
    logger.info(f"Cần xử lý trong phiên này: {len(pending_queries)}")
    
    if not pending_queries:
        logger.info("🎉 Toàn bộ dữ liệu đã được sinh xong. Không cần chạy thêm.")
        return

    # 4. Nạp dữ liệu Cộng đồng (Chỉ làm 1 lần để tiết kiệm I/O)
    logger.info("Đang nạp dữ liệu Cộng đồng vào bộ nhớ...")
    packer = ContextPacker(target_level=2, max_tokens_per_chunk=3500)
    packer.load_and_filter_data(COMMUNITIES_INPUT_PATH)
    chunks = packer.pack_context_chunks()
    
    if not chunks:
        logger.error("Không đóng gói được chunk nào. Dừng chương trình.")
        return

    # 5. Khởi tạo Client hạ tầng (Tự động nạp 3 API Keys từ .env)
    llm_client = AsyncLLMClient()
    
    # 6. Vòng lặp xử lý từng câu hỏi
    # Mở file với mode 'a' (append) để lưu ngay sau mỗi câu
    with open(OUTPUT_FILE_PATH, 'a', encoding='utf-8') as out_file:
        for index, query_data in enumerate(pending_queries):
            logger.info(f"Tiến độ phiên: {index + 1}/{len(pending_queries)}")
            
            try:
                result = await process_single_query(query_data, chunks, llm_client)
                
                if result:
                    # Lưu Progress ngay lập tức xuống đĩa cứng
                    out_file.write(json.dumps(result, ensure_ascii=False) + '\n')
                    out_file.flush() # Bắt buộc HĐH ghi file ngay, chống mất dữ liệu khi mất điện
                    logger.info("✅ Đã lưu kết quả thành công.")
                    
                    # Nghỉ 5 giây giữa các câu hỏi lớn để API Groq hạ nhiệt tổng thể
                    await asyncio.sleep(30)
                else:
                    logger.warning("Bỏ qua lưu do câu hỏi sinh ra lỗi.")
                    
            except QuotaExhaustedError as e:
                logger.error(f"🛑 DỪNG KHẨN CẤP: {e}")
                logger.error("Toàn bộ tiến trình đã được lưu an toàn. Hãy thay API Key mới và chạy lại script này.")
                break # Phá vỡ vòng lặp For, kết thúc script an toàn

if __name__ == "__main__":
    try:
        asyncio.run(main_batch_generation())
    except KeyboardInterrupt:
        logger.info("Người dùng chủ động dừng chương trình. Dữ liệu đã được lưu an toàn.")