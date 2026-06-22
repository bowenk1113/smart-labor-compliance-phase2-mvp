"""反馈相关 Pydantic 模型。"""  # 模块文档字符串，概述当前文件职责
from typing import Optional  # 导入当前模块运行所依赖的工具或类型
from pydantic import BaseModel  # 导入 Pydantic 数据校验或配置能力
from datetime import datetime  # 导入当前模块运行所依赖的工具或类型


class FeedbackCreate(BaseModel):  # 定义业务类 FeedbackCreate
    """反馈创建请求"""  # 类文档字符串，概述 FeedbackCreate 的用途
    question_id: Optional[int] = None  # 更新当前逻辑中的 关联问答 ID
    tenant_code: Optional[str] = None  # 更新当前逻辑中的 tenant code
    user_id: Optional[str] = None  # 更新当前逻辑中的 用户 ID
    is_helpful: Optional[bool] = None  # 更新当前逻辑中的 是否有帮助
    remark: Optional[str] = None  # 更新当前逻辑中的 备注


class FeedbackUpdate(BaseModel):  # 定义业务类 FeedbackUpdate
    """反馈更新请求"""  # 类文档字符串，概述 FeedbackUpdate 的用途
    status: Optional[str] = None  # 更新当前逻辑中的 状态


class FeedbackResponse(BaseModel):  # 定义业务类 FeedbackResponse
    """反馈响应"""  # 类文档字符串，概述 FeedbackResponse 的用途
    id: int  # 执行当前业务步骤并推进后续处理
    tenant_id: int  # 执行当前业务步骤并推进后续处理
    question_id: Optional[int]  # 执行当前业务步骤并推进后续处理
    user_id: Optional[str]  # 执行当前业务步骤并推进后续处理
    is_helpful: Optional[bool]  # 执行当前业务步骤并推进后续处理
    remark: Optional[str]  # 执行当前业务步骤并推进后续处理
    status: str  # 执行当前业务步骤并推进后续处理
    created_at: datetime  # 执行当前业务步骤并推进后续处理
    question: Optional[str] = None  # 更新当前逻辑中的 问题内容
    
    class Config:  # 定义业务类 Config
        from_attributes = True  # 更新当前逻辑中的 from attributes
