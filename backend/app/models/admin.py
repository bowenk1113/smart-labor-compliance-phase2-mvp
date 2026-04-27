"""
管理员模型
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Admin(Base):
    """管理员表"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="admin", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Admin {self.id}: {self.username}>"