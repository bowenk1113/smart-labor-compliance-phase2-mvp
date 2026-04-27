"""
知识包模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class KnowledgePackage(Base):
    """知识包表"""
    __tablename__ = "knowledge_packages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    region = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<KnowledgePackage {self.id}: {self.name}>"