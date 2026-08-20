import os
import json
import asyncio
import logging
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Cấu hình logger chi tiết để bắt lỗi doanh nghiệp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [GroqTester] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

async def test_groq_model_access():
    # Kích hoạt việc tìm và nạp cấu hình từ file .env vào bộ nhớ
    load_dotenv()
    
    # Lấy thông tin cấu hình từ môi trường của bạn
    api_key = os.getenv("GROQ_API_KEY_2")
    base_url = "https://api.groq.com/openai/v1/chat/completions"
    model = "meta-llama/llama-4-scout-17b-16e-instruct"

    logger.info("=" * 60)
    logger.info("🚀 KHỞI ĐỘNG HỆ THỐNG KIỂM TRA MÔ HÌNH VÀ ĐIỀU KIỆN API")
    logger.info("=" * 60)

    # 1. Kiểm tra sự tồn tại của API Key nội bộ
    if not api_key:
        logger.error("❌ LỖI ĐẦU VÀO: Biến môi trường 'GROQ_API_KEY_2' chưa được thiết lập!")
        logger.info("💡 HƯỚNG DẪN: Vui lòng chạy lệnh sau trên PowerShell trước khi thực thi script:")
        logger.info('   $env:GROQ_API_KEY_2="gsk_your_real_key_here"')
        logger.info("=" * 60)
        return

    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "Invalid Key Length"
    logger.info(f"[*] API Key ghi nhận: {masked_key}")
    logger.info(f"[*] Endpoint kết nối: {base_url}")
    logger.info(f"[*] Target Model ID:  {model}")
    logger.info("-" * 60)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Payload kiểm tra tối giản để không tốn nhiều token
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Ping. Trả về đúng 1 từ 'Pong' nếu nhận được."}
        ],
        "max_tokens": 5,
        "temperature": 0.0
    }

    logger.info("📡 Đang mở kết nối bất đồng bộ và đẩy gói tin sang Groq...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(base_url, headers=headers, json=payload, timeout=20) as response:
                status_code = response.status
                response_text = await response.text()
                
                # Giải mã JSON an toàn phục vụ phân tích sâu lý do lỗi
                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError:
                    response_json = {}

                logger.info(f"📬 Nhận phản hồi từ máy chủ Groq. Mã HTTP Status: {status_code}")
                logger.info("-" * 60)

                # PHÂN TÍCH VÀ PHÂN LOẠI LỖI DOANH NGHIỆP TRỰC DIỆN
                if status_code == 200:
                    logger.info("✅ THÀNH CÔNG RỰC RỠ! API Key hoàn toàn hợp lệ.")
                    logger.info(f"✅ Quyền truy cập mô hình '{model}' đã được xác thực.")
                    content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '')
                    logger.info(f"🤖 Phản hồi thô từ Llama-4: '{content.strip()}'")
                    logger.info("🎉 Hệ thống đã sẵn sàng 100% để chạy toàn bộ Core Engine của đồ án!")
                
                elif status_code == 401:
                    logger.error("❌ LỖI XÁC THỰC (HTTP 401 - Unauthorized): API Key nhập sai hoặc đã bị thu hồi!")
                    logger.error("🚨 Nguyên nhân: Chuỗi gsk_... của bạn không khớp với dữ liệu trên Groq Console.")
                    logger.error(f"💬 Chi tiết lỗi từ Groq: {response_text}")
                
                elif status_code == 403:
                    logger.error("❌ LỖI PHÂN QUYỀN (HTTP 403 - Forbidden): API Key đúng nhưng KHÔNG ĐƯỢC PHÉP dùng model này!")
                    logger.error(f"🚨 Nguyên nhân: Tài khoản Groq của bạn chưa nằm trong danh sách whitelist/bị giới hạn quyền đối với dòng mô hình thế hệ mới '{model}'.")
                    logger.error(f"💬 Chi tiết lỗi từ Groq: {response_text}")
                
                elif status_code == 404:
                    logger.error("❌ LỖI KHÔNG TÌM THẤY (HTTP 404 - Not Found): Sai Model ID!")
                    logger.error(f"🚨 Nguyên nhân: Chuỗi cấu hình '{model}' không tồn tại trong danh mục sản phẩm của Groq API.")
                    logger.error(f"💬 Chi tiết lỗi từ Groq: {response_text}")
                
                elif status_code == 429:
                    logger.error("❌ LỖI HẠN MỨC (HTTP 429 - Rate Limit / Insufficient Quota):")
                    error_info = response_json.get('error', {})
                    error_code = error_info.get('code', '')
                    
                    if error_code == 'insufficient_quota' or 'quota' in error_info.get('message', '').lower():
                        logger.error("🚨 NGUYÊN NHÂN CHÍ MẠNG: Tài khoản của bạn ĐÃ HẾT TIỀN hoặc HẾT HẠN MỨC SỬ DỤNG (Insufficient Quota)!")
                        logger.info("💡 KHẮC PHỤC: Hãy truy cập https://console.groq.com/playbook/billing để nạp tiền vào tài khoản.")
                    else:
                        logger.error("🚨 Nguyên nhân: Bạn đã spam vượt quá số lượng Request Per Minute (RPM) hoặc Tokens Per Minute (TPM) cho phép của tầng Free/Tier hiện tại.")
                    
                    logger.error(f"💬 Chi tiết lỗi từ Groq: {response_text}")
                
                elif status_code >= 500:
                    logger.error(f"❌ LỖI HỆ THỐNG PHÍA SERVER (HTTP {status_code}): Máy chủ Groq Cloud đang quá tải hoặc bảo trì cố định.")
                    logger.error(f"💬 Chi tiết lỗi từ Groq: {response_text}")
                
                else:
                    logger.error(f"❌ LỖI BẤT THƯỜNG CHƯA ĐƯỢC PHÂN LOẠI (HTTP {status_code}):")
                    logger.error(f"💬 Chi tiết lỗi từ Groq: {response_text}")

        except asyncio.TimeoutError:
            logger.error("❌ LỖI THỜI GIAN CHỜ (Timeout Error): Server Groq không phản hồi trong vòng 20 giây.")
            logger.error("👉 Khắc phục: Kiểm tra lại đường truyền Internet ổn định, ngắt các kết nối VPN hoặc Proxy chặn cổng quốc tế.")
        except aiohttp.ClientError as e:
            logger.error(f"❌ LỖI KẾT NỐI HẠ TẦNG MẠNG (ClientError): {e}")
            logger.error("👉 Khắc phục: Đường dẫn base_url bị sai hoặc DNS cục bộ của máy không thể phân giải tên miền api.groq.com.")
        except Exception as e:
            logger.error(f"❌ LỖI NGOẠI LỆ TRONG QUÁ TRÌNH THỰC THI SCRIPT: {e}")
            
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_groq_model_access())