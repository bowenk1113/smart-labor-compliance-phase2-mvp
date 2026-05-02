"""验收测试问题模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TestQuestion(Base):
    """用于演示和回归验证的测试问题。"""

    __tablename__ = "slc_test_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    expected_points = Column(JSON, nullable=True)
    category = Column(String(60), nullable=True)
    region = Column(String(80), default="陕西", nullable=False)
    difficulty = Column(String(20), default="normal", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="test_questions")

    def __repr__(self):
        return f"<TestQuestion {self.id}: {self.question[:30]}>"
