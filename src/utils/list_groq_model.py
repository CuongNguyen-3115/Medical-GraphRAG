# import os
# from groq import Groq
# from dotenv import load_dotenv

# def list_groq_models():
#     # 1. Load API Key từ file .env
#     load_dotenv()
#     api_key = os.getenv("GROQ_API_KEY")

#     if not api_key:
#         print("Lỗi: Không tìm thấy GROQ_API_KEY trong file .env")
#         return

#     try:
#         # 2. Khởi tạo client Groq
#         client = Groq(api_key=api_key)

#         # 3. Lấy danh sách các model
#         models = client.models.list()

#         print(f"{'STT':<5} | {'Model ID':<30} | {'Owned By':<15} | {'Created'}")
#         print("-" * 75)

#         for i, model in enumerate(models.data, 1):
#             # Chuyển đổi timestamp sang định dạng ngày tháng dễ đọc
#             import datetime
#             created_date = datetime.datetime.fromtimestamp(model.created).strftime('%Y-%m-%d')
            
#             print(f"{i:<5} | {model.id:<30} | {model.owned_by:<15} | {created_date}")

#     except Exception as e:
#         print(f"Đã xảy ra lỗi khi kết nối với Groq API: {e}")

# if __name__ == "__main__":
#     list_groq_models()

import os
import time
from dotenv import load_dotenv
from groq import Groq

# Load biến môi trường từ file .env
load_dotenv(dotenv_path=r"C:\1. Project\ĐATN\.env")

def scan_all_models_rate_limits():
    api_key = os.getenv("GROQ_API_KEY_2")
    if not api_key:
        print("[!] Lỗi: Không tìm thấy GROQ_API_KEY")
        return

    client = Groq(api_key=api_key)
    print("[*] Đang kết nối Groq để lấy danh sách các models...\n")

    try:
        # 1. Lấy danh sách toàn bộ models có sẵn cho tài khoản của bạn
        models_page = client.models.list()
        model_ids = [m.id for m in models_page.data]
        
        # Sắp xếp theo tên cho dễ nhìn
        model_ids.sort()
        print(f"[+] Tìm thấy {len(model_ids)} models. Bắt đầu quá trình Ping test...\n")
    except Exception as e:
        print(f"[!] Lỗi khi lấy danh sách models: {e}")
        return

    # In Header của bảng
    print(f"{'MODEL ID':<35} | {'REQ LIMIT (Thường là RPD)':<25} | {'TOKEN LIMIT (Thường là TPM)':<25}")
    print("-" * 90)

    for model_id in model_ids:
        # Bỏ qua các model xử lý âm thanh (whisper) vì nó không chạy được trên endpoint chat.completions
        if "whisper" in model_id.lower():
            print(f"{model_id:<35} | {'[Bỏ qua - Model Âm thanh]':<25} | {'[Bỏ qua - Model Âm thanh]':<25}")
            continue

        try:
            # 2. Gửi một request siêu nhỏ (1 token) để lấy HTTP Headers
            raw_response = client.chat.completions.with_raw_response.create(
                model=model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )

            headers = raw_response.headers

            # 3. Trích xuất thông số
            req_limit = headers.get('x-ratelimit-limit-requests', 'N/A')
            tok_limit = headers.get('x-ratelimit-limit-tokens', 'N/A')

            print(f"{model_id:<35} | {req_limit:<25} | {tok_limit:<25}")

        except Exception as e:
            # Bắt lỗi nếu model đang bị bảo trì hoặc tài khoản không có quyền truy cập
            error_message = str(e).split('\n')[0][:30] + "..."
            print(f"{model_id:<35} | {f'[Lỗi: {error_message}]':<25} | {'-':<25}")

        # 4. Ngủ (sleep) 1.5 giây giữa các lượt ping để tránh bị Groq chặn vì spam request
        time.sleep(1.5)

    print("\n==================================================")
    print("Quá trình quét hoàn tất!")
    print("Mẹo: Nếu Reqiuest Limit = 14400, model đó thường cho phép 30 RPM và 14400 RPD.")
    print("     Nếu Request Limit = 1000, model đó thường bị siết rất chặt về RPD.")

if __name__ == "__main__":
    scan_all_models_rate_limits()