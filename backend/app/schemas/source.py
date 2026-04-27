"""
来源相关Pydantic模型
"""
from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime


class SourceCreate(BaseModel):
    """来源创建请求"""
    title: str
    url: Optional[str] = None
    doc_type: Optional[str] = None
    region: Optional[str] = None
    publish_date: Optional[date] = None
    description: Optional[str] = None


class SourceUpdate(BaseModel):
    """来源更新请求"""
    title: Optional[str] = None
    url: Optional[str] = None
    doc_type: Optional[str] = None
    region: Optional[str] = None
    publish_date: Optional[date] = None
    description: Optional[str] = None


class SourceResponse(BaseModel):
    """来源响应"""
    id: int
    title: str
    url: Optional[str]
    doc_type: Optional[str]
    region: Optional[str]
    publish_date: Optional[date]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True