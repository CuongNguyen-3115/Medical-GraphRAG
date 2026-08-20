import os
import json
import time
import re
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load file .env
load_dotenv()

# --- CẤU HÌNH ---
INPUT_FILE = r"C:\1. Project\ĐATN\Data\2_unique_entities_to_map.json"
OUTPUT_FILE = r"C:\1. Project\ĐATN\Data\3_medical_aliases.json"
PROGRESS_FILE = r"C:\1. Project\ĐATN\Data\3_alias_progress.json"
CHUNK_SIZE = 100 # Số lượng thực thể gửi đi trong 1 prompt (Tăng giảm tùy ý)

class ModelCycler:
    """Quản lý xoay vòng các model (Cycle Model) từ các Provider khác nhau"""
    def __init__(self):
        self.models = []
        self._load_models_from_env()
        self.current_idx = 0
        logging.info(f"Đã tải thành công {len(self.models)} models vào hệ thống xoay vòng.")

    def _load_models_from_env(self):
        # 1. Load Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            for i in range(1, 6):
                model_id = os.getenv(f"MODEL_ID_{i}")
                if model_id:
                    self.models.append({"provider": "gemini", "model": model_id, "key": gemini_key})
        
        # 2. Load Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            for i in range(1, 8):
                model_id = os.getenv(f"GROQ_MODEL_ID_{i}")
                if model_id:
                    self.models.append({"provider": "groq", "model": model_id, "key": groq_key})
                    
        # 3. Load Hugging Face
        hf_key = os.getenv("HF_TOKEN")
        if hf_key:
            for i in range(1, 6):
                model_id = os.getenv(f"HF_MODEL_ID_{i}")
                if model_id:
                    self.models.append({"provider": "hf", "model": model_id, "key": hf_key})

    def get_current_model(self):
        return self.models[self.current_idx]

    def next_model(self):
        old_model = self.models[self.current_idx]['model']
        self.current_idx = (self.current_idx + 1) % len(self.models)
        new_model = self.models[self.current_idx]['model']
        logging.warning(f"Chuyển đổi model: {old_model} -> {new_model}")

def call_llm_api(system_prompt: str, user_prompt: str, cycler: ModelCycler) -> str:
    """Gọi API và tự động Retry/Next Model nếu gặp lỗi"""
    max_retries = len(cycler.models) # Thử tối đa một vòng các model
    
    for attempt in range(max_retries):
        current = cycler.get_current_model()
        provider = current["provider"]
        model = current["model"]
        api_key = current["key"]
        
        try:
            logging.info(f"Đang gọi: [{provider.upper()}] {model}...")
            
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.1} # Nhiệt độ thấp để kết quả ổn định
                }
                response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
                response.raise_for_status()
                return response.json()['candidates'][0]['content']['parts'][0]['text']
                
            elif provider in ["groq", "hf"]:
                # Cả Groq và HF đều hỗ trợ chuẩn API tương tự OpenAI
                if provider == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                else: # hf
                    url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1
                }
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']

        except Exception as e:
            logging.error(f"Lỗi với {model}: {str(e)}")
            # Nếu là lỗi Rate Limit (429) hoặc Model Overloaded (503), lập tức đổi model
            cycler.next_model()
            time.sleep(2) # Nghỉ 2s trước khi gọi model mới
            
    raise Exception("Đã thử tất cả các model nhưng đều thất bại!")

def extract_json_from_response(text: str) -> dict:
    """Trích xuất chuỗi JSON từ phản hồi của LLM (Bỏ qua các markdown code block)"""
    try:
        # Tìm nội dung nằm giữa { và }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return {}
    except json.JSONDecodeError:
        logging.error(f"Không thể parse JSON từ phản hồi: {text[:100]}...")
        return {}

def main():
    # 1. Khởi tạo
    cycler = ModelCycler()
    if not cycler.models:
        logging.error("Không tìm thấy cấu hình API keys trong file .env")
        return

    # 2. Load danh sách thực thể đầu vào
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            all_entities = json.load(f)
    except FileNotFoundError:
        logging.error(f"Không tìm thấy {INPUT_FILE}")
        return

    # 3. Load Progress (Checkpoint)
    progress_data = {}
    processed_count = 0
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
            # Tính toán số lượng đã xử lý dựa trên danh sách value
            processed_count = sum(len(v) for v in progress_data.values())
        logging.info(f"Đã khôi phục tiến trình: {processed_count} thực thể đã được xử lý.")

    # 4. Tách các thực thể chưa được xử lý
    # Giả định: Nếu thực thể đã tồn tại trong progress_data (ở phần value), bỏ qua
    processed_entities = set()
    for aliases in progress_data.values():
        processed_entities.update(aliases)
    
    remaining_entities = [e for e in all_entities if e not in processed_entities]
    logging.info(f"Số lượng thực thể cần xử lý tiếp: {len(remaining_entities)} / {len(all_entities)}")

    system_prompt = """Bạn là một Kỹ sư Dữ liệu Y tế (Healthcare Data Engineer) và Chuyên gia NLP. 
Nhiệm vụ của bạn là chuẩn hóa danh sách các thực thể y khoa thô thành một file từ điển ánh xạ (Alias Dictionary) định dạng JSON.

CHỈ THỊ CỐT LÕI:
Chỉ gom nhóm dựa trên LỖI CÚ PHÁP, CÁCH VIẾT TẮT, và TỪ ĐỒNG NGHĨA Y KHOA. Tuyệt đối KHÔNG suy diễn mối liên hệ ngữ cảnh.

CÁC QUY TẮC CHUẨN HÓA BẮT BUỘC (Tuân thủ 100%):
1. CHUẨN HÓA DẤU GẠCH NGANG: Phải xóa toàn bộ khoảng trắng xung quanh dấu "-".
   - VD: "0,35 - 2,5" -> Tên chuẩn là "0,35-2,5". Map: {"0,35-2,5": ["0,35 - 2,5"]}
   - VD: "21 TUẦN - 20 TUỔI" -> Tên chuẩn là "21 TUẦN-20 TUỔI".
   - VD: "6- MERCAPTOPURINE" -> Tên chuẩn là "6-MERCAPTOPURINE".
2. CHUẨN HÓA TÊN HÓA CHẤT: Đưa các cách viết rời (hoặc phiên âm tiếng Việt) về định dạng viết liền tiêu chuẩn. Áp dụng cho cả cụm từ.
   - Các từ như "CAN XI", "MA GIÊ", "O XI" phải được gom về "CANXI", "MAGIE", "OXY".
   - VD: "BỒI BỔ CAN XI" -> Tên chuẩn là "BỒI BỔ CANXI".
   - VD: "CHUYỂN HÓA CAN XI" -> Tên chuẩn là "CHUYỂN HÓA CANXI". Map: {"CHUYỂN HÓA CANXI": ["CHUYỂN HÓA CAN XI"]}
3. GOM NHÓM VIẾT TẮT:
   - VD: "6 MP", "6-MP", "6-MERCAPTOPURINE" -> Đều gom về "6-MERCAPTOPURINE".
4. CẤM SUY DIỄN (NEGATIVE CONSTRAINTS):
   - KHÔNG ĐƯỢC map các con số, phạm vi giá trị đo lường vào tên chất hóa học hay bệnh lý (VD: Tuyệt đối không map "3,2 - 34,6" vào "3-HYDROXYBUTYRATE"). Con số phải là con số.
   - KHÔNG gộp các bệnh/chất có bản chất khác nhau (VD: Không gộp "VIÊM GAN B" và "VIÊM GAN C").
5. LOẠI BỎ NHIỄU: Bỏ qua hoàn toàn các chuỗi rác định dạng hoặc ký tự vô nghĩa (VD: "#### (\"ENTITY\""). Không đưa chúng vào JSON.

ĐIỀU KIỆN ĐƯA VÀO JSON:
Một thực thể CHỈ xuất hiện trong file JSON nếu thỏa mãn 1 trong 2 điều kiện:
- Có từ 2 biến thể trở lên gom vào cùng 1 tên chuẩn.
- Hoặc chỉ có 1 biến thể nhưng biến thể đó cần được đổi tên theo Quy tắc 1 hoặc Quy tắc 2.
- Nếu một từ đã viết chuẩn sẵn và không có biến thể nào trong danh sách, HÃY BỎ QUA để tối ưu hóa.

ĐỊNH DẠNG ĐẦU RA:
- Trả về DUY NHẤT chuỗi JSON hợp lệ. KHÔNG dùng markdown block (như ```json). KHÔNG giải thích thêm.
- Cấu trúc: {"TÊN_CHUẨN": ["BIẾN_THỂ_RAW_1", "BIẾN_THỂ_RAW_2", ...]}"""

    # 5. Xử lý theo từng Chunk
    for i in range(0, len(remaining_entities), CHUNK_SIZE):
        chunk = remaining_entities[i:i + CHUNK_SIZE]
        logging.info(f"Đang xử lý chunk: {i} đến {i + len(chunk)}...")
        
        user_prompt = json.dumps(chunk, ensure_ascii=False)
        
        try:
            # Gọi API
            raw_response = call_llm_api(system_prompt, user_prompt, cycler)
            batch_result = extract_json_from_response(raw_response)
            
            # Cập nhật kết quả vào progress_data
            for std_name, aliases in batch_result.items():
                if std_name in progress_data:
                    progress_data[std_name].extend(aliases)
                    # Lọc trùng lặp
                    progress_data[std_name] = list(set(progress_data[std_name]))
                else:
                    progress_data[std_name] = aliases

            # SAVE PROGRESS NGAY LẬP TỨC SAU MỖI CHUNK
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=4)
            
            logging.info(f"Lưu chunk thành công. Nghỉ 3s để tránh rate limit...")
            time.sleep(3) # Delay một chút giữa các request để an toàn

        except Exception as e:
            logging.error(f"Dừng tiến trình do lỗi nghiêm trọng: {str(e)}")
            break # Dừng lại để bạn kiểm tra, dữ liệu trước đó đã được lưu an toàn trong PROGRESS_FILE

    # 6. Xuất ra file Final
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=4)
    logging.info(f"HOÀN THÀNH! Kết quả cuối cùng lưu tại {OUTPUT_FILE}")

if __name__ == "__main__":
    main()