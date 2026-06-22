"""FAQ 模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class FAQ(Base):  # 定义业务类 FAQ
    """FAQ表"""  # 类文档字符串，概述 FAQ 的用途
    __tablename__ = "slc_faqs"  # 更新当前逻辑中的   tablename  
    __table_args__ = (  # 更新当前逻辑中的   table args  
        UniqueConstraint("tenant_id", "faq_code", name="uq_slc_faqs_tenant_faq_code"),  # 执行当前业务步骤并推进后续处理
        UniqueConstraint("tenant_id", "language", "question", name="uq_slc_faqs_tenant_language_question"),  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)  # 更新当前逻辑中的 租户 ID
    faq_code = Column(String(40), nullable=True, index=True)  # 更新当前逻辑中的 FAQ 编码
    question = Column(String(500), nullable=False)  # 清洗并保存用户提交的问题文本
    answer = Column(Text, nullable=False)  # 更新当前逻辑中的 回答内容
    category = Column(String(50), nullable=True)  # 更新当前逻辑中的 分类
    region = Column(String(80), default="陕西", nullable=False)  # 组合省市信息，作为外部问答服务的地域上下文
    risk_level = Column(String(20), default="medium", nullable=False)  # 更新当前逻辑中的 风险等级
    keywords = Column(JSON, nullable=True)  # 更新当前逻辑中的 关键字
    aliases = Column(JSON, nullable=True)  # 更新当前逻辑中的 aliases
    source_ids = Column(JSON, nullable=True)  # 更新当前逻辑中的 source ids
    language = Column(String(12), default="zh-CN", nullable=False)  # 更新当前逻辑中的 语言代码
    effective_date = Column(Date, nullable=True)  # 更新当前逻辑中的 effective date
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)  # 更新当前逻辑中的 更新时间

    tenant = relationship("Tenant", back_populates="faqs")  # 保存当前请求实际使用的租户对象

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<FAQ {self.id}: {self.question[:30]}>"  # 返回当前分支整理好的结果
