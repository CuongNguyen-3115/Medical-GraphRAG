# Hàm tổng hợp và format text từ Node/Edge thu được để gửi cho LLM

import json
import os
import sys

class LocalContextBuilder:
    """
    Chuyển đổi dữ liệu cấu trúc thô từ Neo4j thành chuỗi văn bản (String Context) 
    sạch sẽ, phân cấp rõ ràng để nạp vào Prompt của LLM.
    """
    def __init__(self):
        pass

    def build_context(self, retrieved_data: list) -> str:
        """
        Xây dựng chuỗi ngữ cảnh từ danh sách thực thể và mối quan hệ.
        
        Args:
            retrieved_data (list): Kết quả trả về từ hàm retrieve_context của GraphRetriever.
            
        Returns:
            str: Chuỗi văn bản đã được định dạng chuẩn học thuật.
        """
        if not retrieved_data:
            return "Không tìm thấy ngữ cảnh y khoa phù hợp trong cơ sở dữ liệu đồ thị."

        context_sections = []
        
        for idx, item in enumerate(retrieved_data, 1):
            entity_name = item.get("entity", "").upper()
            entity_desc = item.get("description", "Không có mô tả.")
            score = item.get("similarity_score", 0.0)
            relationships = item.get("relationships", [])

            # 1. Định dạng phần Thực thể chính (Node Profile)
            node_text = f"=== THỰC THỂ [{idx}]: {entity_name} (Độ khớp: {score}) ===\n"
            node_text += f"[*] Mô tả tri thức: {entity_desc}\n"
            
            # 2. Định dạng phần mạng lưới liên kết xung quanh (Edge Network)
            edge_lines = []
            if relationships:
                edge_lines.append("[*] Mạng lưới liên kết liên quan trực tiếp:")
                for rel in relationships:
                    neighbor = rel.get("neighbor_name", "").upper()
                    rel_desc = rel.get("relation_desc", "Có mối quan hệ lâm sàng.")
                    weight = rel.get("weight", 1)
                    
                    # Định dạng dòng quan hệ sinh động, rành mạch
                    edge_lines.append(f"   - Kết nối với [{neighbor}] | Trọng số tác động: {weight}")
                    edge_lines.append(f"     Chi tiết liên kết: {rel_desc}")
            else:
                edge_lines.append("[*] Mạng lưới liên kết: Thực thể này đứng độc lập trong phân vùng truy xuất hiện tại.")

            # Gộp node text và edge text của thực thể hiện tại
            full_entity_section = node_text + "\n".join(edge_lines)
            context_sections.append(full_entity_section)

        # 3. Kết hợp toàn bộ các phần thực thể lại bằng ranh giới rõ ràng
        final_context = "\n\n" + "="*70 + "\n"
        final_context += "KHO NGỮ CẢNH TRÍCH XUẤT TỪ ĐỒ THỊ Y KHOA (GRAPH CONTEXT)"
        final_context += "\n" + "="*70 + "\n\n"
        final_context += "\n\n----------------------------------------------------------------------\n\n".join(context_sections)
        
        return final_context

# ==========================================
# KHỐI KIỂM TRA TÍCH HỢP (INTEGRATION TEST)
# ==========================================
if __name__ == "__main__":
    # Import các module từ thư mục khác để chạy test tích hợp toàn trình
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    try:
        from module_1_embedding.embedding_client import EmbeddingClient
        from module_2_retrieval.graph_retriever import GraphRetriever
    except ImportError as e:
        print(f"⚠️ Lỗi Import: {e}. Đảm bảo bạn đang chạy file tại đúng thư mục.")
        sys.exit(1)

    print("="*70)
    print("🧪 KIỂM TRA TÍCH HỢP TOÀN TRÌNH: TỪ NEO4J ĐẾN CONTEXT XỬ LÝ")
    print("="*70)
    
    # 1. Khởi tạo 3 bộ phận cốt lõi
    try:
        embedder = EmbeddingClient()
        retriever = GraphRetriever() 
        builder = LocalContextBuilder()
    except Exception as e:
        print(f"❌ Lỗi khởi tạo hệ thống: {e}")
        sys.exit(1)

    # 2. Tiến hành chạy luồng dữ liệu thật
    test_query = "Tác dụng phụ của Bạch cầu là gì?"
    print(f"\n🗣️ Đang xử lý câu hỏi: '{test_query}'")
    
    print("   -> 1/3: Đang nhúng câu hỏi...")
    query_vector = embedder.embed_query(test_query)
    
    print("   -> 2/3: Đang truy xuất Neo4j (Lấy Top 3 để test)...")
    # Lấy Top 3 cho gọn màn hình Console khi test
    real_graph_data = retriever.retrieve_context(query_vector, top_k=3) 
    
    print("   -> 3/3: Đang đóng gói String Context...\n")
    clean_text_context = builder.build_context(real_graph_data)
    
    # 3. In kết quả cuối cùng mà Llama-3 sẽ nhìn thấy
    print(clean_text_context)
    
    print("\n" + "="*70)
    print("🎉 DỮ LIỆU ĐÃ ĐƯỢC ĐÓNG GÓI HOÀN HẢO TỪ DATABASE THẬT!")
    print("Bây giờ LLM chỉ việc đọc chuỗi văn bản cực kỳ rõ ràng này để sinh câu trả lời.")
    print("="*70)
    
    # Đóng kết nối DB
    retriever.close()