"""
反馈记录模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Feedback(Base):
    """反馈记录表"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(Integer, nullable=True)
    user_id = Column(String(64), nullable=True, index=True)
    is_helpful = Column(Boolean, nullable=True)
    remark = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Feedback {self.id}: status={self.status}>"