"""FastAPI 应用入口。

所有路由在这里统一挂载。启动命令（在 backend 目录下执行）:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.resumes import router as resumes_router
from app.api.users import router as users_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# ---------- 跨域配置 ----------
# 开发期走 Vite 代理其实不会触发跨域；这里放行是为了
# 生产部署或前端直连后端地址的场景（例如 5173 直接调 8000）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 路由注册 ----------
app.include_router(users_router)
app.include_router(resumes_router)


@app.get("/health", tags=["System"])
def health_check():
    """健康检查：确认服务存活，前端和将来的部署探针都会用到。"""
    return {"status": "ok", "app": settings.APP_NAME}
