import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("CEREBRAS_API_KEY")

client = OpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key=api_key
)

# BẮT BUỘC SỬ DỤNG model có trong bảng Limits của bạn
model_name = "zai-glm-4.7"

print(f"🚀 Đang gửi yêu cầu tới model '{model_name}' trên máy chủ Cerebras...")

try:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Bạn là một trợ lý AI hữu ích."},
            {"role": "user", "content": "RAG trong AI là viết tắt của từ gì?"}
        ],
        max_tokens=300,
        temperature=0.2
    )
    
    print("\n🎉 Kết nối THÀNH CÔNG!")
    
    content = response.choices[0].message.content
    if content:
        print(f"🤖 Kết quả từ AI:\n{content.strip()}")
    else:
        print(f"⚠️ Cảnh báo: Model xử lý thành công nhưng trả về nội dung rỗng.")

except Exception as e:
    print("\n❌ Kết nối THẤT BẠI!")
    print(f"Chi tiết lỗi hệ thống:\n{e}")
    if "429" in str(e):
        print("💡 Gợi ý: Hạn mức của bạn là 5 requests/phút. Hãy đợi khoảng 15-30 giây rồi chạy lại file nhé!")