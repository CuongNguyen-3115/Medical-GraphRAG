# Quản lý cấu hình: Load file .env, khai báo đường dẫn (Data, Output), các hằng số (ngưỡng Node)

from pathlib import Path

# Xây dựng đường dẫn gốc dựa trên cấu trúc thư mục ĐATN
BASE_DIR = Path(r"C:\1. Project\ĐATN")
DATA_DIR = BASE_DIR / "Data"

# Đường dẫn Input và Output
INPUT_COMMUNITIES_PATH = DATA_DIR / "08_Communities_detecting" / "filtered_communities.json"
OUTPUT_SUMMARIES_DIR = DATA_DIR / "09_Communities_summaries"

# Đảm bảo thư mục output tồn tại, nếu chưa có sẽ tự động tạo
OUTPUT_SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)