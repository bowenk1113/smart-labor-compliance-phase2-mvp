"""
数据库与运行配置。

项目使用本机 Docker MySQL。为避免旧版演示表结构影响新项目，新的业务表统一使用
`slc_` 前缀。
"""
import json  # 导入 JSON 编解码工具，处理结构化字段
import os  # 导入当前模块运行所依赖的工具或类型
from functools import lru_cache  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from typing import List  # 导入当前模块运行所依赖的工具或类型
from urllib.parse import quote_plus  # 导入当前模块运行所依赖的工具或类型

import pymysql  # 导入当前模块运行所依赖的工具或类型
from pydantic import Field, field_validator  # 导入 Pydantic 数据校验或配置能力
from pydantic_settings import BaseSettings  # 导入 Pydantic 数据校验或配置能力
from sqlalchemy import create_engine, inspect, text  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import declarative_base, sessionmaker  # 导入 SQLAlchemy 会话与 ORM 相关能力


def load_dotenv_into_process() -> None:  # 定义 .env 预加载函数
    """把 backend/.env 写入当前 Python 进程环境变量。

    Pydantic Settings 可以直接读取 `.env`，但 RAG 检索、LLM 生成等模块中也有一些轻量配置使用
    `os.getenv()` 读取。这里在应用启动早期把 `.env` 注入 `os.environ`，保证两类读取方式看到同一套配置。
    已经由系统环境变量显式设置的值不会被覆盖，方便生产服务器用更高优先级的环境变量托管密钥。
    """

    # database.py 位于 backend/app/database.py，parents[1] 正好是 backend 目录。
    env_file = Path(__file__).resolve().parents[1] / ".env"  # 更新当前逻辑中的 env file
    # 没有 .env 时直接返回，方便容器或服务器完全使用系统环境变量。
    if not env_file.exists():  # 根据当前条件决定是否进入对应业务分支
        return  # 结束当前函数并返回空结果
    # 逐行读取 .env，支持 KEY=VALUE 形式；空行和注释行会被跳过。
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():  # 遍历当前集合中的每一项并逐个处理
        line = raw_line.strip()  # 更新当前逻辑中的 line
        if not line or line.startswith("#") or "=" not in line:  # 根据当前条件决定是否进入对应业务分支
            continue  # 跳过当前项，继续处理下一项数据
        key, value = line.split("=", 1)  # 执行当前业务步骤并推进后续处理
        key = key.strip()  # 更新当前逻辑中的 key
        value = value.strip().strip('"').strip("'")  # 读取当前字段原始值，准备转成导出格式
        if key:  # 根据当前条件决定是否进入对应业务分支
            os.environ.setdefault(key, value)  # 仅在系统环境未覆盖时写入 .env 中的配置值


# 在 Settings 初始化前先加载 .env，保证 settings 与 os.getenv 使用一致的配置来源。
load_dotenv_into_process()  # 在读取全局配置前先把 .env 注入进程环境变量


class Settings(BaseSettings):  # 定义业务类 Settings
    """应用配置，支持通过 backend/.env 覆盖。"""  # 类文档字符串，概述 Settings 的用途

    app_name: str = "企业用工与社保合规智能平台"  # 更新当前逻辑中的 app name
    app_env: str = "development"  # 更新当前逻辑中的 app env
    api_prefix: str = "/api"  # 更新当前逻辑中的 api prefix
    # serve_frontend=True 时，FastAPI 会直接托管 frontend/dist，适合没有 Nginx 的单服务部署。
    serve_frontend: bool = False  # 更新当前逻辑中的 serve frontend
    # frontend_dist_path 支持相对 backend 目录或绝对路径，默认指向项目根目录下的 frontend/dist。
    frontend_dist_path: str = "../frontend/dist"  # 更新当前逻辑中的 frontend dist path

    db_host: str = "127.0.0.1"  # 更新当前逻辑中的 db host
    db_port: int = 3306  # 更新当前逻辑中的 db port
    db_user: str = "root"  # 更新当前逻辑中的 db user
    db_password: str = "infini_rag_flow"  # 更新当前逻辑中的 db password
    db_name: str = "employment"  # 更新当前逻辑中的 db name
    db_backend: str = "sqlite"  # 更新当前逻辑中的 db backend
    sqlite_path: str = "storage/slc_phase2.db"  # 更新当前逻辑中的 sqlite path

    jwt_secret_key: str = "change-this-dev-secret-before-production"  # 更新当前逻辑中的 jwt secret key
    jwt_expire_minutes: int = 480  # 更新当前逻辑中的 jwt expire minutes
    password_min_length: int = 8  # 执行当前控制流分支

    initial_admin_username: str = "admin"  # 更新当前逻辑中的 initial admin username
    initial_admin_password: str = "Admin@123456"  # 更新当前逻辑中的 initial admin password
    default_tenant_code: str = "demo-sx"  # 更新当前逻辑中的 default tenant code

    cors_origins: List[str] = Field(  # 更新当前逻辑中的 cors origins
        default_factory=lambda: [  # 更新当前逻辑中的 default factory
            "http://localhost:5173",  # 执行当前业务步骤并推进后续处理
            "http://127.0.0.1:5173",  # 执行当前业务步骤并推进后续处理
            "http://localhost:4173",  # 执行当前业务步骤并推进后续处理
            "http://127.0.0.1:4173",  # 执行当前业务步骤并推进后续处理
            "http://localhost:3000",  # 执行当前业务步骤并推进后续处理
            "http://127.0.0.1:3000",  # 执行当前业务步骤并推进后续处理
            "http://localhost:3001",  # 执行当前业务步骤并推进后续处理
            "http://127.0.0.1:3001",  # 执行当前业务步骤并推进后续处理
        ]  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    cors_origin_regex: str = (  # 更新当前逻辑中的 cors origin regex
        r"^https?://("  # 更新当前逻辑中的 cors origin regex
        r"localhost|127\.0\.0\.1|"  # 更新当前逻辑中的 cors origin regex
        r"10(?:\.\d{1,3}){3}|"  # 更新当前逻辑中的 cors origin regex
        r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}|"  # 更新当前逻辑中的 cors origin regex
        r"192\.168(?:\.\d{1,3}){2}"  # 更新当前逻辑中的 cors origin regex
        r")(?::\d{1,5})?$"  # 更新当前逻辑中的 cors origin regex
    )  # 执行当前业务步骤并推进后续处理

    max_request_bytes: int = 1024 * 1024  # 更新当前逻辑中的 max request bytes
    max_upload_bytes: int = 10 * 1024 * 1024  # 更新当前逻辑中的 max upload bytes
    upload_dir: str = "storage/uploads"  # 更新当前逻辑中的 upload dir
    rate_limit_window_seconds: int = 60  # 更新当前逻辑中的 rate limit window seconds
    rate_limit_max_requests: int = 120  # 更新当前逻辑中的 rate limit max requests

    dify_base_url: str = "http://127.0.0.1/v1"  # 更新当前逻辑中的 dify base url
    dify_api_key: str = ""  # 更新当前逻辑中的 dify api key
    dify_timeout_seconds: int = 30  # 更新当前逻辑中的 dify timeout seconds

    ragflow_base_url: str = "http://127.0.0.1:9380"  # 更新当前逻辑中的 ragflow base url
    ragflow_web_url: str = "http://127.0.0.1:8880"  # 更新当前逻辑中的 ragflow web url
    ragflow_api_key: str = ""  # 更新当前逻辑中的 ragflow api key
    ragflow_timeout_seconds: int = 10  # 更新当前逻辑中的 ragflow timeout seconds

    auto_seed: bool = True  # 更新当前逻辑中的 auto seed

    model_config = {  # 更新当前逻辑中的 model config
        "env_file": ".env",  # 填充返回或配置中的 env file 字段
        "env_file_encoding": "utf-8",  # 填充返回或配置中的 env file encoding 字段
        "extra": "allow",  # 填充返回或配置中的 extra 字段
    }  # 结束 model_config 的定义或组装

    @field_validator("cors_origins", mode="before")  # 为后续函数或类声明附加装饰器配置
    @classmethod  # 为后续函数或类声明附加装饰器配置
    def parse_cors_origins(cls, value):  # 定义业务处理函数 parse_cors_origins
        if isinstance(value, str):  # 根据当前条件决定是否进入对应业务分支
            return [item.strip() for item in value.split(",") if item.strip()]  # 返回当前分支整理好的结果
        return value  # 返回当前分支整理好的结果


@lru_cache  # 为后续函数或类声明附加装饰器配置
def get_settings() -> Settings:  # 定义全局配置获取函数
    return Settings()  # 返回当前分支整理好的结果


settings = get_settings()  # 缓存全局运行配置对象供各模块复用


def _safe_identifier(identifier: str) -> str:  # 定义业务处理函数 _safe_identifier
    return identifier.replace("`", "``")  # 返回当前分支整理好的结果


def create_database_if_not_exists() -> None:  # 定义数据库存在性检查与创建逻辑
    """确保目标库存在。"""  # 函数文档字符串，说明 create_database_if_not_exists 的职责
    if settings.db_backend.lower() == "sqlite":  # 根据当前条件决定是否进入对应业务分支
        return  # 结束当前函数并返回空结果
    connection = pymysql.connect(  # 更新当前逻辑中的 connection
        host=settings.db_host,  # 设置 connect 的 host
        port=settings.db_port,  # 设置 connect 的 port
        user=settings.db_user,  # 设置 connect 的 user
        password=settings.db_password,  # 设置 connect 的 password
        charset="utf8mb4",  # 设置 connect 的 charset
        cursorclass=pymysql.cursors.DictCursor,  # 设置 connect 的 cursorclass
        connect_timeout=10,  # 设置 connect 的 connect timeout
    )  # 结束 connect 的定义或组装
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        with connection.cursor() as cursor:  # 执行当前业务步骤并推进后续处理
            cursor.execute(  # 执行当前业务步骤并推进后续处理
                f"CREATE DATABASE IF NOT EXISTS `{_safe_identifier(settings.db_name)}` "  # 执行当前业务步骤并推进后续处理
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
        connection.commit()  # 执行当前业务步骤并推进后续处理
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        connection.close()  # 执行当前业务步骤并推进后续处理


create_database_if_not_exists()  # 在创建数据库引擎前确保目标数据库已经存在

if settings.db_backend.lower() == "sqlite":  # 根据当前条件决定是否进入对应业务分支
    sqlite_file = settings.sqlite_path  # 更新当前逻辑中的 sqlite file
    if not sqlite_file.startswith(("/", "\\")) and ":" not in sqlite_file:  # 根据当前条件决定是否进入对应业务分支
        sqlite_file = str((__import__("pathlib").Path(__file__).resolve().parents[2] / sqlite_file))  # 更新当前逻辑中的 sqlite file
    __import__("pathlib").Path(sqlite_file).parent.mkdir(parents=True, exist_ok=True)  # 执行当前业务步骤并推进后续处理
    DATABASE_URL = f"sqlite:///{sqlite_file}"  # 保存当前环境最终使用的数据库连接串
    engine = create_engine(  # 创建当前运行环境对应的数据库引擎
        DATABASE_URL,  # 设置 create_engine 的 字段
        echo=False,  # 设置 create_engine 的 echo
        connect_args={"check_same_thread": False},  # 设置 create_engine 的 check same thread
        future=True,  # 设置 create_engine 的 future
    )  # 结束 create_engine 的定义或组装
else:  # 处理其他未命中的业务情况
    DATABASE_URL = (  # 保存当前环境最终使用的数据库连接串
        f"mysql+pymysql://{quote_plus(settings.db_user)}:{quote_plus(settings.db_password)}"  # 执行当前业务步骤并推进后续处理
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理

    engine = create_engine(  # 创建当前运行环境对应的数据库引擎
        DATABASE_URL,  # 设置 create_engine 的 字段
        echo=False,  # 设置 create_engine 的 echo
        pool_pre_ping=True,  # 设置 create_engine 的 pool pre ping
        pool_recycle=1800,  # 设置 create_engine 的 pool recycle
        pool_size=10,  # 设置 create_engine 的 pool size
        max_overflow=20,  # 设置 create_engine 的 max overflow
        future=True,  # 设置 create_engine 的 future
    )  # 结束 create_engine 的定义或组装

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)  # 创建数据库会话工厂供请求复用
Base = declarative_base()  # 声明所有 ORM 模型共享的基类


def get_db():  # 定义数据库会话依赖生成器
    """FastAPI 依赖：获取数据库会话。"""  # 函数文档字符串，说明 get_db 的职责
    db = SessionLocal()  # 创建新的数据库会话
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        yield db  # 把当前结果交给 FastAPI 依赖或生成器继续消费
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        db.close()  # 执行当前业务步骤并推进后续处理


def init_db() -> None:  # 定义数据库初始化入口
    """初始化表结构与演示数据。"""  # 函数文档字符串，说明 init_db 的职责
    from app.models import (  # 导入当前业务会读写的 ORM 模型
        admin,  # 执行当前业务步骤并推进后续处理
        chat_log,  # 执行当前业务步骤并推进后续处理
        feedback,  # 执行当前业务步骤并推进后续处理
        faq,  # 执行当前业务步骤并推进后续处理
        knowledge_package,  # 执行当前业务步骤并推进后续处理
        source,  # 执行当前业务步骤并推进后续处理
        tenant,  # 执行当前业务步骤并推进后续处理
        test_question,  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理

    Base.metadata.create_all(bind=engine)  # 根据 ORM 模型自动创建缺失的数据表
    ensure_compat_columns()  # 补齐旧版本数据库可能缺失的兼容字段

    if settings.auto_seed:  # 根据当前条件决定是否进入对应业务分支
        from app.services.seed_data import seed_initial_data  # 导入外部问答或种子数据相关服务

        with SessionLocal() as db:  # 执行当前业务步骤并推进后续处理
            seed_initial_data(db)  # 写入演示租户、FAQ 和资料等初始化数据


def ensure_compat_columns() -> None:  # 定义旧库兼容字段补齐逻辑
    """为已存在的旧演示库补齐新增字段。"""  # 函数文档字符串，说明 ensure_compat_columns 的职责
    if settings.db_backend.lower() == "sqlite":  # 根据当前条件决定是否进入对应业务分支
        return  # 结束当前函数并返回空结果
    inspector = inspect(engine)  # 更新当前逻辑中的 inspector
    tables = set(inspector.get_table_names())  # 更新当前逻辑中的 tables

    def add_missing_columns(table_name: str, definitions: dict[str, str]) -> None:  # 定义业务处理函数 add_missing_columns
        if table_name not in tables:  # 根据当前条件决定是否进入对应业务分支
            return  # 结束当前函数并返回空结果
        columns = {column["name"] for column in inspector.get_columns(table_name)}  # 更新当前逻辑中的 columns
        with engine.begin() as connection:  # 执行当前业务步骤并推进后续处理
            for column_name, ddl in definitions.items():  # 遍历当前集合中的每一项并逐个处理
                if column_name not in columns:  # 根据当前条件决定是否进入对应业务分支
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))  # 执行当前业务步骤并推进后续处理

    def add_missing_indexes(table_name: str, definitions: dict[str, str]) -> None:  # 定义业务处理函数 add_missing_indexes
        if table_name not in tables:  # 根据当前条件决定是否进入对应业务分支
            return  # 结束当前函数并返回空结果
        indexes = {  # 更新当前逻辑中的 indexes
            index["name"]  # 填充返回或配置中的 字段 字段
            for index in inspector.get_indexes(table_name)  # 填充返回或配置中的 字段 字段
        } | {  # 结束 indexes 的定义或组装
            constraint["name"]  # 执行当前业务步骤并推进后续处理
            for constraint in inspector.get_unique_constraints(table_name)  # 遍历当前集合中的每一项并逐个处理
            if constraint.get("name")  # 根据当前条件决定是否进入对应业务分支
        }  # 执行当前业务步骤并推进后续处理
        with engine.begin() as connection:  # 执行当前业务步骤并推进后续处理
            for index_name, ddl in definitions.items():  # 遍历当前集合中的每一项并逐个处理
                if index_name not in indexes:  # 根据当前条件决定是否进入对应业务分支
                    connection.execute(text(f"ALTER TABLE {table_name} ADD INDEX {index_name} {ddl}"))  # 执行当前业务步骤并推进后续处理

    def add_missing_unique_indexes(table_name: str, definitions: dict[str, str]) -> None:  # 定义业务处理函数 add_missing_unique_indexes
        if table_name not in tables:  # 根据当前条件决定是否进入对应业务分支
            return  # 结束当前函数并返回空结果
        indexes = {  # 更新当前逻辑中的 indexes
            index["name"]  # 填充返回或配置中的 字段 字段
            for index in inspector.get_indexes(table_name)  # 填充返回或配置中的 字段 字段
        } | {  # 结束 indexes 的定义或组装
            constraint["name"]  # 执行当前业务步骤并推进后续处理
            for constraint in inspector.get_unique_constraints(table_name)  # 遍历当前集合中的每一项并逐个处理
            if constraint.get("name")  # 根据当前条件决定是否进入对应业务分支
        }  # 执行当前业务步骤并推进后续处理
        with engine.begin() as connection:  # 执行当前业务步骤并推进后续处理
            for index_name, ddl in definitions.items():  # 遍历当前集合中的每一项并逐个处理
                if index_name not in indexes:  # 根据当前条件决定是否进入对应业务分支
                    connection.execute(text(f"ALTER TABLE {table_name} ADD UNIQUE KEY {index_name} {ddl}"))  # 执行当前业务步骤并推进后续处理

    add_missing_columns(  # 执行当前业务步骤并推进后续处理
        "slc_sources",  # 执行当前业务步骤并推进后续处理
        {  # 执行当前业务步骤并推进后续处理
            "source_code": "source_code VARCHAR(40) NULL AFTER tenant_id",  # 执行当前业务步骤并推进后续处理
            "reviewed_at": "reviewed_at DATETIME NULL AFTER review_status",  # 执行当前业务步骤并推进后续处理
            "reviewed_by": "reviewed_by VARCHAR(80) NULL AFTER reviewed_at",  # 执行当前业务步骤并推进后续处理
            "captured_at": "captured_at DATE NULL AFTER review_status",  # 执行当前业务步骤并推进后续处理
            "owner": "owner VARCHAR(80) NULL AFTER captured_at",  # 执行当前业务步骤并推进后续处理
            "local_file": "local_file VARCHAR(500) NULL AFTER owner",  # 执行当前业务步骤并推进后续处理
            "note": "note TEXT NULL AFTER local_file",  # 执行当前业务步骤并推进后续处理
        },  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    if "slc_sources" in tables:  # 根据当前条件决定是否进入对应业务分支
        with engine.begin() as connection:  # 执行当前业务步骤并推进后续处理
            connection.execute(text("UPDATE slc_sources SET issuer = '' WHERE issuer IS NULL"))  # 执行当前业务步骤并推进后续处理
            connection.execute(text("""
                UPDATE slc_sources
                SET reviewed_at = COALESCE(reviewed_at, created_at),
                    reviewed_by = COALESCE(reviewed_by, owner, '系统初始化')
                WHERE review_status IN ('已复核', 'reviewed')
            """))
            connection.execute(text("ALTER TABLE slc_sources MODIFY issuer VARCHAR(120) NOT NULL DEFAULT ''"))  # 执行当前业务步骤并推进后续处理
    add_missing_indexes("slc_sources", {"ix_slc_sources_source_code": "(source_code)"})  # 执行当前业务步骤并推进后续处理
    add_missing_columns("slc_faqs", {"faq_code": "faq_code VARCHAR(40) NULL AFTER tenant_id"})  # 执行当前业务步骤并推进后续处理
    add_missing_indexes("slc_faqs", {"ix_slc_faqs_faq_code": "(faq_code)"})  # 执行当前业务步骤并推进后续处理
    deduplicate_business_data()  # 执行当前业务步骤并推进后续处理
    add_missing_unique_indexes(  # 执行当前业务步骤并推进后续处理
        "slc_sources",  # 执行当前业务步骤并推进后续处理
        {  # 执行当前业务步骤并推进后续处理
            "uq_slc_sources_tenant_source_code": "(tenant_id, source_code)",  # 执行当前业务步骤并推进后续处理
            "uq_slc_sources_tenant_url": "(tenant_id, url)",  # 执行当前业务步骤并推进后续处理
            "uq_slc_sources_tenant_title_issuer": "(tenant_id, title, issuer)",  # 执行当前业务步骤并推进后续处理
        },  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    add_missing_unique_indexes(  # 执行当前业务步骤并推进后续处理
        "slc_faqs",  # 执行当前业务步骤并推进后续处理
        {  # 执行当前业务步骤并推进后续处理
            "uq_slc_faqs_tenant_faq_code": "(tenant_id, faq_code)",  # 执行当前业务步骤并推进后续处理
            "uq_slc_faqs_tenant_language_question": "(tenant_id, language, question)",  # 执行当前业务步骤并推进后续处理
        },  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理


def deduplicate_business_data() -> None:  # 定义业务处理函数 deduplicate_business_data
    """清理历史重复来源与 FAQ，只保留每组最早记录。"""  # 函数文档字符串，说明 deduplicate_business_data 的职责
    inspector = inspect(engine)  # 更新当前逻辑中的 inspector
    tables = set(inspector.get_table_names())  # 更新当前逻辑中的 tables
    if "slc_sources" not in tables and "slc_faqs" not in tables:  # 根据当前条件决定是否进入对应业务分支
        return  # 结束当前函数并返回空结果

    def parse_json_ids(value) -> list:  # 定义业务处理函数 parse_json_ids
        if not value:  # 根据当前条件决定是否进入对应业务分支
            return []  # 返回当前分支整理好的结果
        if isinstance(value, list):  # 根据当前条件决定是否进入对应业务分支
            return value  # 返回当前分支整理好的结果
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            return json.loads(value)  # 返回当前分支整理好的结果
        except (TypeError, json.JSONDecodeError):  # 捕获异常并执行降级或错误处理逻辑
            return []  # 返回当前分支整理好的结果

    def resolved_source_id(source_id: int, duplicate_map: dict[int, int]) -> int:  # 定义业务处理函数 resolved_source_id
        current = source_id  # 更新当前逻辑中的 current
        visited = set()  # 更新当前逻辑中的 visited
        while current in duplicate_map and current not in visited:  # 在条件满足时持续循环处理
            visited.add(current)  # 执行当前业务步骤并推进后续处理
            current = duplicate_map[current]  # 更新当前逻辑中的 current
        return current  # 返回当前分支整理好的结果

    with engine.begin() as connection:  # 执行当前业务步骤并推进后续处理
        if "slc_sources" in tables:  # 根据当前条件决定是否进入对应业务分支
            source_rows = connection.execute(text("""
                SELECT id, tenant_id, source_code, url, title, issuer
                FROM slc_sources
                ORDER BY id ASC
            """)).mappings().all()
            duplicate_map: dict[int, int] = {}  # 更新当前逻辑中的 duplicate map
            for fields in (("tenant_id", "source_code"), ("tenant_id", "url"), ("tenant_id", "title", "issuer")):  # 遍历当前集合中的每一项并逐个处理
                groups: dict[tuple, list[int]] = {}  # 更新当前逻辑中的 groups
                for row in source_rows:  # 遍历当前集合中的每一项并逐个处理
                    key = tuple((row[field] or "").strip() if isinstance(row[field], str) else row[field] for field in fields)  # 更新当前逻辑中的 key
                    if any(value in (None, "") for value in key):  # 根据当前条件决定是否进入对应业务分支
                        continue  # 跳过当前项，继续处理下一项数据
                    groups.setdefault(key, []).append(row["id"])  # 执行当前业务步骤并推进后续处理
                for ids in groups.values():  # 遍历当前集合中的每一项并逐个处理
                    if len(ids) < 2:  # 根据当前条件决定是否进入对应业务分支
                        continue  # 跳过当前项，继续处理下一项数据
                    keep_id = min(ids)  # 更新当前逻辑中的 keep id
                    for source_id in ids:  # 遍历当前集合中的每一项并逐个处理
                        if source_id != keep_id:  # 根据当前条件决定是否进入对应业务分支
                            duplicate_map[source_id] = keep_id  # 更新当前逻辑中的 duplicate map[source id]

            duplicate_map = {  # 更新当前逻辑中的 duplicate map
                duplicate_id: resolved_source_id(keep_id, duplicate_map)  # 填充返回或配置中的 字段 字段
                for duplicate_id, keep_id in duplicate_map.items()  # 填充返回或配置中的 字段 字段
                if duplicate_id != resolved_source_id(keep_id, duplicate_map)  # 填充返回或配置中的 字段 字段
            }  # 结束 duplicate_map 的定义或组装

            if duplicate_map and "slc_faqs" in tables:  # 根据当前条件决定是否进入对应业务分支
                faq_rows = connection.execute(text("""
                    SELECT id, source_ids
                    FROM slc_faqs
                    WHERE source_ids IS NOT NULL
                """)).mappings().all()
                for row in faq_rows:  # 遍历当前集合中的每一项并逐个处理
                    raw_ids = parse_json_ids(row["source_ids"])  # 更新当前逻辑中的 raw ids
                    normalized_ids = []  # 更新当前逻辑中的 normalized ids
                    changed = False  # 更新当前逻辑中的 changed
                    for raw_id in raw_ids:  # 遍历当前集合中的每一项并逐个处理
                        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
                            source_id = int(raw_id)  # 更新当前逻辑中的 source id
                        except (TypeError, ValueError):  # 捕获异常并执行降级或错误处理逻辑
                            continue  # 跳过当前项，继续处理下一项数据
                        normalized_id = duplicate_map.get(source_id, source_id)  # 更新当前逻辑中的 normalized id
                        changed = changed or normalized_id != source_id  # 更新当前逻辑中的 changed
                        if normalized_id not in normalized_ids:  # 根据当前条件决定是否进入对应业务分支
                            normalized_ids.append(normalized_id)  # 执行当前业务步骤并推进后续处理
                    if changed:  # 根据当前条件决定是否进入对应业务分支
                        connection.execute(  # 执行当前业务步骤并推进后续处理
                            text("UPDATE slc_faqs SET source_ids = :source_ids WHERE id = :id"),  # 执行当前业务步骤并推进后续处理
                            {"source_ids": json.dumps(normalized_ids, ensure_ascii=False), "id": row["id"]},  # 执行当前业务步骤并推进后续处理
                        )  # 执行当前业务步骤并推进后续处理

            if duplicate_map:  # 根据当前条件决定是否进入对应业务分支
                delete_ids = ",".join(str(source_id) for source_id in sorted(duplicate_map))  # 更新当前逻辑中的 delete ids
                connection.execute(text(f"DELETE FROM slc_sources WHERE id IN ({delete_ids})"))  # 执行当前业务步骤并推进后续处理

        if "slc_faqs" in tables:  # 根据当前条件决定是否进入对应业务分支
            connection.execute(text("""
                DELETE f FROM slc_faqs f
                JOIN slc_faqs kept
                  ON f.tenant_id = kept.tenant_id
                 AND f.faq_code = kept.faq_code
                 AND f.id > kept.id
                WHERE f.faq_code IS NOT NULL AND f.faq_code <> ''
            """))
            connection.execute(text("""
                DELETE f FROM slc_faqs f
                JOIN slc_faqs kept
                  ON f.tenant_id = kept.tenant_id
                 AND f.language = kept.language
                 AND f.question = kept.question
                 AND f.id > kept.id
            """))
