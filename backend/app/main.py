"""
企业用工与社保合规智能平台 - FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routers import chat, feedback, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    try:
        init_db()
        print("数据库初始化完成")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
    yield
    # 关闭时清理资源
    print("应用正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="企业用工与社保合规智能平台 API",
    description="首期 MVP 聚焦陕西地区用工与社保合规场景",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "企业用工与社保合规智能平台 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)