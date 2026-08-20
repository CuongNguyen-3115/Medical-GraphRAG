"""
Templates for K-N-M Pipeline: Global Sensemaking Question Generation
Dựa theo Section 3.2: From Local to Global (Microsoft Research)
"""

PERSONA_SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích dữ liệu y khoa và kỹ sư hệ thống AI.
Dựa vào mô tả tập dữ liệu (Corpus) dưới đây, hãy định nghĩa 2 chân dung người dùng (Personas) tiềm năng nhất sẽ cần khai thác tập dữ liệu này để phục vụ công việc chuyên môn của họ. Tập trung vào các vai trò như bác sĩ, dược sĩ lâm sàng, hoặc nhà nghiên cứu.

--- YÊU CẦU ĐẦU RA ---
Trả về ĐÚNG định dạng JSON. KHÔNG thêm bất kỳ văn bản, giải thích hay markdown block (như ```json) nào khác.
{{
  "personas": [
    {{
      "role": "<Tên vai trò>",
      "description": "<Mô tả chi tiết mục tiêu và lý do họ cần dữ liệu này>"
    }}
  ]
}}

--- VÍ DỤ MINH HỌA (FEW-SHOT) ---
Đầu vào Corpus: Cộng đồng này tập trung vào mối quan hệ giữa Tăng huyết áp và các bệnh lý tim mạch khác như Suy tim, Nhồi máu cơ tim. Các loại thuốc điều trị như Enalapril...
Đầu ra JSON:
{{
  "personas": [
    {{
      "role": "Bác sĩ Nội Tim mạch",
      "description": "Cần tra cứu mối liên hệ nhân quả giữa tăng huyết áp và suy tim để tối ưu hóa phác đồ điều trị, đồng thời kiểm tra rủi ro tác dụng phụ của các thuốc."
    }},
    {{
      "role": "Dược sĩ Lâm sàng",
      "description": "Muốn rà soát các tương tác thuốc và tác dụng phụ tiềm ẩn để tư vấn an toàn sử dụng thuốc."
    }}
  ]
}}

--- MÔ TẢ TẬP DỮ LIỆU THỰC TẾ ---
{corpus_summary}
"""

TASK_SYSTEM_PROMPT = """Bạn là một giám đốc y khoa. Hãy xác định 2 tác vụ (Tasks) phân tích mức độ cao, phức tạp mà Persona dưới đây cần thực hiện trên tập dữ liệu được mô tả.
Tác vụ phải đòi hỏi việc phân tích xu hướng, so sánh, hoặc đánh giá rủi ro diện rộng (không phải là việc tra cứu một thông tin cục bộ).

--- YÊU CẦU ĐẦU RA ---
Trả về ĐÚNG định dạng JSON. KHÔNG thêm markdown block hay văn bản thừa.
{{
  "tasks": [
    {{
      "task_name": "<Tên tác vụ ngắn gọn>",
      "task_description": "<Mô tả chi tiết những gì persona cần phân tích để hoàn thành tác vụ>"
    }}
  ]
}}

--- VÍ DỤ MINH HỌA (FEW-SHOT) ---
Đầu vào Corpus: Dữ liệu về Tăng huyết áp, Suy tim, Enalapril...
Đầu vào Persona: Bác sĩ Nội Tim mạch (Cần tra cứu mối liên hệ nhân quả...)
Đầu ra JSON:
{{
  "tasks": [
    {{
      "task_name": "Đánh giá an toàn và hiệu quả của Enalapril",
      "task_description": "Phân tích diện rộng các báo cáo lâm sàng để đánh giá hiệu quả của Enalapril trong việc ngăn ngừa biến chứng nhồi máu cơ tim."
    }},
    {{
      "task_name": "Phân tích rủi ro tương tác thuốc đa bệnh lý",
      "task_description": "Rà soát toàn bộ đồ thị để tìm các chống chỉ định có thể xảy ra khi kê đơn cho bệnh nhân suy tim."
    }}
  ]
}}

--- DỮ LIỆU THỰC TẾ ---
MÔ TẢ TẬP DỮ LIỆU:
{corpus_summary}

PERSONA:
Vai trò: {role}
Mô tả: {description}
"""

QUESTION_SYSTEM_PROMPT = """Bạn là một chuyên gia đánh giá hệ thống thuật toán RAG (AI Evaluator). 
Nhiệm vụ của bạn là sinh ra 2 câu hỏi truy vấn toàn cục (Global Sensemaking Questions) để kiểm tra khả năng tổng hợp thông tin của hệ thống GraphRAG.

--- RÀNG BUỘC TỐI THƯỢNG CHO CÂU HỎI ---
1. TÍNH TOÀN CỤC: Phải đòi hỏi hệ thống quét và kết nối thông tin trên TOÀN BỘ các cụm (communities) dữ liệu.
2. TÍNH TRỪU TƯỢNG: TUYỆT ĐỐI KHÔNG hỏi về các sự kiện chi tiết, tài liệu cụ thể (vd: "Tác dụng phụ của Diltiazem là gì?").
3. TỪ KHÓA BẮT ĐẦU: Nên bắt đầu bằng: "Phân tích...", "Đánh giá tổng thể...", "So sánh xu hướng...", "Chỉ ra bức tranh toàn cảnh về...".

--- YÊU CẦU ĐẦU RA ---
Trả về ĐÚNG định dạng JSON. KHÔNG thêm markdown block hay văn bản thừa.
{{
  "questions": [
    {{
      "question": "<Nội dung câu hỏi phân tích toàn cục>",
      "expected_complexity": "<Giải thích lý do tại sao câu hỏi này đòi hỏi tổng hợp từ nhiều nguồn dữ liệu>"
    }}
  ]
}}

--- VÍ DỤ MINH HỌA (FEW-SHOT) ---
Đầu vào Task: Đánh giá an toàn và hiệu quả của Enalapril
Đầu ra JSON:
{{
  "questions": [
    {{
      "question": "Phân tích bức tranh toàn cảnh về rủi ro biến chứng tim mạch khi sử dụng dài hạn nhóm thuốc ức chế men chuyển (như Enalapril) trên bệnh nhân có tiền sử tăng huyết áp.",
      "expected_complexity": "Câu hỏi này buộc hệ thống phải quét qua các cụm thông tin về Enalapril, suy tim và nhồi máu cơ tim để tổng hợp đối chiếu."
    }},
    {{
      "question": "Đánh giá tổng thể sự khác biệt về hiệu quả lâm sàng giữa các phác đồ điều trị Tăng huyết áp có sử dụng Enalapril so với các nhóm thuốc khác.",
      "expected_complexity": "Yêu cầu hệ thống tổng hợp thông tin từ nhiều nút dữ liệu về phác đồ và thuốc để đưa ra so sánh diện rộng."
    }}
  ]
}}

--- DỮ LIỆU THỰC TẾ ---
MÔ TẢ TẬP DỮ LIỆU:
{corpus_summary}

NGỮ CẢNH NGƯỜI DÙNG:
Vai trò người dùng: {role}
Tác vụ đang thực hiện: {task_name} - {task_description}
"""