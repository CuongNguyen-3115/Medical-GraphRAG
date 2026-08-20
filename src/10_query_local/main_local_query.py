# C:\1. Project\ĐATN\src\10_query_local\main_local_query.py

import os
import sys
import time

# Đảm bảo Python nhận diện đúng đường dẫn các module nội bộ
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_1_embedding.embedding_client import EmbeddingClient
from module_2_retrieval.graph_retriever import GraphRetriever
from module_2_retrieval.context_builder import LocalContextBuilder
from module_3_generation.local_prompt import LOCAL_SEARCH_SYSTEM_PROMPT
from module_3_generation.llm_generator import LLMGenerator

class LocalQueryEngine:
    """
    Trạm điều khiển trung tâm: Tích hợp Embedding, Retrieval và Generation
    để tạo thành một hệ thống GraphRAG Local Search hoàn chỉnh.
    """
    def __init__(self):
        print("="*70)
        print("🚀 KHỞI ĐỘNG HỆ THỐNG GRAPHRAG LOCAL SEARCH TỔNG THỂ")
        print("="*70)
        
        start_time = time.time()
        
        try:
            # Khởi tạo các module (Singleton)
            self.embedder = EmbeddingClient()
            self.retriever = GraphRetriever() 
            self.context_builder = LocalContextBuilder()
            self.llm_generator = LLMGenerator()
            
            print(f"✅ Đã tải toàn bộ hệ thống thành công! (Thời gian: {round(time.time() - start_time, 2)}s)\n")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo hệ thống nghiêm trọng: {e}")
            sys.exit(1)

    def ask(self, query: str, top_k: int = 5):
        """
        Thực thi toàn bộ luồng truy vấn có logging chi tiết.
        """
        print("\n" + "="*70)
        print(f"🗣️ CÂU HỎI USER: {query}")
        print("="*70)
        
        total_start = time.time()

        # ---------------------------------------------------------
        # BƯỚC 1: TRÍCH XUẤT TỪ KHÓA & NHÚNG (KEYWORD EMBEDDING)
        # ---------------------------------------------------------
        print("\n[BƯỚC 1] Phân tích ngữ nghĩa & Sinh Vector (Embedding)...")
        t1 = time.time()
        
        # Gọi LLM để nhặt từ khóa y khoa trước
        search_query = self.llm_generator.extract_search_keywords(query)
        print(f"  -> Từ khóa chắt lọc để quét Đồ thị: [{search_query}]")
        
        # Nhúng các từ khóa này thay vì nhúng cả câu hỏi dài
        query_vector = self.embedder.embed_query(search_query)
        
        t1_end = time.time()
        print(f"  -> Vector chiều dài: {len(query_vector)} dimensions")
        print(f"  -> Thời gian thực thi: {round(t1_end - t1, 4)}s")

        # ---------------------------------------------------------
        # BƯỚC 2: TRUY XUẤT ĐỒ THỊ (RETRIEVAL)
        # ---------------------------------------------------------
        print("\n[BƯỚC 2] Truy vấn cơ sở dữ liệu Neo4j (Vector + Graph Traversal)...")
        t2 = time.time()
        # Truyền cả Vector (để tìm ý nghĩa) và Search Query (để tìm chính xác tên)
        retrieved_data = self.retriever.retrieve_context(
            query_vector=query_vector, 
            search_term=search_query, 
            top_k=top_k
        )
        t2_end = time.time()
        print(f"  -> Số lượng Thực thể (Nodes) tìm thấy: {len(retrieved_data)}")
        for idx, item in enumerate(retrieved_data, 1):
            edge_count = len(item.get('relationships', []))
            print(f"     + Node {idx}: [{item['entity']}] (Score: {item['similarity_score']}) - Kéo theo {edge_count} Edges")
        print(f"  -> Thời gian thực thi: {round(t2_end - t2, 4)}s")

        if not retrieved_data:
            print("⚠️ CẢNH BÁO: Không tìm thấy bất kỳ thông tin nào trong Đồ thị. Dừng luồng xử lý.")
            return

        # ---------------------------------------------------------
        # BƯỚC 3: XÂY DỰNG NGỮ CẢNH (CONTEXT BUILDING)
        # ---------------------------------------------------------
        print("\n[BƯỚC 3] Đóng gói Context JSON thành văn bản phẳng (Plain Text)...")
        t3 = time.time()
        clean_context = self.context_builder.build_context(retrieved_data)
        t3_end = time.time()
        
        # Ước lượng token đơn giản (1 token ~ 4 chars tiếng Việt)
        est_tokens = len(clean_context) // 4 
        print(f"  -> Dung lượng Context ước tính: ~{est_tokens} tokens")
        print(f"  -> Preview Context (Đầu): {clean_context[:1000].replace(chr(10), ' ')}...")
        print(f"  -> Preview Context (Cuối): {clean_context[-1000:].replace(chr(10), ' ')}...")
        print(f"  -> Thời gian thực thi: {round(t3_end - t3, 4)}s")

        # ---------------------------------------------------------
        # BƯỚC 4: SINH CÂU TRẢ LỜI (GENERATION)
        # ---------------------------------------------------------
        print("\n[BƯỚC 4] LLM Groq/Llama-3 đang suy luận và sinh văn bản...")
        t4 = time.time()
        answer = self.llm_generator.generate_answer(
            system_prompt_template=LOCAL_SEARCH_SYSTEM_PROMPT,
            context=clean_context,
            query=query
        )
        t4_end = time.time()
        print(f"  -> Thời gian thực thi (Latency API Groq): {round(t4_end - t4, 4)}s")

        # ---------------------------------------------------------
        # BƯỚC 5: KẾT QUẢ TRẢ VỀ
        # ---------------------------------------------------------
        total_time = round(time.time() - total_start, 2)
        print("\n" + "="*70)
        print(f"🤖 TRỢ LÝ Y KHOA GRAPHRAG (Tổng thời gian: {total_time}s)")
        print("="*70)
        print(answer)
        print("="*70 + "\n")

    def shutdown(self):
        """Đóng an toàn các kết nối khi thoát chương trình."""
        self.retriever.close()
        print("Đã ngắt kết nối an toàn với Cơ sở dữ liệu.")

# ==========================================
# GIAO DIỆN TƯƠNG TÁC (INTERACTIVE LOOP)
# ==========================================
if __name__ == "__main__":
    # Khởi tạo engine
    engine = LocalQueryEngine()
    
    print("\n💡 HƯỚNG DẪN: Gõ câu hỏi của bạn và nhấn Enter.")
    print("💡 Gõ 'exit' hoặc 'quit' để thoát chương trình.\n")
    
    try:
        while True:
            user_input = input(">> Nhập câu hỏi y khoa: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("Đang thoát chương trình...")
                break
                
            if not user_input:
                continue
                
            # Kích hoạt luồng chạy chính với Top K = 5
            engine.ask(query=user_input, top_k=5)
            
    except KeyboardInterrupt:
        print("\nĐã ép buộc dừng chương trình.")
    finally:
        engine.shutdown()