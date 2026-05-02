"""反馈相关 Pydantic 模型。"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FeedbackCreate(BaseModel):
    """反馈创建请求"""
    question_id: Optional[int] = None
    tenant_code: Optional[str] = None
    user_id: Optional[str] = None
    is_helpful: Optional[bool] = None
    remark: Optional[str] = None


class FeedbackUpdate(BaseModel):
    """反馈更新请求"""
    status: Optional[str] = None


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: int
    tenant_id: int
    question_id: Optional[int]
    user_id: Optional[str]
    is_helpful: Optional[bool]
    remark: Optional[str]
    status: str
    created_at: datetime
    question: Optional[str] = None
    
    class Config:
        from_attributes = True
