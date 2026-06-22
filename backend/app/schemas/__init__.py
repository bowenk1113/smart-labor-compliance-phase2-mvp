"""
Pydantic模型包
"""
from app.schemas.chat import ChatRequest, ChatResponse, SourceInfo, TaskInfo, HistoryItem, HistoryResponse  # 导入接口请求体与响应体模型
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate, FeedbackResponse  # 导入接口请求体与响应体模型
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse  # 导入接口请求体与响应体模型
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse  # 导入接口请求体与响应体模型
from app.schemas.admin import (  # 导入接口请求体与响应体模型
    AdminLogin,  # 执行当前业务步骤并推进后续处理
    AdminToken,  # 执行当前业务步骤并推进后续处理
    AdminInfo,  # 执行当前业务步骤并推进后续处理
    StatisticsResponse,  # 执行当前业务步骤并推进后续处理
    TenantCreate,  # 执行当前业务步骤并推进后续处理
    TenantUpdate,  # 执行当前业务步骤并推进后续处理
    TenantResponse,  # 执行当前业务步骤并推进后续处理
)  # 执行当前业务步骤并推进后续处理

__all__ = [  # 更新当前逻辑中的   all  
    "ChatRequest",  # 补充列表中的 ChatRequest 项
    "ChatResponse",  # 补充列表中的 ChatResponse 项
    "SourceInfo",  # 补充列表中的 SourceInfo 项
    "TaskInfo",  # 补充列表中的 TaskInfo 项
    "HistoryItem",  # 补充列表中的 HistoryItem 项
    "HistoryResponse",  # 补充列表中的 HistoryResponse 项
    "FeedbackCreate",  # 补充列表中的 FeedbackCreate 项
    "FeedbackUpdate",  # 补充列表中的 FeedbackUpdate 项
    "FeedbackResponse",  # 补充列表中的 FeedbackResponse 项
    "FAQCreate",  # 补充列表中的 FAQCreate 项
    "FAQUpdate",  # 补充列表中的 FAQUpdate 项
    "FAQResponse",  # 补充列表中的 FAQResponse 项
    "SourceCreate",  # 补充列表中的 SourceCreate 项
    "SourceUpdate",  # 补充列表中的 SourceUpdate 项
    "SourceResponse",  # 补充列表中的 SourceResponse 项
    "AdminLogin",  # 补充列表中的 AdminLogin 项
    "AdminToken",  # 补充列表中的 AdminToken 项
    "AdminInfo",  # 补充列表中的 AdminInfo 项
    "StatisticsResponse",  # 补充列表中的 StatisticsResponse 项
    "TenantCreate",  # 补充列表中的 TenantCreate 项
    "TenantUpdate",  # 补充列表中的 TenantUpdate 项
    "TenantResponse",  # 补充列表中的 TenantResponse 项
]  # 结束 __all__ 的定义或组装
