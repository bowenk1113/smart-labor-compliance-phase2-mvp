"""管理员模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class Admin(Base):  # 定义业务类 Admin
    """管理员表"""  # 类文档字符串，概述 Admin 的用途
    __tablename__ = "slc_admins"  # 更新当前逻辑中的   tablename  
    __table_args__ = (  # 更新当前逻辑中的   table args  
        UniqueConstraint("tenant_id", "username", name="uq_slc_admin_tenant_username"),  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # 更新当前逻辑中的 租户 ID
    username = Column(String(50), nullable=False, index=True)  # 更新当前逻辑中的 username
    password_hash = Column(String(200), nullable=False)  # 执行当前控制流分支
    role = Column(String(20), default="admin", nullable=False)  # 更新当前逻辑中的 role
    display_name = Column(String(80), nullable=True)  # 更新当前逻辑中的 display name
    email = Column(String(120), nullable=True)  # 更新当前逻辑中的 email
    is_active = Column(Boolean, default=True, nullable=False)  # 更新当前逻辑中的 is active
    last_login_at = Column(DateTime, nullable=True)  # 更新当前逻辑中的 last login at
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)  # 更新当前逻辑中的 更新时间

    tenant = relationship("Tenant", back_populates="admins")  # 保存当前请求实际使用的租户对象

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<Admin {self.id}: {self.username}>"  # 返回当前分支整理好的结果
