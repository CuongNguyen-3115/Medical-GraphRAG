# Class gọi API Llama-3/Groq để sinh câu trả lời cuối cùng

import os
from dotenv import load_dotenv
from groq import Groq

class LLMGenerator:
    """
    Module phụ trách giao tiếp với Groq API, truyền Context và Prompt vào LLM 
    để sinh câu trả lời tự nhiên, chính xác.
    """
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        print(f"⏳ Đang khởi tạo LLM Generator với model [{model_name}]...")
        
        # Load biến môi trường từ file .env
        load_dotenv()
        
        # Linh hoạt lấy API Key (Ưu tiên KEY_1 nếu bạn vẫn giữ cấu trúc 4 keys cũ, nếu không lấy mặc định)
        api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
        
        if not api_key:
            raise ValueError("❌ KHÔNG TÌM THẤY API KEY! Hãy kiểm tra lại file .env.")
            
        try:
            self.client = Groq(api_key=api_key)
            self.model_name = model_name
            print("✅ LLM Generator đã kết nối Groq API thành công!")
        except Exception as e:
            raise RuntimeError(f"❌ Lỗi kết nối API: {e}")

    def generate_answer(self, system_prompt_template: str, context: str, query: str) -> str:
        """
        Gửi yêu cầu tới Llama-3 để sinh câu trả lời.
        
        Args:
            system_prompt_template (str): Khuôn mẫu Prompt từ file local_prompt.py
            context (str): Chuỗi ngữ cảnh đã được build từ Graph.
            query (str): Câu hỏi của người dùng.
            
        Returns:
            str: Câu trả lời cuối cùng của Chatbot.
        """
        # 1. Bơm dữ liệu vào Khuôn mẫu Prompt
        final_prompt = system_prompt_template.format(
            context=context,
            query=query
        )
        
        # 2. Cấu hình tin nhắn gửi đi
        # Với Llama-3, ta đưa toàn bộ lệnh và context vào vai 'user' để ép model 
        # chú ý tối đa vào instruction (theo đúng thiết kế prompt của chúng ta).
        messages = [
            {"role": "user", "content": final_prompt}
        ]
        
        # 3. Gọi API sinh phản hồi
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,  # Nhiệt độ thấp (0.1) -> Trả lời logic, khô khan, chuẩn y khoa, không bịa đặt.
                max_tokens=2048,  # Giới hạn token đầu ra để tiết kiệm hạn mức 12K TPM
                top_p=0.9
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                return "⚠️ HỆ THỐNG: Đã đạt giới hạn truy vấn của API (Rate Limit 12K TPM). Vui lòng đợi khoảng 1 phút rồi thử lại."
            else:
                return f"❌ Lỗi phát sinh trong quá trình sinh văn bản: {e}"

# ==========================================
# KHỐI KIỂM TRA ĐỘC LẬP (UNIT TEST)
# ==========================================
if __name__ == "__main__":
    import sys
    
    # Import Prompt Template từ file bên cạnh
    try:
        from local_prompt import LOCAL_SEARCH_SYSTEM_PROMPT
    except ImportError:
        print("⚠️ Không tìm thấy file local_prompt.py. Đảm bảo file này nằm cùng thư mục.")
        sys.exit(1)

    print("="*60)
    print("🧪 KIỂM TRA MODULE LLM GENERATOR")
    print("="*60)
    
    # Khởi tạo Generator
    generator = LLMGenerator()
    
    # Giả lập dữ liệu đã đóng gói
    dummy_context = """
    === THỰC THỂ [1]: MYELOSUPPRESSION (Độ khớp: 0.7606) ===
    [*] Mô tả tri thức: Suy giảm chức năng tủy xương, dẫn đến giảm bạch cầu, hồng cầu và tiểu cầu.
    [*] Mạng lưới liên kết liên quan trực tiếp:
       - Kết nối với [FLUOROURACIL] | Trọng số tác động: 7
         Chi tiết liên kết: Fluorouracil gây suy giảm tủy xương nghiêm trọng.
    """
    dummy_query = "Thuốc nào gây suy giảm chức năng tủy xương?"
    
    print(f"\n🗣️ Câu hỏi: '{dummy_query}'")
    print("⏳ Đang đợi Llama-3 suy luận và trả lời...\n")
    
    # Kích hoạt LLM
    answer = generator.generate_answer(
        system_prompt_template=LOCAL_SEARCH_SYSTEM_PROMPT,
        context=dummy_context,
        query=dummy_query
    )
    
    print("🤖 CHATBOT Y KHOA:")
    print("-" * 50)
    print(answer)
    print("-" * 50)
    print("\n🎉 Module sinh ngôn ngữ hoạt động hoàn hảo!")

# import os
# from dotenv import load_dotenv
# from groq import Groq

# class LLMGenerator:
#     """
#     Module phụ trách giao tiếp với Groq API.
#     Bao gồm 2 nhiệm vụ: Trích xuất từ khóa để Search và Sinh câu trả lời.
#     """
#     def __init__(self, model_name="llama-3.3-70b-versatile"):
#         print(f"⏳ Đang khởi tạo LLM Generator với model [{model_name}]...")
#         load_dotenv()
        
#         api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
#         if not api_key:
#             raise ValueError("❌ KHÔNG TÌM THẤY API KEY! Hãy kiểm tra lại file .env.")
            
#         try:
#             self.client = Groq(api_key=api_key)
#             self.model_name = model_name
#             print("✅ LLM Generator đã kết nối Groq API thành công!")
#         except Exception as e:
#             raise RuntimeError(f"❌ Lỗi kết nối API: {e}")

#     def extract_search_keywords(self, query: str) -> str:
#         """
#         [CẬP NHẬT] Chuyển đổi câu hỏi thành cụm từ khóa tìm kiếm ngữ nghĩa (Semantic Search Query)
#         nhằm giữ lại toàn bộ ngữ cảnh (Đối tượng + Tính chất).
#         """
#         extraction_prompt = f"""
#         Nhiệm vụ của bạn là chuyển đổi câu hỏi của người dùng thành một "Cụm từ khóa tìm kiếm" (Search Query) tối ưu cho công cụ Vector Search Y khoa.
#         - Phải giữ lại TẤT CẢ các vế quan trọng: Đối tượng (Thuốc, bệnh...), Tính chất (Tác dụng phụ, cơ chế...), và Tên cụ thể.
#         - Loại bỏ các từ để hỏi (như thế nào, là gì, tại sao).
#         - Ví dụ 1: Người dùng hỏi "Thuốc nào có tác dụng phụ làm giảm bạch cầu?", bạn trả về: "Thuốc có tác dụng phụ giảm bạch cầu"
#         - Ví dụ 2: Người dùng hỏi "Aspirin điều trị bệnh gì?", bạn trả về: "Aspirin điều trị bệnh"
#         - CHỈ trả về duy nhất cụm từ tìm kiếm, không giải thích gì thêm.

#         Câu hỏi gốc: {query}
#         Cụm từ khóa tìm kiếm:"""
        
#         try:
#             response = self.client.chat.completions.create(
#                 model=self.model_name,
#                 messages=[{"role": "user", "content": extraction_prompt}],
#                 temperature=0.0, 
#                 max_tokens=50
#             )
#             keywords = response.choices[0].message.content.strip()
#             # Xóa dấu ngoặc kép nếu LLM lỡ sinh ra
#             return keywords.replace('"', '').replace("'", "")
#         except Exception:
#             return query

#     def generate_answer(self, system_prompt_template: str, context: str, query: str) -> str:
#         """Sinh câu trả lời từ Context."""
#         final_prompt = system_prompt_template.format(context=context, query=query)
#         messages = [{"role": "user", "content": final_prompt}]
        
#         try:
#             response = self.client.chat.completions.create(
#                 model=self.model_name,
#                 messages=messages,
#                 temperature=0.1,  
#                 max_tokens=2048,  
#                 top_p=0.9
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             error_msg = str(e).lower()
#             if "429" in error_msg or "rate limit" in error_msg:
#                 return "⚠️ HỆ THỐNG: Đạt giới hạn API (Rate Limit 12K TPM). Vui lòng đợi 1 phút."
#             return f"❌ Lỗi sinh văn bản: {e}"

# # ==========================================
# # KHỐI KIỂM TRA ĐỘC LẬP
# # ==========================================
# if __name__ == "__main__":
#     generator = LLMGenerator()
    
#     test_query = "Thuốc nào có tác dụng phụ làm giảm bạch cầu và cơ chế của nó là gì?"
#     print(f"\n🗣️ Câu hỏi gốc: '{test_query}'")
    
#     keywords = generator.extract_search_keywords(test_query)
#     print(f"🔑 Từ khóa trích xuất để Search: '{keywords}'")