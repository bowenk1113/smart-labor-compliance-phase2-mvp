"""租户模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class Tenant(Base):  # 定义业务类 Tenant
    """企业租户。"""  # 类文档字符串，概述 Tenant 的用途

    __tablename__ = "slc_tenants"  # 更新当前逻辑中的   tablename  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    code = Column(String(64), unique=True, nullable=False, index=True)  # 更新当前逻辑中的 code
    name = Column(String(120), nullable=False)  # 更新当前逻辑中的 名称
    industry = Column(String(80), nullable=True)  # 更新当前逻辑中的 industry
    region = Column(String(80), default="陕西", nullable=False)  # 组合省市信息，作为外部问答服务的地域上下文
    contact_name = Column(String(80), nullable=True)  # 更新当前逻辑中的 contact name
    contact_email = Column(String(120), nullable=True)  # 更新当前逻辑中的 contact email
    contact_phone = Column(String(40), nullable=True)  # 更新当前逻辑中的 contact phone
    status = Column(String(20), default="active", nullable=False)  # 更新当前逻辑中的 状态
    data_scope = Column(String(30), default="tenant", nullable=False)  # 更新当前逻辑中的 data scope
    dify_api_key = Column(Text, nullable=True)  # 更新当前逻辑中的 dify api key
    dify_app_id = Column(String(120), nullable=True)  # 更新当前逻辑中的 dify app id
    ragflow_dataset_id = Column(String(120), nullable=True)  # 更新当前逻辑中的 ragflow dataset id
    notes = Column(Text, nullable=True)  # 更新当前逻辑中的 notes
    is_demo = Column(Boolean, default=False, nullable=False)  # 更新当前逻辑中的 is demo
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)  # 更新当前逻辑中的 更新时间

    admins = relationship("Admin", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 admins
    chat_logs = relationship("ChatLog", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 chat logs
    faqs = relationship("FAQ", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 faqs
    sources = relationship("Source", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 来源列表
    knowledge_packages = relationship("KnowledgePackage", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 knowledge packages
    feedbacks = relationship("Feedback", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 feedbacks
    test_questions = relationship("TestQuestion", back_populates="tenant", cascade="all, delete-orphan")  # 更新当前逻辑中的 test questions

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<Tenant {self.id}: {self.code}>"  # 返回当前分支整理好的结果
