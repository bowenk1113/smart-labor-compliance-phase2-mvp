"""管理员与租户相关 Pydantic 模型。"""  # 模块文档字符串，概述当前文件职责
from typing import Optional  # 导入当前模块运行所依赖的工具或类型

from pydantic import BaseModel, Field  # 导入 Pydantic 数据校验或配置能力
from datetime import datetime  # 导入当前模块运行所依赖的工具或类型


class AdminLogin(BaseModel):  # 定义业务类 AdminLogin
    """管理员登录请求"""  # 类文档字符串，概述 AdminLogin 的用途
    username: str  # 执行当前业务步骤并推进后续处理
    password: str  # 执行当前控制流分支
    tenant_code: Optional[str] = None  # 更新当前逻辑中的 tenant code


class AdminCreate(BaseModel):  # 定义业务类 AdminCreate
    """管理员创建请求"""  # 类文档字符串，概述 AdminCreate 的用途
    username: str = Field(min_length=2, max_length=50)  # 更新当前逻辑中的 username
    password: str = Field(min_length=8, max_length=128)  # 执行当前控制流分支
    role: str = "operator"  # 更新当前逻辑中的 role
    display_name: Optional[str] = None  # 更新当前逻辑中的 display name
    email: Optional[str] = None  # 更新当前逻辑中的 email
    tenant_id: Optional[int] = None  # 更新当前逻辑中的 租户 ID


class AdminUpdate(BaseModel):  # 定义业务类 AdminUpdate
    """管理员更新请求"""  # 类文档字符串，概述 AdminUpdate 的用途
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)  # 执行当前控制流分支
    role: Optional[str] = None  # 更新当前逻辑中的 role
    display_name: Optional[str] = None  # 更新当前逻辑中的 display name
    email: Optional[str] = None  # 更新当前逻辑中的 email
    is_active: Optional[bool] = None  # 更新当前逻辑中的 is active


class AdminToken(BaseModel):  # 定义业务类 AdminToken
    """管理员令牌响应"""  # 类文档字符串，概述 AdminToken 的用途
    access_token: str  # 执行当前业务步骤并推进后续处理
    token_type: str = "bearer"  # 更新当前逻辑中的 token type
    admin_id: int  # 执行当前业务步骤并推进后续处理
    username: str  # 执行当前业务步骤并推进后续处理
    role: str  # 执行当前业务步骤并推进后续处理
    role_label: str  # 执行当前业务步骤并推进后续处理
    permissions: list[str]  # 执行当前业务步骤并推进后续处理
    tenant_id: Optional[int]  # 执行当前业务步骤并推进后续处理
    tenant_code: Optional[str]  # 执行当前业务步骤并推进后续处理
    tenant_name: Optional[str]  # 执行当前业务步骤并推进后续处理


class AdminInfo(BaseModel):  # 定义业务类 AdminInfo
    """管理员信息"""  # 类文档字符串，概述 AdminInfo 的用途
    id: int  # 执行当前业务步骤并推进后续处理
    tenant_id: Optional[int]  # 执行当前业务步骤并推进后续处理
    username: str  # 执行当前业务步骤并推进后续处理
    role: str  # 执行当前业务步骤并推进后续处理
    display_name: Optional[str] = None  # 更新当前逻辑中的 display name
    email: Optional[str] = None  # 更新当前逻辑中的 email
    is_active: bool  # 执行当前业务步骤并推进后续处理
    created_at: datetime  # 执行当前业务步骤并推进后续处理
    
    class Config:  # 定义业务类 Config
        from_attributes = True  # 更新当前逻辑中的 from attributes


class StatisticsResponse(BaseModel):  # 定义业务类 StatisticsResponse
    """统计数据响应"""  # 类文档字符串，概述 StatisticsResponse 的用途
    total_questions: int  # 执行当前业务步骤并推进后续处理
    today_questions: int  # 执行当前业务步骤并推进后续处理
    total_feedbacks: int  # 执行当前业务步骤并推进后续处理
    pending_feedbacks: int  # 执行当前业务步骤并推进后续处理
    total_faqs: int  # 执行当前业务步骤并推进后续处理
    total_sources: int  # 执行当前业务步骤并推进后续处理
    total_tenants: int  # 执行当前业务步骤并推进后续处理
    helpful_rate: int  # 执行当前业务步骤并推进后续处理
    avg_response_time: int  # 执行当前业务步骤并推进后续处理
    top_questions: list[dict]  # 执行当前业务步骤并推进后续处理


class TenantCreate(BaseModel):  # 定义业务类 TenantCreate
    """租户创建请求。"""  # 类文档字符串，概述 TenantCreate 的用途

    code: str = Field(min_length=2, max_length=64)  # 更新当前逻辑中的 code
    name: str = Field(min_length=2, max_length=120)  # 更新当前逻辑中的 名称
    industry: Optional[str] = None  # 更新当前逻辑中的 industry
    region: str = "陕西"  # 更新当前逻辑中的 地区
    contact_name: Optional[str] = None  # 更新当前逻辑中的 contact name
    contact_email: Optional[str] = None  # 更新当前逻辑中的 contact email
    contact_phone: Optional[str] = None  # 更新当前逻辑中的 contact phone
    status: str = "active"  # 更新当前逻辑中的 状态
    notes: Optional[str] = None  # 更新当前逻辑中的 notes
    admin_username: Optional[str] = Field(default=None, min_length=2, max_length=50)  # 更新当前逻辑中的 admin username
    admin_password: Optional[str] = Field(default=None, min_length=8, max_length=128)  # 更新当前逻辑中的 admin password


class TenantUpdate(BaseModel):  # 定义业务类 TenantUpdate
    """租户更新请求。"""  # 类文档字符串，概述 TenantUpdate 的用途

    name: Optional[str] = None  # 更新当前逻辑中的 名称
    industry: Optional[str] = None  # 更新当前逻辑中的 industry
    region: Optional[str] = None  # 更新当前逻辑中的 地区
    contact_name: Optional[str] = None  # 更新当前逻辑中的 contact name
    contact_email: Optional[str] = None  # 更新当前逻辑中的 contact email
    contact_phone: Optional[str] = None  # 更新当前逻辑中的 contact phone
    status: Optional[str] = None  # 更新当前逻辑中的 状态
    notes: Optional[str] = None  # 更新当前逻辑中的 notes
    dify_api_key: Optional[str] = None  # 更新当前逻辑中的 dify api key
    dify_app_id: Optional[str] = None  # 更新当前逻辑中的 dify app id
    ragflow_dataset_id: Optional[str] = None  # 更新当前逻辑中的 ragflow dataset id


class TenantResponse(BaseModel):  # 定义业务类 TenantResponse
    """租户响应。"""  # 类文档字符串，概述 TenantResponse 的用途

    id: int  # 执行当前业务步骤并推进后续处理
    code: str  # 执行当前业务步骤并推进后续处理
    name: str  # 执行当前业务步骤并推进后续处理
    industry: Optional[str] = None  # 更新当前逻辑中的 industry
    region: str  # 执行当前业务步骤并推进后续处理
    contact_name: Optional[str] = None  # 更新当前逻辑中的 contact name
    contact_email: Optional[str] = None  # 更新当前逻辑中的 contact email
    contact_phone: Optional[str] = None  # 更新当前逻辑中的 contact phone
    status: str  # 执行当前业务步骤并推进后续处理
    is_demo: bool  # 执行当前业务步骤并推进后续处理
    created_at: datetime  # 执行当前业务步骤并推进后续处理
    updated_at: datetime  # 执行当前业务步骤并推进后续处理

    class Config:  # 定义业务类 Config
        from_attributes = True  # 更新当前逻辑中的 from attributes
