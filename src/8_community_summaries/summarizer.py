import json
import re
import tiktoken
from typing import Dict, Optional
from prompts import COMMUNITY_REPORT_PROMPT_VI
from llm_client import call_groq, call_gemini, call_github, call_hf, call_sambanova, call_cerebras

# Khởi tạo Tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    """Đếm chính xác số lượng tokens của một đoạn text."""
    return len(tokenizer.encode(text))

def format_community_data(community: dict, max_input_tokens: int) -> str:
    """Format dữ liệu với cơ chế Cắt tỉa Động (Dynamic Truncation)."""
    nodes = sorted(community.get("nodes", []), key=lambda x: x.get("degree", 0), reverse=True)
    edges = sorted(community.get("edges", []), key=lambda x: x.get("priority_score", 0), reverse=True)
    
    entities_text = "Entities\nid,entity,description\n"
    MAX_DESC_CHARS = 300 
    
    # 1. Ngân sách cho Entities (60%)
    entity_budget_tokens = int(max_input_tokens * 0.6)
    
    for node in nodes:
        node_id, name = node.get("id", ""), node.get("entity_name", "")
        raw_desc = " ".join(node.get("descriptions", [])) if node.get("descriptions") else "Không có mô tả"
        desc = raw_desc[:MAX_DESC_CHARS] + "..." if len(raw_desc) > MAX_DESC_CHARS else raw_desc
        row = f"{node_id},{name},{desc}\n"
        
        if count_tokens(entities_text + row) > entity_budget_tokens:
            entities_text += "...(Đã cắt bớt các thực thể phụ)...\n"
            break
            
        entities_text += row
        
    # 2. Ngân sách cho Relationships (40%)
    current_tokens = count_tokens(entities_text)
    edge_budget_tokens = max_input_tokens - current_tokens
    
    rels_text = "\nRelationships\nid,source,target,description\n"
    current_rel_tokens = count_tokens(rels_text)
    
    if edges:
        for edge in edges:
            rel_id, source, target = edge.get("id", ""), edge.get("source", ""), edge.get("target", "")
            raw_rel_desc = " ".join(edge.get("descriptions", [])) if edge.get("descriptions") else "Không có mô tả"
            rel_desc = raw_rel_desc[:MAX_DESC_CHARS] + "..." if len(raw_rel_desc) > MAX_DESC_CHARS else raw_rel_desc
            row = f"{rel_id},{source},{target},{rel_desc}\n"
            
            row_tokens = count_tokens(row)
            if current_rel_tokens + row_tokens > edge_budget_tokens:
                rels_text += "...(Đã cắt bớt các quan hệ phụ)...\n"
                break
                
            rels_text += row
            current_rel_tokens += row_tokens
    else:
        rels_text += "Không có thông tin mối quan hệ rõ ràng trong cụm này.\n"
        
    return f"{entities_text}\n{rels_text}"

def clean_json_string(raw_string: str) -> str:
    match = re.search(r'\{[\s\S]*\}', raw_string)
    return match.group(0) if match else raw_string

async def attempt_extraction(call_function, system_prompt, user_prompt, comm_id, retries=1, is_vip=False) -> tuple[Optional[Dict], int, str]:
    """Cơ chế vá lỗi JSON tự chữa lành (Self-Healing) chuẩn doanh nghiệp."""
    original_context = user_prompt  # Sao lưu dữ liệu gốc của cụm
    
    for attempt in range(1, retries + 1):
        if call_function.__name__ == 'call_groq':
            raw_res, tokens, out_tokens, err_type = await call_function(system_prompt, user_prompt, comm_id, is_vip=is_vip)
        else:
            raw_res, tokens, out_tokens, err_type = await call_function(system_prompt, user_prompt, comm_id)
            
        if err_type == "413": 
            return None, 0, "413"
        if err_type in ["QUOTA_EXHAUSTED", "ALL_MODELS_FAILED", "GITHUB_FAILED"]:
            return None, 0, "EXHAUSTED"
            
        if not raw_res: 
            continue
            
        try:
            cleaned = clean_json_string(raw_res)
            data = json.loads(cleaned)
            if "title" in data and "findings" in data:
                return data, tokens, "SUCCESS"
        except (json.JSONDecodeError, ValueError) as e:
            print(f"\n[!] [ID: {comm_id} - Lần thử {attempt}] Parse JSON thất bại. Mã lỗi: {e}")
            
            # Nếu output token xấp xỉ mức 1024 (trừ hao khác biệt Tokenizer API), chắc chắn là bị cắt cụt.
            if out_tokens >= 1000:
                print(f"    [!] ID {comm_id}: BỊ CẮT CỤT (Out: {out_tokens}). Đánh dấu là CỤM SIÊU TO.")
                # Trả về cờ TRUNCATED ngay lập tức, không thèm Retry
                return None, out_tokens, "TRUNCATED"
                
            # 3. ÁP DỤNG PATTERN 1: Vá lỗi giữ nguyên Ngữ cảnh gốc + Kết quả lỗi + Chỉ thị sửa
            user_prompt = (
                f"{original_context}\n\n"
                f"=== HỆ THỐNG CẢNH BÁO SỬA LỖI ===\n"
                f"Ở lượt xử lý trước, bạn đã trả về một chuỗi kết quả không hợp lệ hoặc lỗi cú pháp JSON.\n"
                f"Kết quả lỗi trước đó của bạn: \n{raw_res}\n"
                f"YÊU CẦU: Hãy đọc lại DỮ LIỆU ĐẦU VÀO ở trên và viết lại cấu trúc JSON hoàn chỉnh, "
                f"đảm bảo đóng đầy đủ các dấu ngoặc nhọn '}}' và tuân thủ định dạng mẫu."
            )
            
    return None, 0, "PARSE_ERROR"

async def generate_community_summary(community: dict, is_vip: bool = False) -> tuple[Optional[Dict], str]:
    """Trả về Tuple: (Kết quả JSON, Mã trạng thái)"""
    comm_id = community.get("community_id", "Unknown")
    
    # Biến theo dõi xem có tầng nào bị EXHAUSTED không
    is_exhausted = False
    
    # =================================================================
    # TẦNG 1: GROQ
    # =================================================================
    if is_vip:
        # VIP: Cho input rộng rãi hơn một chút
        input_tokens = 5000 
    else:
        input_tokens = 4000
        
    groq_prompt = f"ĐẦU VÀO:\n\n{format_community_data(community, max_input_tokens=input_tokens)}"
    result, tokens, err_type = await attempt_extraction(call_groq, COMMUNITY_REPORT_PROMPT_VI, groq_prompt, comm_id, retries=2, is_vip=is_vip)
    
    if result:
        result["_actual_tokens"] = tokens
        result["_model"] = "Groq"
        return result, "SUCCESS"
    if err_type == "PARSE_ERROR" and is_vip:
        # Nếu đang chạy VIP mà Parse Error -> Ném ra thẳng cờ VIP_FAILED để ghi file
        return None, "VIP_FAILED"
    # --- THÊM DÒNG NÀY ---
    # Nếu bị cắt cụt, thoát ngay luồng thác đổ, ném cờ ra ngoài cho main.py xử lý
    if err_type == "TRUNCATED":
        return None, "TRUNCATED" 
        
    if err_type == "EXHAUSTED": is_exhausted = True
        
    # =================================================================
    # TẦNG 2: GITHUB
    # =================================================================
    print(f"   [!] ID {comm_id}: GROQ thất bại. Đẩy lên Tầng 2 (GitHub)...")
    github_prompt = f"ĐẦU VÀO:\n\n{format_community_data(community, max_input_tokens=6000)}"
    result, tokens, err_type = await attempt_extraction(call_github, COMMUNITY_REPORT_PROMPT_VI, github_prompt, comm_id, retries=1)
    
    if result:
        result["_actual_tokens"] = tokens
        result["_model"] = "GitHub"
        return result, "SUCCESS"
    if err_type == "EXHAUSTED": is_exhausted = True
        
    # =================================================================
    # TẦNG 3: GEMINI
    # =================================================================
    print(f"   [-] ID {comm_id}: GitHub thất bại. Đang chuyển sang Tầng 3 (Gemini)...")
    gemini_prompt = f"ĐẦU VÀO:\n\n{format_community_data(community, max_input_tokens=6000)}"
    
    result, tokens, err_type = await attempt_extraction(lambda s, u, cid: call_gemini(s, u, cid, use_pro=False), COMMUNITY_REPORT_PROMPT_VI, gemini_prompt, comm_id, retries=1)
    if result:
        result["_actual_tokens"] = count_tokens(gemini_prompt) 
        result["_model"] = "Gemini"
        return result, "SUCCESS"
    if err_type == "EXHAUSTED": is_exhausted = True

    # =================================================================
    # TẦNG 4: HUGGING FACE
    # =================================================================
    print(f"   [-] ID {comm_id}: Gemini thất bại. Đẩy sang Tầng 4 (Hugging Face)...")
    hf_prompt = f"ĐẦU VÀO:\n\n{format_community_data(community, max_input_tokens=3000)}"
    result, tokens, err_type = await attempt_extraction(call_hf, COMMUNITY_REPORT_PROMPT_VI, hf_prompt, comm_id, retries=1)
    
    if result:
        result["_actual_tokens"] = tokens
        result["_model"] = "Hugging Face"
        return result, "SUCCESS"
    if err_type == "EXHAUSTED": is_exhausted = True

    # =================================================================
    # TẦNG 5: SAMBANOVA
    # =================================================================
    print(f"   [-] ID {comm_id}: Hugging Face thất bại. Đẩy sang Tầng 5 (SambaNova)...")
    sambanova_prompt = f"ĐẦU VÀO:\n\n{format_community_data(community, max_input_tokens=4000)}"
    result, tokens, err_type = await attempt_extraction(call_sambanova, COMMUNITY_REPORT_PROMPT_VI, sambanova_prompt, comm_id, retries=1)
    
    if result:
        result["_actual_tokens"] = tokens
        result["_model"] = "SambaNova"
        return result, "SUCCESS"
    if err_type == "EXHAUSTED": is_exhausted = True

    # =================================================================
    # TẦNG 6: CEREBRAS
    # =================================================================
    print(f"   [-] ID {comm_id}: SambaNova thất bại. Đẩy sang Tầng 6 (Cerebras)...")
    cerebras_prompt = f"ĐẦU VÀO:\n\n{format_community_data(community, max_input_tokens=4000)}"
    result, tokens, err_type = await attempt_extraction(call_cerebras, COMMUNITY_REPORT_PROMPT_VI, cerebras_prompt, comm_id, retries=1)
    
    if result:
        result["_actual_tokens"] = tokens
        result["_model"] = "Cerebras"
        return result, "SUCCESS"
    if err_type == "EXHAUSTED": is_exhausted = True

    # Kiểm tra xem có phải do Hết Quota toàn tập sau khi đã chạy qua CẢ 6 TẦNG không
    if is_exhausted:
        print(f"   [!] ID {comm_id}: Toàn bộ Hệ sinh thái API cạn kiệt tài nguyên (EXHAUSTED).")
        return None, "GLOBAL_EXHAUSTED"

    # Nếu không phải do Quota mà do dữ liệu quá khó (Vỡ JSON liên tục)
    print(f"   [X] ID {comm_id}: Dữ liệu hỏng hoặc quá phức tạp. Đánh dấu bỏ qua.")
    return None, "FAILED"

