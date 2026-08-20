from fastapi import APIRouter, HTTPException
from schemas.chat_schema import UserQuery
from services.graphrag_service import get_graphrag_response

# Chỉ cần khai báo router như thế này là đủ
router = APIRouter(
    prefix="/api",
    tags=["Chatbot"]
)

@router.post("/chat")
async def chat_with_ai(request: UserQuery):
    """
    Endpoint tiếp nhận câu hỏi y tế, chuyển tiếp qua tầng dịch vụ GraphRAG
    và trả về câu trả lời cuối cùng từ AI Doctor.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
    
    # Gọi service xử lý
    final_reply = await get_graphrag_response(request.query)
    
    return {"reply": final_reply}