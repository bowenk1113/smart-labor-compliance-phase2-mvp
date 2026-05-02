"""FAQ 相关 Pydantic 模型。"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date, datetime


class FAQCreate(BaseModel):
    """FAQ创建请求"""
    faq_code: Optional[str] = None
    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2)
    category: Optional[str] = None
    region: str = "陕西"
    risk_level: str = "medium"
    keywords: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    source_ids: Optional[List[int]] = None
    language: str = "zh-CN"
    effective_date: Optional[date] = None


class FAQUpdate(BaseModel):
    """FAQ更新请求"""
    faq_code: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    risk_level: Optional[str] = None
    keywords: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    source_ids: Optional[List[int]] = None
    language: Optional[str] = None
    effective_date: Optional[date] = None


class FAQResponse(BaseModel):
    """FAQ响应"""
    id: int
    tenant_id: int
    faq_code: Optional[str]
    question: str
    answer: str
    category: Optional[str]
    region: str
    risk_level: str
    keywords: Optional[List[str]]
    aliases: Optional[List[str]]
    source_ids: Optional[List[int]]
    language: str
    effective_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
