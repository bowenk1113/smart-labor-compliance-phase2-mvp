"""来源目录模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class Source(Base):  # 定义业务类 Source
    """来源目录表"""  # 类文档字符串，概述 Source 的用途
    __tablename__ = "slc_sources"  # 更新当前逻辑中的   tablename  
    __table_args__ = (  # 更新当前逻辑中的   table args  
        UniqueConstraint("tenant_id", "source_code", name="uq_slc_sources_tenant_source_code"),  # 执行当前业务步骤并推进后续处理
        UniqueConstraint("tenant_id", "url", name="uq_slc_sources_tenant_url"),  # 执行当前业务步骤并推进后续处理
        UniqueConstraint("tenant_id", "title", "issuer", name="uq_slc_sources_tenant_title_issuer"),  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)  # 更新当前逻辑中的 租户 ID
    source_code = Column(String(40), nullable=True, index=True)  # 更新当前逻辑中的 资料编码
    title = Column(String(200), nullable=False)  # 更新当前逻辑中的 标题
    url = Column(String(500), nullable=True)  # 更新当前逻辑中的 链接地址
    doc_type = Column(String(20), nullable=True)  # 更新当前逻辑中的 doc type
    issuer = Column(String(120), default="", nullable=False)  # 更新当前逻辑中的 issuer
    region = Column(String(50), nullable=True)  # 组合省市信息，作为外部问答服务的地域上下文
    publish_date = Column(Date, nullable=True)  # 更新当前逻辑中的 publish date
    effective_date = Column(Date, nullable=True)  # 更新当前逻辑中的 effective date
    validity_status = Column(String(30), default="有效", nullable=False)  # 更新当前逻辑中的 validity status
    review_status = Column(String(30), default="待人工复核", nullable=False)  # 更新当前逻辑中的 review status
    reviewed_at = Column(DateTime, nullable=True)  # 更新当前逻辑中的 reviewed at
    reviewed_by = Column(String(80), nullable=True)  # 更新当前逻辑中的 reviewed by
    captured_at = Column(Date, nullable=True)  # 更新当前逻辑中的 captured at
    owner = Column(String(80), nullable=True)  # 更新当前逻辑中的 owner
    local_file = Column(String(500), nullable=True)  # 更新当前逻辑中的 local file
    note = Column(Text, nullable=True)  # 更新当前逻辑中的 note
    description = Column(Text, nullable=True)  # 更新当前逻辑中的 说明描述
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间

    tenant = relationship("Tenant", back_populates="sources")  # 保存当前请求实际使用的租户对象

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<Source {self.id}: {self.title}>"  # 返回当前分支整理好的结果
