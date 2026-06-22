"""FAQ 相关 Pydantic 模型。"""  # 模块文档字符串，概述当前文件职责
from typing import Optional, List  # 导入当前模块运行所依赖的工具或类型
from pydantic import BaseModel, Field  # 导入 Pydantic 数据校验或配置能力
from datetime import date, datetime  # 导入当前模块运行所依赖的工具或类型


class FAQCreate(BaseModel):  # 定义业务类 FAQCreate
    """FAQ创建请求"""  # 类文档字符串，概述 FAQCreate 的用途
    faq_code: Optional[str] = None  # 更新当前逻辑中的 FAQ 编码
    question: str = Field(min_length=2, max_length=500)  # 更新当前逻辑中的 问题内容
    answer: str = Field(min_length=2)  # 更新当前逻辑中的 回答内容
    category: Optional[str] = None  # 更新当前逻辑中的 分类
    region: str = "陕西"  # 更新当前逻辑中的 地区
    risk_level: str = "medium"  # 更新当前逻辑中的 风险等级
    keywords: Optional[List[str]] = None  # 更新当前逻辑中的 关键字
    aliases: Optional[List[str]] = None  # 更新当前逻辑中的 aliases
    source_ids: Optional[List[int]] = None  # 更新当前逻辑中的 source ids
    language: str = "zh-CN"  # 更新当前逻辑中的 语言代码
    effective_date: Optional[date] = None  # 更新当前逻辑中的 effective date


class FAQUpdate(BaseModel):  # 定义业务类 FAQUpdate
    """FAQ更新请求"""  # 类文档字符串，概述 FAQUpdate 的用途
    faq_code: Optional[str] = None  # 更新当前逻辑中的 FAQ 编码
    question: Optional[str] = None  # 更新当前逻辑中的 问题内容
    answer: Optional[str] = None  # 更新当前逻辑中的 回答内容
    category: Optional[str] = None  # 更新当前逻辑中的 分类
    region: Optional[str] = None  # 更新当前逻辑中的 地区
    risk_level: Optional[str] = None  # 更新当前逻辑中的 风险等级
    keywords: Optional[List[str]] = None  # 更新当前逻辑中的 关键字
    aliases: Optional[List[str]] = None  # 更新当前逻辑中的 aliases
    source_ids: Optional[List[int]] = None  # 更新当前逻辑中的 source ids
    language: Optional[str] = None  # 更新当前逻辑中的 语言代码
    effective_date: Optional[date] = None  # 更新当前逻辑中的 effective date


class FAQResponse(BaseModel):  # 定义业务类 FAQResponse
    """FAQ响应"""  # 类文档字符串，概述 FAQResponse 的用途
    id: int  # 执行当前业务步骤并推进后续处理
    tenant_id: int  # 执行当前业务步骤并推进后续处理
    faq_code: Optional[str]  # 执行当前业务步骤并推进后续处理
    question: str  # 执行当前业务步骤并推进后续处理
    answer: str  # 执行当前业务步骤并推进后续处理
    category: Optional[str]  # 执行当前业务步骤并推进后续处理
    region: str  # 执行当前业务步骤并推进后续处理
    risk_level: str  # 执行当前业务步骤并推进后续处理
    keywords: Optional[List[str]]  # 执行当前业务步骤并推进后续处理
    aliases: Optional[List[str]]  # 执行当前业务步骤并推进后续处理
    source_ids: Optional[List[int]]  # 执行当前业务步骤并推进后续处理
    language: str  # 执行当前业务步骤并推进后续处理
    effective_date: Optional[date]  # 执行当前业务步骤并推进后续处理
    created_at: datetime  # 执行当前业务步骤并推进后续处理
    updated_at: datetime  # 执行当前业务步骤并推进后续处理
    
    class Config:  # 定义业务类 Config
        from_attributes = True  # 更新当前逻辑中的 from attributes
