"""
问答相关Pydantic模型
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    """问答请求"""
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class SourceInfo(BaseModel):
    """来源信息"""
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None


class TaskInfo(BaseModel):
    """办事路径信息"""
    title: str
    steps: List[str]
    url: Optional[str] = None


class ChatResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: Optional[List[SourceInfo]] = None
    related_tasks: Optional[List[TaskInfo]] = None
    response_time: int
    conversation_id: Optional[str] = None


class HistoryItem(BaseModel):
    """历史记录项"""
    id: int
    question: str
    answer: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    """历史记录响应"""
    total: int
    list: List[HistoryItem]