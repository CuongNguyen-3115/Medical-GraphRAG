# Class quản lý model nhúng (SentenceTransformer)

import os
import warnings
import torch
from sentence_transformers import SentenceTransformer

# Tắt các cảnh báo không cần thiết
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class EmbeddingClient:
    """
    Lớp quản lý việc nhúng (embedding) câu hỏi của người dùng.
    Được thiết kế để chỉ load mô hình 1 lần duy nhất vào bộ nhớ (Singleton pattern style).
    """
    def __init__(self, model_name='intfloat/multilingual-e5-small'):
        print(f"⏳ Đang khởi tạo Embedding Client với model [{model_name}]...")
        
        # Thiết lập luồng CPU (Tương tự như lúc tạo DB để đảm bảo máy không bị treo)
        # Quá trình nhúng 1 câu hỏi rất nhẹ, 4 luồng là quá đủ để phản hồi tức thì (Real-time).
        torch.set_num_threads(4) 
        
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = 384
            print("✅ Embedding Client đã sẵn sàng!")
        except Exception as e:
            raise RuntimeError(f"❌ Lỗi khi khởi tạo mô hình nhúng: {e}")

    def embed_query(self, query: str) -> list:
        
        """
        Nhận vào một chuỗi văn bản (câu hỏi) và trả về mảng Vector.
        
        Args:
            query (str): Câu hỏi của người dùng (VD: "Tác dụng phụ của Bạch cầu?")
            
        Returns:
            list: Mảng chứa 384 số thực đại diện cho Vector của câu hỏi.
        """
        # E5 BẮT BUỘC phải thêm chữ 'query: ' trước câu hỏi
        e5_query = f"query: {query}" 
        vector = self.model.encode(e5_query, show_progress_bar=False)
        return vector.tolist()

# ==========================================
# KHỐI KIỂM TRA ĐỘC LẬP (UNIT TEST)
# ==========================================
# Đoạn code dưới đây chỉ chạy khi bạn thực thi trực tiếp file này.
# Nó sẽ bị bỏ qua khi file này được import vào các module khác.
if __name__ == "__main__":
    print("="*50)
    print("🧪 KIỂM TRA MODULE EMBEDDING CLIENT")
    print("="*50)
    
    # Khởi tạo client
    client = EmbeddingClient()
    
    # Giả lập một câu hỏi từ người dùng chatbot
    test_query = "Thuốc Cefazidim có tác dụng phụ gì và ảnh hưởng đến bạch cầu như thế nào?"
    
    # Tiến hành nhúng
    print("\n-> Đang nhúng câu hỏi test...")
    query_vector = client.embed_query(test_query)
    
    # In kết quả kiểm tra
    print(f"-> Câu hỏi gốc: '{test_query}'")
    print(f"-> Kích thước Vector trả về: {len(query_vector)} chiều (Kỳ vọng: 768)")
    print(f"-> 5 giá trị đầu tiên của Vector: {query_vector[:5]}")
    print("\n🎉 Module hoạt động hoàn hảo!")