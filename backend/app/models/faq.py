"""FAQ 模型。"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class FAQ(Base):
    """FAQ表"""
    __tablename__ = "slc_faqs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "faq_code", name="uq_slc_faqs_tenant_faq_code"),
        UniqueConstraint("tenant_id", "language", "question", name="uq_slc_faqs_tenant_language_question"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    faq_code = Column(String(40), nullable=True, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    region = Column(String(80), default="陕西", nullable=False)
    risk_level = Column(String(20), default="medium", nullable=False)
    keywords = Column(JSON, nullable=True)
    aliases = Column(JSON, nullable=True)
    source_ids = Column(JSON, nullable=True)
    language = Column(String(12), default="zh-CN", nullable=False)
    effective_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="faqs")

    def __repr__(self):
        return f"<FAQ {self.id}: {self.question[:30]}>"
