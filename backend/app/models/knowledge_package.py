"""知识包模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class KnowledgePackage(Base):
    """知识包表"""
    __tablename__ = "slc_knowledge_packages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    region = Column(String(50), nullable=True)
    version = Column(String(40), default="v1.0", nullable=False)
    description = Column(Text, nullable=True)
    categories = Column(JSON, nullable=True)
    dify_dataset_id = Column(String(120), nullable=True)
    ragflow_dataset_id = Column(String(120), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="knowledge_packages")

    def __repr__(self):
        return f"<KnowledgePackage {self.id}: {self.name}>"
