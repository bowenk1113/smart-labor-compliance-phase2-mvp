"""
管理员相关Pydantic模型
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class AdminLogin(BaseModel):
    """管理员登录请求"""
    username: str
    password: str


class AdminToken(BaseModel):
    """管理员令牌响应"""
    access_token: str
    token_type: str = "bearer"
    admin_id: int
    username: str
    role: str


class AdminInfo(BaseModel):
    """管理员信息"""
    id: int
    username: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class StatisticsResponse(BaseModel):
    """统计数据响应"""
    total_questions: int
    today_questions: int
    total_feedbacks: int
    pending_feedbacks: int
    total_faqs: int
    total_sources: int