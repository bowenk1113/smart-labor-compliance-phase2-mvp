"""企业用工与社保合规智能平台 API 入口。"""  # 模块文档字符串，概述当前文件职责
from collections import defaultdict, deque  # 导入当前模块运行所依赖的工具或类型
from contextlib import asynccontextmanager  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from time import monotonic  # 导入当前模块运行所依赖的工具或类型

from fastapi import FastAPI, HTTPException, Request  # 导入 FastAPI 的路由、请求和依赖注入对象
from fastapi.middleware.cors import CORSMiddleware  # 导入 FastAPI 的路由、请求和依赖注入对象
from fastapi.staticfiles import StaticFiles  # 导入 FastAPI 的路由、请求和依赖注入对象
from starlette.middleware.base import BaseHTTPMiddleware  # 导入 Starlette 提供的响应或线程池工具
from starlette.responses import FileResponse, JSONResponse  # 导入 Starlette 提供的响应或线程池工具

from app.database import init_db, settings  # 导入数据库依赖与全局运行配置
from app.response import ok  # 导入统一成功响应与分页响应封装
from app.routers import admin, chat, feedback  # 导入当前模块运行所依赖的工具或类型


class SecurityHeadersMiddleware(BaseHTTPMiddleware):  # 定义统一补充安全响应头的中间件
    async def dispatch(self, request: Request, call_next):  # 定义异步处理函数 dispatch
        response = await call_next(request)  # 保存当前分支生成的响应对象
        response.headers["X-Content-Type-Options"] = "nosniff"  # 为响应补充安全相关的 HTTP 头
        response.headers["X-Frame-Options"] = "DENY"  # 为响应补充安全相关的 HTTP 头
        response.headers["Referrer-Policy"] = "no-referrer"  # 为响应补充安全相关的 HTTP 头
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"  # 为响应补充安全相关的 HTTP 头
        response.headers["Cache-Control"] = "no-store"  # 为响应补充安全相关的 HTTP 头
        return response  # 返回当前分支整理好的结果


class RequestGuardMiddleware(BaseHTTPMiddleware):  # 定义请求体大小与访问频率限制中间件
    def __init__(self, app):  # 定义业务处理函数 __init__
        super().__init__(app)  # 执行当前业务步骤并推进后续处理
        self.buckets: dict[str, deque[float]] = defaultdict(deque)  # 初始化按客户端区分的限流桶缓存

    async def dispatch(self, request: Request, call_next):  # 定义异步处理函数 dispatch
        content_length = request.headers.get("content-length")  # 更新当前逻辑中的 content length
        upload_paths = ("/sources/upload", "/chat-with-file")  # 更新当前逻辑中的 upload paths
        limit = settings.max_upload_bytes if request.url.path.endswith(upload_paths) else settings.max_request_bytes  # 更新当前逻辑中的 limit
        if content_length and int(content_length) > limit:  # 根据当前条件决定是否进入对应业务分支
            return JSONResponse(status_code=413, content={"detail": "请求体过大"})  # 直接返回 JSON 错误响应给前端

        client = request.client.host if request.client else "unknown"  # 更新当前逻辑中的 client
        now = monotonic()  # 更新当前逻辑中的 now
        bucket = self.buckets[client]  # 更新当前逻辑中的 bucket
        while bucket and now - bucket[0] > settings.rate_limit_window_seconds:  # 在条件满足时持续循环处理
            bucket.popleft()  # 移除超出限流窗口的旧请求时间戳
        if len(bucket) >= settings.rate_limit_max_requests:  # 根据当前条件决定是否进入对应业务分支
            return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})  # 直接返回 JSON 错误响应给前端
        bucket.append(now)  # 记录本次请求时间，纳入限流统计
        return await call_next(request)  # 返回当前分支整理好的结果


@asynccontextmanager  # 为后续函数或类声明附加装饰器配置
async def lifespan(app: FastAPI):  # 定义异步处理函数 lifespan
    init_db()  # 执行当前业务步骤并推进后续处理
    yield  # 把当前结果交给 FastAPI 依赖或生成器继续消费


app = FastAPI(  # 更新当前逻辑中的 app
    title="企业用工与社保合规智能平台 API",  # 设置 FastAPI 的 标题
    description="前后端分离、多租户隔离、Dify/RAGFlow 可配置接入的企业合规智能问答平台。",  # 设置 FastAPI 的 说明描述
    version="2.0.0",  # 设置 FastAPI 的 版本
    docs_url="/docs",  # 设置 FastAPI 的 docs url
    redoc_url="/redoc",  # 设置 FastAPI 的 redoc url
    lifespan=lifespan,  # 设置 FastAPI 的 lifespan
)  # 结束 FastAPI 的定义或组装

app.add_middleware(RequestGuardMiddleware)  # 为 FastAPI 应用挂载中间件能力
app.add_middleware(SecurityHeadersMiddleware)  # 为 FastAPI 应用挂载中间件能力
app.add_middleware(  # 为 FastAPI 应用挂载中间件能力
    CORSMiddleware,  # 执行当前业务步骤并推进后续处理
    allow_origins=settings.cors_origins,  # 更新当前逻辑中的 allow origins
    allow_origin_regex=settings.cors_origin_regex,  # 更新当前逻辑中的 allow origin regex
    allow_credentials=True,  # 更新当前逻辑中的 allow credentials
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 更新当前逻辑中的 allow methods
    allow_headers=["Authorization", "Content-Type", "X-Tenant-Code"],  # 更新当前逻辑中的 allow headers
)  # 执行当前业务步骤并推进后续处理

app.include_router(chat.router)  # 把对应子路由注册到 FastAPI 主应用中
app.include_router(feedback.router)  # 把对应子路由注册到 FastAPI 主应用中
app.include_router(admin.router)  # 把对应子路由注册到 FastAPI 主应用中


def frontend_dist_dir() -> Path:  # 定义前端构建目录解析函数
    """解析前端生产构建目录。"""  # 函数文档字符串，说明 frontend_dist_dir 的职责

    # main.py 位于 backend/app/main.py，parents[1] 是 backend 目录。
    backend_dir = Path(__file__).resolve().parents[1]  # 更新当前逻辑中的 backend dir
    # 支持 .env 中写绝对路径，也支持默认的 ../frontend/dist 相对路径。
    configured = Path(settings.frontend_dist_path)  # 更新当前逻辑中的 configured
    if not configured.is_absolute():  # 根据当前条件决定是否进入对应业务分支
        configured = backend_dir / configured  # 更新当前逻辑中的 configured
    return configured.resolve()  # 返回当前分支整理好的结果


def mount_frontend_if_enabled() -> None:  # 定义前端静态资源挂载逻辑
    """在没有 Nginx 时，用 FastAPI 直接托管 frontend/dist。"""  # 函数文档字符串，说明 mount_frontend_if_enabled 的职责

    # 默认关闭，避免开发模式下覆盖 API 根路径；生产单服务部署时由 SERVE_FRONTEND=true 开启。
    if not settings.serve_frontend:  # 根据当前条件决定是否进入对应业务分支
        return  # 结束当前函数并返回空结果
    dist_dir = frontend_dist_dir()  # 更新当前逻辑中的 dist dir
    assets_dir = dist_dir / "assets"  # 更新当前逻辑中的 assets dir
    index_file = dist_dir / "index.html"  # 更新当前逻辑中的 index file
    if not index_file.exists():  # 根据当前条件决定是否进入对应业务分支
        # 前端没有 build 时不挂载，避免启动失败；日志通过 print 留给部署排障。
        print(f"[smart-labor] frontend dist not found, skip static mount: {dist_dir}")  # 执行当前业务步骤并推进后续处理
        return  # 结束当前函数并返回空结果
    if assets_dir.exists():  # 根据当前条件决定是否进入对应业务分支
        # /assets 对应 Vite build 产物中的 JS/CSS 静态资源。
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend_assets")  # 执行当前业务步骤并推进后续处理

    @app.get("/{full_path:path}", include_in_schema=False)  # 为后续函数或类声明附加装饰器配置
    async def serve_frontend(full_path: str):  # 定义异步处理函数 serve_frontend
        """Vue Router history fallback：非 API 路径统一返回 index.html。"""  # 函数文档字符串，说明 serve_frontend 的职责

        # 这些路径属于后端接口或文档，不能被前端 fallback 吃掉。
        reserved_prefixes = ("api/", "docs", "redoc", "openapi.json", "health")  # 更新当前逻辑中的 reserved prefixes
        if full_path.startswith(reserved_prefixes):  # 根据当前条件决定是否进入对应业务分支
            raise HTTPException(status_code=404, detail="Not Found")  # 抛出 HTTP 异常并把错误信息返回给前端
        return FileResponse(index_file)  # 返回前端入口文件或静态文件


@app.exception_handler(HTTPException)  # 为后续函数或类声明附加装饰器配置
async def http_exception_handler(request: Request, exc: HTTPException):  # 定义统一 HTTP 异常处理器
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail, "data": None})  # 直接返回 JSON 错误响应给前端


@app.get("/")  # 为后续函数或类声明附加装饰器配置
async def root():  # 定义系统根路径接口
    if settings.serve_frontend:  # 根据当前条件决定是否进入对应业务分支
        index_file = frontend_dist_dir() / "index.html"  # 更新当前逻辑中的 index file
        if index_file.exists():  # 根据当前条件决定是否进入对应业务分支
            return FileResponse(index_file)  # 返回前端入口文件或静态文件
    return ok(  # 按统一成功响应格式返回结果
        {  # 设置 ok 的 字段
            "name": settings.app_name,  # 设置 ok 的 名称
            "version": "2.0.0",  # 设置 ok 的 版本
            "docs": "/docs",  # 设置 ok 的 docs
            "health": "/health",  # 设置 ok 的 health
        }  # 设置 ok 的 字段
    )  # 结束 ok 的定义或组装


@app.get("/health")  # 为后续函数或类声明附加装饰器配置
async def health_check():  # 定义服务健康检查接口
    return ok({"status": "healthy", "database": settings.db_name})  # 按统一成功响应格式返回结果


# 前端 fallback 必须最后注册，避免覆盖 /health、/docs、/api 等后端路由。
mount_frontend_if_enabled()  # 按配置决定是否由 FastAPI 托管前端构建产物
