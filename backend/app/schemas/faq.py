"""
FAQ相关Pydantic模型
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class FAQCreate(BaseModel):
    """FAQ创建请求"""
    question: str
    answer: str
    category: Optional[str] = None
    keywords: Optional[List[str]] = None


class FAQUpdate(BaseModel):
    """FAQ更新请求"""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None


class FAQResponse(BaseModel):
    """FAQ响应"""
    id: int
    question: str
    answer: str
    category: Optional[str]
    keywords: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True