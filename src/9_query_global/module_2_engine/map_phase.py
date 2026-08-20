# Lọc điểm 0, Chạy async đa luồng, chấm điểm Helpfulness, trả về Analyst Reports.
import asyncio
import logging
import json
from typing import List, Dict

# Import các module trong cùng package
from .llm_client import AsyncLLMClient
from .prompt_templates import MAP_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class MapPhaseEngine:
    """
    Controller chính cho pha Map. 
    Chịu trách nhiệm ghép prompt, điều phối gọi LLM theo cơ chế Batching Delay 
    để bảo vệ Quota API và hậu xử lý kết quả (lọc điểm).
    """
    def __init__(self, llm_client: AsyncLLMClient):
        self.llm_client = llm_client
        self.system_prompt = MAP_SYSTEM_PROMPT

    def _build_user_prompt(self, user_query: str, chunk_content: str) -> str:
        """Ghép câu hỏi của user và dữ liệu chunk thành một User Prompt hoàn chỉnh."""
        return f"---USER QUERY---\n{user_query}\n\n---DATA CONTEXT---\n{chunk_content}"

    async def _process_single_chunk(self, session, chunk_id: int, payload: dict) -> dict:
        """
        Hàm bọc (Wrapper) xử lý riêng biệt cho từng chunk.
        Gọi API hạ tầng một cách an toàn và tự đóng gói cấu trúc dữ liệu trả về.
        """
        try:
            # Gọi API hạ tầng - Chỉ truyền đúng 2 tham số vị trí theo đúng thiết kế của llm_client
            response_data = await self.llm_client.post_request(session, payload)
            
            # Trích xuất nội dung văn bản từ phản hồi gốc
            raw_content = response_data['choices'][0]['message']['content']
            
            # Khử các ký tự nhiễu markdown nếu mô hình tự ý in thêm
            clean_content = raw_content.strip().lstrip("```json").rstrip("```").strip()
            result_json = json.loads(clean_content)
            
            return {
                "chunk_id": chunk_id,
                "analyst_report": result_json
            }
        except Exception as e:
            logger.error(f"[-] Thất bại khi xử lý sinh dữ liệu tại Chunk {chunk_id}. Chi tiết: {e}")
            # Trả về cấu trúc rỗng để hệ thống tự động loại bỏ ở tầng nghiệp vụ lọc điểm mà không làm sập luồng
            return {
                "chunk_id": chunk_id,
                "analyst_report": {"points": []}
            }

    def _filter_and_format_results(self, raw_results: List[Dict]) -> List[Dict]:
        """
        Logic nghiệp vụ: Lọc bỏ các point có điểm = 0 (Nhiễu/Không liên quan).
        Làm phẳng (flatten) kết quả để trả về danh sách các báo cáo tinh gọn.
        """
        valid_analyst_reports = []
        total_points_generated = 0
        valid_points_retained = 0

        for result in raw_results:
            if not result:
                continue
            chunk_id = result.get("chunk_id")
            report_data = result.get("analyst_report", {})
            
            points = report_data.get("points", [])
            if not isinstance(points, list):
                continue

            valid_points_for_chunk = []
            for pt in points:
                total_points_generated += 1
                score = pt.get("score", 0)
                
                # Chỉ giữ lại những point có điểm số hữu ích thực sự (> 0)
                if isinstance(score, (int, float)) and score > 0:
                    valid_points_for_chunk.append(pt)
                    valid_points_retained += 1

            # Nếu chunk này chắt lọc được ít nhất 1 thông tin hữu ích, đóng gói thành Analyst Report
            if valid_points_for_chunk:
                valid_analyst_reports.append({
                    "chunk_id": chunk_id,
                    "points": valid_points_for_chunk,
                    "max_score": max(int(pt.get("score", 0)) for pt in valid_points_for_chunk)
                })

        logger.info(f"[+] Hậu xử lý hoàn tất: Tạo ra {total_points_generated} ý tưởng, chắt lọc được {valid_points_retained} ý tưởng hữu ích (>0 điểm).")
        return valid_analyst_reports

    async def execute(self, user_query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Hàm thực thi điều phối chính của pha Map áp dụng kỹ thuật Pacing Batch.
        """
        logger.info(f"[*] Khởi động luồng Map Phase: Tổng cộng {len(chunks)} chunks.")
        
        successful_results = []
        
        # Cấu hình siêu tham số Batching điều tốc để bảo vệ 30K TPM của Groq
        # BATCH_SIZE = 3      # Mỗi đợt chỉ đẩy 3 chunks (~10.5K tokens), rất an toàn
        # DELAY_SECONDS = 25   # Thời gian nghỉ xả tải giữa các đợt để hạ nhiệt rolling token window

        BATCH_SIZE = 6      # Xử lý 12 chunks một đợt (~42.000 tokens) 
        DELAY_SECONDS = 5    # Chỉ cần nghỉ 5 giây để API kịp xả tải
        
        total_chunks = len(chunks)
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Vòng lặp phân đoạn dữ liệu đầu vào
            for i in range(0, total_chunks, BATCH_SIZE):
                batch_chunks = chunks[i:i + BATCH_SIZE]
                current_batch_num = (i // BATCH_SIZE) + 1
                total_batches = (total_chunks - 1) // BATCH_SIZE + 1
                
                logger.info(f"====> Đang xử lý Phân đoạn (Batch) {current_batch_num}/{total_batches} (Gồm {len(batch_chunks)} chunks song song)...")
                
                tasks = []
                for chunk in batch_chunks:
                    user_prompt = self._build_user_prompt(user_query, chunk['content'])
                    
                    payload = {
                        "model": self.llm_client.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                    
                    # Tạo task bất đồng bộ thông qua hàm bọc an toàn
                    task = asyncio.create_task(
                        self._process_single_chunk(session, chunk['chunk_id'], payload)
                    )
                    tasks.append(task)
                
                # Thực thi song song các tác vụ trong phạm vi phân đoạn hiện tại
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Gom kết quả sạch
                for res in batch_results:
                    if isinstance(res, Exception):
                        logger.error(f"[-] Lỗi nghiêm trọng xuất hiện trong phân đoạn: {res}")
                    else:
                        successful_results.append(res)
                
                # Cơ chế trì hoãn thông minh: Nghỉ ngơi nếu chưa phải là phân đoạn cuối cùng
                if i + BATCH_SIZE < total_chunks:
                    logger.info(f"[*] Hoàn thành phân đoạn {current_batch_num}. Hệ thống tạm nghỉ {DELAY_SECONDS} giây để giải phóng hạn mức API (TPM)...")
                    await asyncio.sleep(DELAY_SECONDS)

        # Tiến hành lọc nhiễu điểm số
        final_reports = self._filter_and_format_results(successful_results)
        logger.info(f"[+] Kết thúc Map Phase thành công. Thu được {len(final_reports)} Analyst Reports chất lượng cao.")
        return final_reports