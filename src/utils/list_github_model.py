# import os
# import requests
# from dotenv import load_dotenv

# # --- CẤU HÌNH ---
# ENV_PATH = r"C:\1. Project\ĐATN\.env"
# load_dotenv(ENV_PATH)

# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# def get_github_models():
#     if not GITHUB_TOKEN:
#         print("❌ Không tìm thấy GITHUB_TOKEN trong file .env")
#         return

#     # Endpoint danh sách model của GitHub
#     url = "https://models.inference.ai.azure.com/models"
    
#     headers = {
#         "Authorization": f"Bearer {GITHUB_TOKEN}",
#         "Content-Type": "application/json"
#     }

#     try:
#         response = requests.get(url, headers=headers)
        
#         if response.status_code == 200:
#             models = response.json()
#             print(f"✅ Tìm thấy {len(models)} model khả dụng cho tài khoản của bạn:\n")
#             print(f"{'STT':<5} | {'Tên Model (ID để điền vào .env)':<40} | {'Nhà phát triển':<15}")
#             print("-" * 70)
            
#             for idx, model in enumerate(models, 1):
#                 name = model.get("name", "N/A")
#                 publisher = model.get("publisher", "N/A")
#                 print(f"{idx:<5} | {name:<40} | {publisher:<15}")
                
#             print("\n💡 Hãy copy chính xác tên ở cột giữa vào file .env của bạn.")
#         else:
#             print(f"❌ Lỗi truy vấn: {response.status_code}")
#             print(response.text)
            
#     except Exception as e:
#         print(f"❌ Có lỗi xảy ra: {e}")

# if __name__ == "__main__":
#     get_github_models()

import os
import requests
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv(dotenv_path=r"C:\1. Project\ĐATN\.env")

# Lấy GitHub Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("[!] Không tìm thấy GITHUB_TOKEN trong file .env")

def estimate_github_rate_limits(model_name: str) -> dict:
    """Ước lượng Rate Limit cho GitHub Models (Tài khoản Free/Pro)"""
    name = model_name.lower()
    
    if "gpt-4" in name or "o1" in name or "70b" in name or "405b" in name or "command-r-plus" in name:
        return {"RPM": 10, "RPD": 50, "TPM": "4,000", "TPD": "N/A"}
    elif "8b" in name or "phi-3" in name or "mistral" in name or "gpt-4o-mini" in name or "jamba" in name:
        return {"RPM": 15, "RPD": 150, "TPM": "8,000", "TPD": "N/A"}
    elif "embedding" in name:
        return {"RPM": 15, "RPD": 150, "TPM": "8,000", "TPD": "N/A"}
    else:
        return {"RPM": 10, "RPD": 50, "TPM": "4,000", "TPD": "N/A"}

def list_github_models():
    print("[*] Đang kết nối GitHub Models API (Direct HTTP) để lấy danh sách...\n")
    
    url = "https://models.inference.ai.azure.com/models"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Gọi trực tiếp qua HTTP thay vì dùng wrapper của OpenAI
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Bắt lỗi nếu Token sai hoặc bị chặn
        
        raw_data = response.json()
        
        # Xử lý linh hoạt: Đón đầu cả trường hợp GitHub trả về List hoặc Dict
        if isinstance(raw_data, list):
            models = [m.get("id", m.get("name")) for m in raw_data]
        else:
            models = [m.get("id", m.get("name")) for m in raw_data.get("data", [])]
            
        # Lọc các giá trị rỗng và sắp xếp theo bảng chữ cái
        models = sorted(list(set(filter(None, models))))
        
        print(f"{'MODEL ID':<35} | {'RPM':<5} | {'RPD':<6} | {'TPM (Tokens/Phút)'}")
        print("-" * 70)
        
        count = 0
        for name in models:
            limits = estimate_github_rate_limits(name)
            print(f"{name:<35} | {str(limits['RPM']):<5} | {str(limits['RPD']):<6} | {str(limits['TPM']):<15}")
            count += 1
            
        print("-" * 70)
        print(f"[+] Tìm thấy {count} models trên GitHub Azure AI.")
        print("\n* Lưu ý: Hạn mức trên là ước lượng cho tài khoản GitHub cá nhân (Free/Pro).")
        
    except Exception as e:
        print(f"[!] Lỗi khi lấy danh sách model: {e}")

if __name__ == "__main__":
    list_github_models()