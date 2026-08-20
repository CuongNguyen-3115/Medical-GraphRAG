import asyncio
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv() 

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import Client và Prompt
import sys
sys.path.append(str(Path(__file__).resolve().parents[1])) 
from module_2_engine.llm_client import AsyncLLMClient 

from knm_templates import PERSONA_SYSTEM_PROMPT, TASK_SYSTEM_PROMPT, QUESTION_SYSTEM_PROMPT

# Cấu hình Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)
class RateLimitError(Exception):
    """Lỗi tùy chỉnh khi vượt quá hạn mức API (HTTP 429)."""
    pass

class ServerError(Exception):
    """Lỗi tùy chỉnh khi hệ thống server LLM gặp sự cố (HTTP 5xx)."""
    pass

# Cấu hình siêu tham số
K_PERSONAS = 2
N_TASKS = 2
M_QUESTIONS = 2

# Đường dẫn file
INPUT_FILE = r"C:\1. Project\ĐATN\Data\10_query\eval_samples\sampled_communities.jsonl"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\10_query\question_gen"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "medical_global_questions.jsonl")

GLOBAL_DOMAIN_CONTEXT = """
HỆ QUẢN TRỊ TRI THỨC Y KHOA (MEDICAL KNOWLEDGE GRAPH):
Đây là một hệ thống Đồ thị Tri thức y khoa phức hợp, được tổng hợp từ hàng ngàn báo cáo lâm sàng và y văn. 
Hệ thống không giới hạn ở một chuyên khoa cụ thể, mà kết nối đa chiều các thực thể y tế (Bệnh lý, Thuốc, Cấu trúc giải phẫu, Phương pháp điều trị).
Mục tiêu cốt lõi của dữ liệu là làm nổi bật các "Mối quan hệ" (Relationships) nguyên nhân - kết quả, cảnh báo rủi ro lâm sàng, và các xu hướng điều trị tổng thể.
"""

class FormatError(Exception):
    pass

@retry(
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((RateLimitError, ServerError, asyncio.TimeoutError, aiohttp.ClientError)),
        before_sleep=lambda retry_state: logger.warning(
            # ĐÃ CẬP NHẬT: In ra lý do lỗi thực sự để dễ Debug
            f"Lỗi gọi API: {retry_state.outcome.exception()}. Đang thử lại lần {retry_state.attempt_number}..."
        )
    )

async def safe_generate_json(llm_client: AsyncLLMClient, session: aiohttp.ClientSession, prompt: str, expected_key: str) -> dict:
    """Gọi LLM, ép định dạng JSON và kiểm tra key bắt buộc."""
    payload = {
        "model": "llama-3.3-70b-versatile", # Override model cụ thể cho pha này
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "response_format": {"type": "json_object"}
    }
    
    response_data = await llm_client.post_request(session, payload)
    raw_content = response_data['choices'][0]['message']['content']
    
    parsed_json = json.loads(raw_content)
    if expected_key not in parsed_json:
        raise FormatError(f"Thiếu key '{expected_key}' trong JSON trả về.")
        
    return parsed_json

async def process_community(llm_client: AsyncLLMClient, session: aiohttp.ClientSession, community: dict) -> list:
    """Luồng K-N-M cho một cộng đồng cụ thể."""
    comm_id = community.get('community_id')
    comm_summary = community.get('summary', '')
    
    # Kết hợp Macro và Micro Context
    combined_corpus_summary = f"{GLOBAL_DOMAIN_CONTEXT}\n\n--- CHI TIẾT CỘNG ĐỒNG SỐ {comm_id} ---\n{comm_summary}"
    
    final_questions = []
    
    try:
        # Bước 1: Sinh Personas
        logger.info(f"[{comm_id}] Đang sinh {K_PERSONAS} Personas...")
        p_prompt = PERSONA_SYSTEM_PROMPT.format(corpus_summary=combined_corpus_summary)
        p_data = await safe_generate_json(llm_client, session, p_prompt, "personas")
        
        # Cắt đúng K Personas đề phòng LLM sinh thừa
        personas = p_data["personas"][:K_PERSONAS] 
        
        for p in personas:
            role = p.get("role", "Unknown Role")
            desc = p.get("description", "")
            
            # Tránh Rate Limit: Dừng 2 giây giữa các call liên tiếp
            await asyncio.sleep(2) 
            
            # Bước 2: Sinh Tasks
            logger.info(f"[{comm_id}]  -> Đang sinh {N_TASKS} Tasks cho: {role}")
            t_prompt = TASK_SYSTEM_PROMPT.format(
                corpus_summary=combined_corpus_summary,
                role=role,
                description=desc
            )
            t_data = await safe_generate_json(llm_client, session, t_prompt, "tasks")
            tasks = t_data["tasks"][:N_TASKS]
            
            for t in tasks:
                task_name = t.get("task_name", "")
                task_desc = t.get("task_description", "")
                
                await asyncio.sleep(2)
                
                # Bước 3: Sinh Questions
                logger.info(f"[{comm_id}]    => Đang sinh {M_QUESTIONS} Questions cho Task: {task_name}")
                q_prompt = QUESTION_SYSTEM_PROMPT.format(
                    corpus_summary=combined_corpus_summary,
                    role=role,
                    task_name=task_name,
                    task_description=task_desc
                )
                q_data = await safe_generate_json(llm_client, session, q_prompt, "questions")
                questions = q_data["questions"][:M_QUESTIONS]
                
                # Đóng gói kết quả cuối cùng
                for q in questions:
                    final_questions.append({
                        "community_id": comm_id,
                        "persona_role": role,
                        "task_name": task_name,
                        "question": q.get("question", ""),
                        "expected_complexity": q.get("expected_complexity", "")
                    })
                    
    except Exception as e:
        logger.error(f"Lỗi không thể phục hồi tại Community {comm_id}: {e}")
        
    return final_questions

async def main():
    logger.info("Khởi động hệ thống sinh Global Benchmark Questions...")
    
    # 1. Khởi tạo
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    llm_client = AsyncLLMClient()
    
    # 2. Đọc dữ liệu đã lấy mẫu
    sampled_communities = []
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    sampled_communities.append(json.loads(line))
    else:
        logger.error(f"Không tìm thấy file: {INPUT_FILE}. Vui lòng chạy sample_data.py trước.")
        return

    logger.info(f"Đã tải {len(sampled_communities)} communities để xử lý.")
    
    all_benchmark_questions = []

    # 3. Xử lý TUẦN TỰ từng cộng đồng để chống chạm đỉnh 6K TPM
    async with aiohttp.ClientSession() as session:
        for community in sampled_communities:
            questions = await process_community(llm_client, session, community)
            all_benchmark_questions.extend(questions)
            
            # Nghỉ ngơi giữa các cộng đồng để xả quota
            logger.info("Nghỉ 5 giây để làm mát API Quota...")
            await asyncio.sleep(5)
            
    # 4. Ghi kết quả
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for q in all_benchmark_questions:
            f.write(json.dumps(q, ensure_ascii=False) + '\n')
            
    logger.info("="*50)
    logger.info(f"[+] Đã tạo thành công {len(all_benchmark_questions)} câu hỏi Global Sensemaking.")
    logger.info(f"[+] File được lưu tại: {OUTPUT_FILE}")
    logger.info("="*50)

if __name__ == "__main__":
    asyncio.run(main())