import os
from google import genai
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv(dotenv_path=r"C:\1. Project\ĐATN\.env")

# Lấy API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_1")
if not GEMINI_API_KEY:
    raise ValueError("[!] Không tìm thấy GEMINI_API_KEY trong file .env")

# Khởi tạo Client theo chuẩn SDK mới (google-genai)
client = genai.Client(api_key=GEMINI_API_KEY)

def estimate_rate_limits(model_name: str) -> dict:
    """
    Hàm ước lượng Rate Limit cho Free Tier dựa trên phân khúc model.
    Thay vì tra từ điển cứng, hệ thống tự động phân loại bằng từ khóa.
    """
    name = model_name.lower()
    # Dòng Pro, Research và các bản siêu cấp thường bị giới hạn rất chặt (2 RPM)
    if "pro" in name or "research" in name or "antigravity" in name or "robotics" in name:
        return {"RPM": 2, "RPD": 50, "TPM": "32,000", "TPD": "Không giới hạn"}
    # Dòng Flash, Lite, Gemma được thiết kế để xử lý nhanh và nhiều (15 RPM)
    elif "flash" in name or "lite" in name or "gemma" in name or "nano" in name:
        return {"RPM": 15, "RPD": 1500, "TPM": "1 triệu", "TPD": "Không giới hạn"}
    else:
        # Mặc định an toàn cho các model chưa phân loại
        return {"RPM": 2, "RPD": 50, "TPM": "32,000", "TPD": "Không giới hạn"}

def list_gemini_models():
    print("[*] Đang kết nối Gemini API (SDK mới) để lấy danh sách models...\n")
    
    try:
        # Cú pháp mới để lấy danh sách model
        models = client.models.list()
        
        # Định dạng bảng rộng hơn để chứa tên model dài
        print(f"{'MODEL ID':<35} | {'RPM':<5} | {'RPD':<6} | {'TPM (Tokens/Phút)':<15} | {'TPD'}")
        print("-" * 85)
        
        count = 0
        for m in models:
            name = m.name
            
            # Cắt bỏ tiền tố "models/" nếu API trả về kèm theo để nhìn gọn hơn
            short_name = name.replace("models/", "")
            
            # Ước lượng giới hạn theo thuật toán phân loại
            limits = estimate_rate_limits(short_name)
            
            print(f"{short_name:<35} | {str(limits['RPM']):<5} | {str(limits['RPD']):<6} | {str(limits['TPM']):<15} | {str(limits['TPD'])}")
            count += 1
            
        print("-" * 85)
        print(f"[+] Tìm thấy {count} models.")
        print("\n* Lưu ý: Các thông số trên áp dụng cho hạng Free Tier (Ước lượng).")
        
    except Exception as e:
        print(f"[!] Lỗi khi lấy danh sách model: {e}")

if __name__ == "__main__":
    list_gemini_models()