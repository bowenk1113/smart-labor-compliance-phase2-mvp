"""
问答记录模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class ChatLog(Base):
    """问答记录表"""
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    related_tasks = Column(JSON, nullable=True)
    response_time = Column(Integer, nullable=True)
    status = Column(String(20), default="success")
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ChatLog {self.id}: {self.question[:30]}>"