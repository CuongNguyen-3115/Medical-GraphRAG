import os
import requests
from dotenv import load_dotenv

# --- CẤU HÌNH ---
ENV_PATH = r"C:\1. Project\ĐATN\.env"
load_dotenv(ENV_PATH)

HF_TOKEN = os.getenv("HF_TOKEN")

def get_best_hf_models(limit=30):
    if not HF_TOKEN:
        print("❌ Không tìm thấy HF_TOKEN trong file .env")
        return

    # API của Hugging Face để lấy danh sách model
    url = "https://huggingface.co/api/models"
    
    # Các tham số lọc: 
    # - filter: text-generation (để dùng được cho chat/extraction)
    # - inference: warm (các model đang sẵn sàng trên serverless)
    # - sort: downloads (độ phổ biến cao = ổn định hơn)
    params = {
        "filter": "text-generation",
        "inference": "warm",
        "sort": "downloads",
        "direction": -1,
        "limit": limit
    }
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Tìm thấy {len(models)} model 'chiến thần' đang sẵn sàng trên HF:\n")
            print(f"{'STT':<5} | {'Model ID (Copy vào .env)':<45} | {'Lượt tải'}")
            print("-" * 75)
            
            for idx, model in enumerate(models, 1):
                model_id = model.get("modelId", "N/A")
                downloads = model.get("downloads", 0)
                print(f"{idx:<5} | {model_id:<45} | {downloads:,}")
                
            print("\n💡 Lưu ý: Hãy ưu tiên chọn các model có chữ '-Instruct' hoặc '-it' (Instruction Tuned)")
            print("để đảm bảo khả năng trích xuất thực thể tốt nhất.")
        else:
            print(f"❌ Lỗi: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    get_best_hf_models(limit=40)