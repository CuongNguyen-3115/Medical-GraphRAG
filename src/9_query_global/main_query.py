# import os
# import asyncio
# import logging

# # Import các thành phần của Engine
# from module_2_engine.state_manager import ContextPacker
# from module_2_engine.llm_client import AsyncLLMClient
# from module_2_engine.map_phase import MapPhaseEngine
# from module_2_engine.reduce_phase import ReducePhaseEngine

# # Import tiện ích Checkpoint
# from utils.file_io import save_jsonl_checkpoint, load_jsonl_checkpoint

# # Cấu hình log
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)

# # --- CẤU HÌNH ĐƯỜNG DẪN ---
# INPUT_DATA_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"
# CHECKPOINT_PATH = r"C:\1. Project\ĐATN\Data\10_query\community_answers\temp_analyst_reports.jsonl"

# async def run_graphrag_pipeline(user_query: str, use_checkpoint: bool = True):
#     """
#     Luồng điều phối toàn bộ hệ thống GraphRAG.
#     """
#     logger.info("="*50)
#     logger.info(f"TIẾP NHẬN TRUY VẤN: '{user_query}'")
#     logger.info("="*50)

#     # Khởi tạo Client hạ tầng
#     # Lưu ý: Thiết lập biến môi trường LLM_API_KEY trước khi chạy
#     llm_client = AsyncLLMClient() 
    
#     analyst_reports = []

#     # --- KIỂM TRA CHECKPOINT ---
#     if use_checkpoint and os.path.exists(CHECKPOINT_PATH):
#         logger.info(f"[DEV MODE] Phát hiện file Checkpoint. Bỏ qua pha Map...")
#         analyst_reports = load_jsonl_checkpoint(CHECKPOINT_PATH)
    
#     # --- CHẠY PHA MAP (Nếu không có Checkpoint) ---
#     if not analyst_reports:
#         logger.info("Không dùng Checkpoint. Khởi động Pha Map...")
        
#         # 1. Nạp và đóng gói dữ liệu
#         packer = ContextPacker(target_level=2, max_tokens_per_chunk=3500)
#         packer.load_and_filter_data(INPUT_DATA_PATH)
#         chunks = packer.pack_context_chunks()
        
#         if not chunks:
#             logger.error("Không có chunk nào để xử lý. Dừng chương trình.")
#             return

#         # 2. Chạy Engine Map
#         map_engine = MapPhaseEngine(llm_client=llm_client)
#         analyst_reports = await map_engine.execute(user_query, chunks)
        
#         # 3. Ghi ra file Checkpoint ngay lập tức
#         if analyst_reports:
#             logger.info("Đang lưu kết quả Pha Map vào Checkpoint...")
#             save_jsonl_checkpoint(analyst_reports, CHECKPOINT_PATH)

#     # --- CHẠY PHA REDUCE ---
#     if analyst_reports:
#         logger.info("Khởi động Pha Reduce...")
#         reduce_engine = ReducePhaseEngine(llm_client=llm_client)
        
#         final_answer = await reduce_engine.execute(user_query, analyst_reports)
        
#         print("\n" + "★"*50)
#         print("🤖 AI DOCTOR'S FINAL ANSWER:")
#         print("★"*50)
#         print(final_answer)
#         print("★"*50 + "\n")

#         return final_answer
#     else:
#         logger.warning("Pipeline bị hủy vì không có Analyst Reports hợp lệ.")
#         return "Không thể khởi tạo báo cáo phân tích hợp lệ từ dữ liệu đồ thị."

# if __name__ == "__main__":
#     # Câu hỏi thử nghiệm
#     test_query = "Phân tích bức tranh toàn cảnh về hiệu quả của kháng sinh trong dự phòng nhiễm khuẩn"
    
#     # Chạy vòng lặp bất đồng bộ
#     asyncio.run(run_graphrag_pipeline(test_query, use_checkpoint=True))

import os
import asyncio
import logging

# Import các thành phần của Engine
from module_2_engine.state_manager import ContextPacker
from module_2_engine.llm_client import AsyncLLMClient
from module_2_engine.map_phase import MapPhaseEngine
from module_2_engine.reduce_phase import ReducePhaseEngine

# Import tiện ích Checkpoint
from utils.file_io import save_jsonl_checkpoint, load_jsonl_checkpoint

# Cấu hình log
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_DATA_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"
CHECKPOINT_PATH = r"C:\1. Project\ĐATN\Data\10_query\community_answers\temp_analyst_reports.jsonl"

async def run_graphrag_pipeline(user_query: str, use_checkpoint: bool = False):
    """
    Luồng điều phối toàn bộ hệ thống GraphRAG.
    Đã thiết lập mặc định use_checkpoint = False để luôn chạy Pha Map.
    """
    logger.info("="*50)
    logger.info(f"TIẾP NHẬN TRUY VẤN: '{user_query}'")
    logger.info("="*50)

    # Khởi tạo Client hạ tầng
    llm_client = AsyncLLMClient() 
    
    analyst_reports = []

    # --- ĐÃ TẮT KIỂM TRA CHECKPOINT THEO YÊU CẦU ---
    # Ép hệ thống luôn bỏ qua việc đọc file checkpoint cũ
    if False and os.path.exists(CHECKPOINT_PATH):
        pass 
    
    # --- CHẠY PHA MAP (Luôn thực thi) ---
    logger.info("Không dùng Checkpoint. Khởi động Pha Map...")
    
    # 1. Nạp và đóng gói dữ liệu
    packer = ContextPacker(target_level=2, max_tokens_per_chunk=3500)
    packer.load_and_filter_data(INPUT_DATA_PATH)
    chunks = packer.pack_context_chunks()
    
    if not chunks:
        logger.error("Không có chunk nào để xử lý. Dừng chương trình.")
        return "Xin lỗi, không có dữ liệu nào để phân tích."

    # 2. Chạy Engine Map
    map_engine = MapPhaseEngine(llm_client=llm_client)
    analyst_reports = await map_engine.execute(user_query, chunks)
    
    # 3. Ghi ra file Checkpoint ngay lập tức để sao lưu kết quả Map mới nhất
    if analyst_reports:
        logger.info("Đang lưu kết quả Pha Map mới nhất vào file sao lưu...")
        save_jsonl_checkpoint(analyst_reports, CHECKPOINT_PATH)

    # --- CHẠY PHA REDUCE ---
    if analyst_reports:
        logger.info("Khởi động Pha Reduce...")
        reduce_engine = ReducePhaseEngine(llm_client=llm_client)
        
        final_answer = await reduce_engine.execute(user_query, analyst_reports)
        
        print("\n" + "★"*50)
        print("🤖 AI DOCTOR'S FINAL ANSWER:")
        print("★"*50)
        print(final_answer)
        print("★"*50 + "\n")

        return final_answer
    else:
        logger.warning("Pipeline bị hủy vì không có Analyst Reports hợp lệ.")
        return "Không thể khởi tạo báo cáo phân tích hợp lệ từ dữ liệu đồ thị."

if __name__ == "__main__":
    test_query = "Phân tích bức tranh toàn cảnh về hiệu quả của kháng sinh trong dự phòng nhiễm khuẩn"
    asyncio.run(run_graphrag_pipeline(test_query, use_checkpoint=False))