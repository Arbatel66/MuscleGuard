from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware  # 1. 导入中间件
from controller import sync, user, exercise
from lifespan import lifespan

app = FastAPI(lifespan=lifespan)

# 2. 配置 CORS (必须放在 include_router 之前)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # 允许所有来源（包括你的 localhost:3000 和手机端）
    allow_credentials=True,          # 允许携带凭证（如 Cookies）
    allow_methods=["*"],             # 允许所有方法（GET, POST, OPTIONS 等）
    allow_headers=["*"],             # 允许所有请求头
)
app.include_router(sync.router)
app.include_router(user.router)
app.include_router(exercise.router)

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # pnpm dev
    # ngrok http 3000
