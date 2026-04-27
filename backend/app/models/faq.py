"""
FAQ模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class FAQ(Base):
    """FAQ表"""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    keywords = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<FAQ {self.id}: {self.question[:30]}>"