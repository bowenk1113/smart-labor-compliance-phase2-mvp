"""问答相关 Pydantic 模型。"""  # 模块文档字符串，概述当前文件职责
from typing import Optional, List  # 导入当前模块运行所依赖的工具或类型
from pydantic import BaseModel, Field  # 导入 Pydantic 数据校验或配置能力
from datetime import datetime  # 导入当前模块运行所依赖的工具或类型


class ChatRequest(BaseModel):  # 定义业务类 ChatRequest
    """问答请求"""  # 类文档字符串，概述 ChatRequest 的用途
    question: str = Field(min_length=1, max_length=3000)  # 更新当前逻辑中的 问题内容
    scenario_id: Optional[str] = None  # 更新当前逻辑中的 scenario id
    generation_id: Optional[str] = None  # 更新当前逻辑中的 generation id
    session_id: Optional[str] = None  # 更新当前逻辑中的 会话 ID
    user_id: Optional[str] = None  # 更新当前逻辑中的 用户 ID
    tenant_code: Optional[str] = None  # 更新当前逻辑中的 tenant code
    language: str = "zh-CN"  # 更新当前逻辑中的 语言代码
    conversation_id: Optional[str] = None  # 更新当前逻辑中的 会话 ID
    user_role: str = "employee"  # 更新当前逻辑中的 用户角色
    province: str = "陕西省"  # 更新当前逻辑中的 省份
    city: str = "西安市"  # 更新当前逻辑中的 城市


class ChatStopRequest(BaseModel):  # 定义业务类 ChatStopRequest
    """停止生成请求"""  # 类文档字符串，概述 ChatStopRequest 的用途

    generation_id: str = Field(min_length=1, max_length=120)  # 更新当前逻辑中的 generation id
    user_id: Optional[str] = None  # 更新当前逻辑中的 用户 ID
    tenant_code: Optional[str] = None  # 更新当前逻辑中的 tenant code


class SourceInfo(BaseModel):  # 定义业务类 SourceInfo
    """来源信息"""  # 类文档字符串，概述 SourceInfo 的用途
    title: str  # 执行当前业务步骤并推进后续处理
    url: Optional[str] = None  # 更新当前逻辑中的 链接地址
    snippet: Optional[str] = None  # 更新当前逻辑中的 snippet


class TaskInfo(BaseModel):  # 定义业务类 TaskInfo
    """办事路径信息"""  # 类文档字符串，概述 TaskInfo 的用途
    title: str  # 执行当前业务步骤并推进后续处理
    steps: List[str]  # 执行当前业务步骤并推进后续处理
    url: Optional[str] = None  # 更新当前逻辑中的 链接地址


class ChatResponse(BaseModel):  # 定义业务类 ChatResponse
    """问答响应"""  # 类文档字符串，概述 ChatResponse 的用途
    answer: str  # 执行当前业务步骤并推进后续处理
    sources: Optional[List[SourceInfo]] = None  # 更新当前逻辑中的 来源列表
    related_tasks: Optional[List[TaskInfo]] = None  # 更新当前逻辑中的 关联任务列表
    response_time: int  # 执行当前业务步骤并推进后续处理
    conversation_id: Optional[str] = None  # 更新当前逻辑中的 会话 ID
    question_id: Optional[int] = None  # 更新当前逻辑中的 关联问答 ID
    provider: str = "local_faq"  # 更新当前逻辑中的 服务提供方
    route: str = "rag"  # 更新当前逻辑中的 route
    answer_source: str = "hybrid_retrieval_template"  # 更新当前逻辑中的 answer source
    risk_level: str = "medium"  # 更新当前逻辑中的 风险等级
    suggestions: List[str] = Field(default_factory=list)  # 更新当前逻辑中的 建议列表
    disclaimer: Optional[str] = None  # 更新当前逻辑中的 免责声明
    retrieval: dict = Field(default_factory=dict)  # 更新当前逻辑中的 retrieval


class HistoryItem(BaseModel):  # 定义业务类 HistoryItem
    """历史记录项"""  # 类文档字符串，概述 HistoryItem 的用途
    id: int  # 执行当前业务步骤并推进后续处理
    tenant_id: int  # 执行当前业务步骤并推进后续处理
    user_id: Optional[str] = None  # 更新当前逻辑中的 用户 ID
    session_id: Optional[str] = None  # 更新当前逻辑中的 会话 ID
    conversation_id: Optional[str] = None  # 更新当前逻辑中的 会话 ID
    language: str = "zh-CN"  # 更新当前逻辑中的 语言代码
    question: str  # 执行当前业务步骤并推进后续处理
    answer: Optional[str] = None  # 更新当前逻辑中的 回答内容
    sources: Optional[List[dict]] = None  # 更新当前逻辑中的 来源列表
    related_tasks: Optional[List[dict]] = None  # 更新当前逻辑中的 关联任务列表
    provider: str  # 执行当前业务步骤并推进后续处理
    risk_level: str = "medium"  # 更新当前逻辑中的 风险等级
    response_time: Optional[int]  # 执行当前业务步骤并推进后续处理
    status: str  # 执行当前业务步骤并推进后续处理
    created_at: datetime  # 执行当前业务步骤并推进后续处理
    
    class Config:  # 定义业务类 Config
        from_attributes = True  # 更新当前逻辑中的 from attributes


class HistoryResponse(BaseModel):  # 定义业务类 HistoryResponse
    """历史记录响应"""  # 类文档字符串，概述 HistoryResponse 的用途
    total: int  # 执行当前业务步骤并推进后续处理
    page: int = 1  # 更新当前逻辑中的 page
    page_size: int = 20  # 更新当前逻辑中的 page size
    list: List[HistoryItem]  # 执行当前业务步骤并推进后续处理
