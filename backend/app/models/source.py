"""
来源目录模型
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Source(Base):
    """来源目录表"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    url = Column(String(500), nullable=True)
    doc_type = Column(String(20), nullable=True)
    region = Column(String(50), nullable=True)
    publish_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Source {self.id}: {self.title}>"