import os
import sys

# 1. Lấy đường dẫn của file hiện tại (...\backend\services)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Đi ngược lên 2 cấp để tìm gốc dự án (C:\1. Project\ĐATN)
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

# 3. Trỏ chính xác vào thư mục chứa file main_query.py
# ĐÃ SỬA: "9_query" thành "9_query_global"
target_query_dir = os.path.join(project_root, "src", "9_query_global")

# 4. Ép Python nạp thư mục này vào danh sách tìm kiếm hệ thống
if target_query_dir not in sys.path:
    sys.path.append(target_query_dir)

# 5. Bây giờ bạn import trực tiếp từ file main_query cực kỳ an toàn
from main_query import run_graphrag_pipeline  # type: ignore

async def get_graphrag_response(user_query: str) -> str:
    """
    Service wrapper gọi trực tiếp pipeline GraphRAG từ core hệ thống.
    Mặc định bật use_checkpoint=True cho môi trường dev/test.
    """
    try:
        # Kích hoạt pipeline bất đồng bộ mà bạn đã viết sẵn
        # answer = await run_graphrag_pipeline(user_query, use_checkpoint=True)
        answer = await run_graphrag_pipeline(user_query, use_checkpoint=False)
        return answer
    except Exception as e:
        # Log lỗi hoặc xử lý exception bọc ngoài
        return f"Đã xảy ra lỗi trong quá trình xử lý luồng GraphRAG: {str(e)}"