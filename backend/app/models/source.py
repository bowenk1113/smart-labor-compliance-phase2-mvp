"""来源目录模型。"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Source(Base):
    """来源目录表"""
    __tablename__ = "slc_sources"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_code", name="uq_slc_sources_tenant_source_code"),
        UniqueConstraint("tenant_id", "url", name="uq_slc_sources_tenant_url"),
        UniqueConstraint("tenant_id", "title", "issuer", name="uq_slc_sources_tenant_title_issuer"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_code = Column(String(40), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    url = Column(String(500), nullable=True)
    doc_type = Column(String(20), nullable=True)
    issuer = Column(String(120), default="", nullable=False)
    region = Column(String(50), nullable=True)
    publish_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=True)
    validity_status = Column(String(30), default="有效", nullable=False)
    review_status = Column(String(30), default="待人工复核", nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(80), nullable=True)
    captured_at = Column(Date, nullable=True)
    owner = Column(String(80), nullable=True)
    local_file = Column(String(500), nullable=True)
    note = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="sources")

    def __repr__(self):
        return f"<Source {self.id}: {self.title}>"
