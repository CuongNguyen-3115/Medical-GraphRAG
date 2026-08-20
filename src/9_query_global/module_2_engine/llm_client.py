import os
import json
import logging
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# 1. KÍCH HOẠT ĐỌC FILE .ENV TỰ ĐỘNG
ROOT_DIR = Path(__file__).resolve().parents[3] 
env_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Lỗi tùy chỉnh khi vượt quá hạn mức API (HTTP 429)."""
    pass

class ServerError(Exception):
    """Lỗi tùy chỉnh khi hệ thống server LLM gặp sự cố (HTTP 5xx)."""
    pass

class AsyncLLMClient:
    """
    Client hạ tầng (Infrastructure Layer) giao tiếp HTTP bất đồng bộ.
    Tích hợp thuật toán Round-Robin Load Balancing đa API Key để mở rộng Quota.
    """
    def __init__(self, base_url: str = None):
        # Nạp toàn bộ danh sách API Keys từ .env
        raw_keys = [
            os.getenv("GEMINI_API_KEY_1"),
            os.getenv("GEMINI_API_KEY_2")
        ]
        
        # Lọc bỏ các giá trị None hoặc rỗng
        self.api_keys = [key for key in raw_keys if key and key.strip()]
        
        if not self.api_keys:
            logger.error("🚨 NGHIÊM TRỌNG: Không tìm thấy bất kỳ API Key nào trong file .env!")
            raise ValueError("Missing API Keys")

        logger.info(f"[*] Load Balancer Khởi động: Đã nạp thành công {len(self.api_keys)} API Keys độc lập.")

        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        # self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.model = 'gemini-2.5-flash-lite'

        # Con trỏ Round-Robin
        self.current_key_index = 0
        
        # Mở rộng luồng song song: 2 request/1 key -> Có 3 keys thì được chạy 6 luồng cùng lúc
        max_concurrent = len(self.api_keys) * 2
        self.semaphore = asyncio.Semaphore(max_concurrent)

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((RateLimitError, ServerError, asyncio.TimeoutError, aiohttp.ClientError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Lỗi gọi API: {retry_state.outcome.exception()}. Đang xoay vòng Key và thử lại lần {retry_state.attempt_number}..."
        )
    )
    async def post_request(self, session: aiohttp.ClientSession, payload: dict) -> dict:
        """Gửi request POST bất đồng bộ tới API LLM bằng thuật toán Round-Robin."""
        
        # 1. Lấy Key hiện tại và Dịch chuyển con trỏ sang Key tiếp theo (Round-Robin)
        current_key = self.api_keys[self.current_key_index]
        used_index = self.current_key_index # Lưu lại index để in log nếu cần
        
        # Toán tử Modulo (%) giúp con trỏ quay về 0 khi vượt quá số lượng Key (0 -> 1 -> 2 -> 0)
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        headers = {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json"
        }
        
        # Kích hoạt lớp bảo vệ kiểm soát luồng
        async with self.semaphore:
            async with session.post(self.base_url, headers=headers, json=payload, timeout=90) as response:
                
                # Xử lý các mã trạng thái lỗi HTTP đặc thù
                if response.status == 429:
                    raise RateLimitError(f"Hệ thống LLM báo quá tải hạn mức tại Key index {used_index} (HTTP 429).")
                elif response.status >= 500:
                    raise ServerError(f"Lỗi Server (HTTP {response.status}).")
                elif response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Lỗi cấu hình tại Key index {used_index}: HTTP {response.status} - {error_text}")
                
                return await response.json()