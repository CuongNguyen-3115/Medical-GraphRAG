import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. Tải các biến môi trường từ file .env
load_dotenv()
api_key = os.getenv("SAMBANOVA_API_KEY")

if not api_key:
    print("❌ Lỗi: Không tìm thấy biến 'SAMBANOVA_API_KEY' trong file .env!")
    exit(1)

# 2. Khởi tạo Client bằng thư viện OpenAI nhưng trỏ về máy chủ SambaNova
client = OpenAI(
    base_url="https://api.sambanova.ai/v1",
    api_key=api_key
)

# Các mô hình phổ biến đang được SambaNova hỗ trợ miễn phí:
# - "Meta-Llama-3.1-8B-Instruct"
# - "Meta-Llama-3.1-70B-Instruct"
# - "Qwen2.5-72B-Instruct"
model_name =  "gpt-oss-120b"
print(f"🚀 Đang gửi yêu cầu tới model '{model_name}' trên SambaNova Cloud...")

try:
    # 3. Gửi request dạng Chat
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Bạn là một chuyên gia lập trình AI."},
            {"role": "user", "content": "Hãy tóm tắt ngắn gọn quy trình hoạt động của hệ thống RAG."}
        ],
        max_tokens=250,
        temperature=0.7
    )
    
    print("\n🎉 Kết nối THÀNH CÔNG!")
    print(f"🤖 Kết quả từ AI:\n{response.choices[0].message.content.strip()}")

except Exception as e:
    print("\n❌ Kết nối THẤT BẠI!")
    print(f"Chi tiết lỗi hệ thống:\n{e}")