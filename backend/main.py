from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router

app = FastAPI(
    title="Medical GraphRAG API",
    description="Backend API phục vụ hệ thống hỏi đáp y tế sử dụng GraphRAG và Neo4j",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các endpoints từ tầng API vào ứng dụng chính
app.include_router(chat_router)

@app.get("/")
async def root():
    return {"message": "API Backend GraphRAG đang hoạt động ổn định!"}