"""反馈记录模型。"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Feedback(Base):
    """反馈记录表"""
    __tablename__ = "slc_feedbacks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("slc_chat_logs.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(64), nullable=True, index=True)
    is_helpful = Column(Boolean, nullable=True)
    remark = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="feedbacks")
    chat_log = relationship("ChatLog")

    def __repr__(self):
        return f"<Feedback {self.id}: status={self.status}>"
