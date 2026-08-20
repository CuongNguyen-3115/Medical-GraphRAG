# sắp xếp điểm giảm dần, nhồi vào context và gọi LLM tổng hợp.
import logging
import aiohttp
from typing import List, Dict

# Import các module trong cùng package
from .llm_client import AsyncLLMClient
from .prompt_templates import REDUCE_SYSTEM_PROMPT, NO_DATA_ANSWER

logger = logging.getLogger(__name__)

class ReducePhaseEngine:
    """
    Controller chính cho pha Reduce (Tổng hợp toàn cục).
    Chịu trách nhiệm sắp xếp các báo cáo, gộp ngữ cảnh và gọi LLM lần cuối.
    """
    def __init__(self, llm_client: AsyncLLMClient, max_context_tokens: int = 6000):
        self.llm_client = llm_client
        self.system_prompt_template = REDUCE_SYSTEM_PROMPT
        self.no_data_answer = NO_DATA_ANSWER
        
        # Giới hạn token cho pha Reduce (Chừa lại ~2000 tokens cho output của LLM)
        self.max_context_tokens = max_context_tokens
        # Heuristic: 1 token Llama thường tương đương khoảng 3.5 - 4 ký tự tiếng Việt
        self.char_limit = self.max_context_tokens * 3.5 

    def _sort_and_flatten_reports(self, analyst_reports: List[Dict]) -> List[Dict]:
        """
        Làm phẳng danh sách các báo cáo và sắp xếp giảm dần theo Helpfulness Score.
        """
        all_points = []
        for report in analyst_reports:
            for pt in report.get("points", []):
                # Đảm bảo format chuẩn trước khi đưa vào list
                if "description" in pt and "score" in pt:
                    all_points.append(pt)
                    
        # Sắp xếp giảm dần (Descending) theo điểm 'score'
        all_points.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_points

    def _build_report_context(self, sorted_points: List[Dict]) -> str:
        """
        Gộp các ý tưởng lại thành một chuỗi văn bản duy nhất.
        Dừng gộp nếu chạm ngưỡng an toàn của Context Window.
        """
        context_string = ""
        current_length = 0
        included_points = 0
        
        for idx, pt in enumerate(sorted_points):
            # Format: [Điểm: 85] Mô tả chi tiết...
            point_text = f"--- Ý quan trọng {idx + 1} (Điểm: {pt['score']}) ---\n{pt['description']}\n\n"
            
            # Kiểm tra xem nếu cộng thêm chuỗi này có vượt quá giới hạn token không
            if current_length + len(point_text) > self.char_limit:
                logger.warning(f"Đã đạt giới hạn Context Window. Bỏ qua {len(sorted_points) - included_points} ý kém quan trọng hơn.")
                break
                
            context_string += point_text
            current_length += len(point_text)
            included_points += 1
            
        logger.info(f"Đã gộp {included_points}/{len(sorted_points)} ý tưởng vào Context (Độ dài: {current_length} ký tự).")
        return context_string

    async def execute(self, user_query: str, analyst_reports: List[Dict], response_type: str = "Một bài phân tích y khoa chi tiết gồm nhiều đoạn văn") -> str:
        """
        Hàm thực thi chính của pha Reduce. Trả về chuỗi Markdown cuối cùng.
        """
        logger.info("Bắt đầu thực thi Reduce Phase...")
        
        # 1. Kiểm tra dữ liệu đầu vào (Trường hợp Map Phase không tìm thấy gì)
        if not analyst_reports:
            logger.warning("Không có Analyst Reports nào hợp lệ. Trả về câu trả lời mặc định.")
            return self.no_data_answer

        # 2. Sắp xếp và Gộp Context
        sorted_points = self._sort_and_flatten_reports(analyst_reports)
        if not sorted_points:
            return self.no_data_answer
            
        report_data_str = self._build_report_context(sorted_points)

        # 3. Định dạng System Prompt
        formatted_system_prompt = self.system_prompt_template.format(
            response_type=response_type,
            report_data=report_data_str,
            no_data_answer=self.no_data_answer
        )

        # 4. Chuẩn bị Payload
        # Pha này không yêu cầu trả về JSON, ta muốn text Markdown thuần túy
        payload = {
            "model": self.llm_client.model,
            "messages": [
                {"role": "system", "content": formatted_system_prompt},
                # Nhắc lại câu hỏi của User để LLM không bị lạc đề
                {"role": "user", "content": f"Câu hỏi của tôi là: {user_query}"}
            ],
            "temperature": 0.3, # Tăng nhẹ temperature (0.3) so với Map (0.1) để hành văn mượt mà hơn
        }

        # 5. Gọi LLM
        async with aiohttp.ClientSession() as session:
            try:
                logger.info("Đang gửi Context tới LLM để tổng hợp (Reduce)...")
                # Truyền chunk_id = 0 vì đây là request tổng
                response_data = await self.llm_client.post_request(session, payload)
                
                final_markdown = response_data['choices'][0]['message']['content']
                logger.info("Hoàn thành Reduce Phase xuất sắc!")
                return final_markdown
                
            except Exception as e:
                logger.error(f"Lỗi nghiêm trọng trong pha Reduce: {e}")
                return "Đã xảy ra lỗi hệ thống trong quá trình tổng hợp câu trả lời. Vui lòng thử lại sau."