import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

# 1. Load môi trường
env_path = Path(r"C:\1. Project\2. DoAn_GraphRAG\.env")
load_dotenv(dotenv_path=env_path)

def list_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Không tìm thấy GEMINI_API_KEY trong file .env")
        return

    # Khởi tạo client
    client = genai.Client(api_key=api_key)

    print("🚀 Đang truy vấn danh sách model từ Google AI Studio...")
    print(f"{'STT':<5} | {'Model ID':<40}")
    print("-" * 50)

    try:
        # Lấy danh sách model
        # Trong SDK mới, chúng ta iterate trực tiếp qua client.models.list()
        index = 1
        for model in client.models.list():
            # In ra ID của model (đây là cái bạn cần điền vào biến môi trường)
            print(f"{index:<5} | {model.name:<40}")
            index += 1
                
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách model: {e}")
        print("\nGợi ý: Thử kiểm tra lại quyền hạn của API Key trên Google AI Studio.")

if __name__ == "__main__":
    list_gemini_models()