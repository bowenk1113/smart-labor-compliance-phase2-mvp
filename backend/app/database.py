"""
数据库连接配置 - MySQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import pymysql


class Settings(BaseSettings):
    """数据库配置"""
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "root1234"
    db_name: str = "employment"

    model_config = {"extra": "allow", "env_file": ".env"}


# 加载配置
settings = Settings()


def create_database_if_not_exists():
    """如果数据库不存在则创建"""
    try:
        # 先连接到 MySQL 服务器（不指定数据库）
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # 创建数据库（如果不存在）
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        connection.commit()
        connection.close()
        print(f"数据库 {settings.db_name} 检查/创建完成")
    except Exception as e:
        print(f"创建数据库失败: {e}")


# 先确保数据库存在
create_database_if_not_exists()

# 数据库连接配置 - 使用 MySQL
DATABASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    from app.models import chat_log, feedback, faq, source, knowledge_package, admin
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")