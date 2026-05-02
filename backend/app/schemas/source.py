"""来源相关 Pydantic 模型。"""
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime


def _has_text(value: Optional[str]) -> bool:
    return bool((value or "").strip())


class SourceCreate(BaseModel):
    """来源创建请求"""
    source_code: Optional[str] = None
    title: str = Field(min_length=2, max_length=200)
    url: Optional[str] = None
    doc_type: Optional[str] = None
    issuer: Optional[str] = None
    region: Optional[str] = None
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    validity_status: str = "有效"
    review_status: str = "待人工复核"
    captured_at: Optional[date] = None
    owner: Optional[str] = None
    local_file: Optional[str] = None
    note: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_source_path(self):
        if not _has_text(self.url) and not _has_text(self.local_file):
            raise ValueError("外部链接与上传文件必须至少填写一个")
        return self


class SourceUpdate(BaseModel):
    """来源更新请求"""
    source_code: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    url: Optional[str] = None
    doc_type: Optional[str] = None
    issuer: Optional[str] = None
    region: Optional[str] = None
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    validity_status: Optional[str] = None
    review_status: Optional[str] = None
    captured_at: Optional[date] = None
    owner: Optional[str] = None
    local_file: Optional[str] = None
    note: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_source_path(self):
        if self.url is not None and self.local_file is not None and not _has_text(self.url) and not _has_text(self.local_file):
            raise ValueError("外部链接与上传文件必须至少填写一个")
        return self


class SourceResponse(BaseModel):
    """来源响应"""
    id: int
    tenant_id: int
    source_code: Optional[str]
    title: str
    url: Optional[str]
    doc_type: Optional[str]
    issuer: Optional[str]
    region: Optional[str]
    publish_date: Optional[date]
    effective_date: Optional[date]
    validity_status: str
    review_status: str
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
    captured_at: Optional[date]
    owner: Optional[str]
    local_file: Optional[str]
    note: Optional[str]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
