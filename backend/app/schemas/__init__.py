"""
Pydantic模型包
"""
from app.schemas.chat import ChatRequest, ChatResponse, SourceInfo, TaskInfo, HistoryItem, HistoryResponse
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate, FeedbackResponse
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse
from app.schemas.admin import AdminLogin, AdminToken, AdminInfo, StatisticsResponse

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "SourceInfo",
    "TaskInfo",
    "HistoryItem",
    "HistoryResponse",
    "FeedbackCreate",
    "FeedbackUpdate",
    "FeedbackResponse",
    "FAQCreate",
    "FAQUpdate",
    "FAQResponse",
    "SourceCreate",
    "SourceUpdate",
    "SourceResponse",
    "AdminLogin",
    "AdminToken",
    "AdminInfo",
    "StatisticsResponse"
]