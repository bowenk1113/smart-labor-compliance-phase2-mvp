"""管理员模型。"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Admin(Base):
    """管理员表"""
    __tablename__ = "slc_admins"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_slc_admin_tenant_username"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    username = Column(String(50), nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="admin", nullable=False)
    display_name = Column(String(80), nullable=True)
    email = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="admins")

    def __repr__(self):
        return f"<Admin {self.id}: {self.username}>"
