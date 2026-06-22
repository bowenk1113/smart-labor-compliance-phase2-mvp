"""知识包模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class KnowledgePackage(Base):  # 定义业务类 KnowledgePackage
    """知识包表"""  # 类文档字符串，概述 KnowledgePackage 的用途
    __tablename__ = "slc_knowledge_packages"  # 更新当前逻辑中的   tablename  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)  # 更新当前逻辑中的 租户 ID
    name = Column(String(100), nullable=False)  # 更新当前逻辑中的 名称
    region = Column(String(50), nullable=True)  # 组合省市信息，作为外部问答服务的地域上下文
    version = Column(String(40), default="v1.0", nullable=False)  # 更新当前逻辑中的 版本
    description = Column(Text, nullable=True)  # 更新当前逻辑中的 说明描述
    categories = Column(JSON, nullable=True)  # 更新当前逻辑中的 categories
    dify_dataset_id = Column(String(120), nullable=True)  # 更新当前逻辑中的 dify dataset id
    ragflow_dataset_id = Column(String(120), nullable=True)  # 更新当前逻辑中的 ragflow dataset id
    status = Column(String(20), default="active", nullable=False)  # 更新当前逻辑中的 状态
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)  # 更新当前逻辑中的 更新时间

    tenant = relationship("Tenant", back_populates="knowledge_packages")  # 保存当前请求实际使用的租户对象

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<KnowledgePackage {self.id}: {self.name}>"  # 返回当前分支整理好的结果
