"""来源相关 Pydantic 模型。"""  # 模块文档字符串，概述当前文件职责
from typing import Optional  # 导入当前模块运行所依赖的工具或类型
from pydantic import BaseModel, Field, model_validator  # 导入 Pydantic 数据校验或配置能力
from datetime import date, datetime  # 导入当前模块运行所依赖的工具或类型


def _has_text(value: Optional[str]) -> bool:  # 定义业务处理函数 _has_text
    return bool((value or "").strip())  # 返回当前分支整理好的结果


class SourceCreate(BaseModel):  # 定义业务类 SourceCreate
    """来源创建请求"""  # 类文档字符串，概述 SourceCreate 的用途
    source_code: Optional[str] = None  # 更新当前逻辑中的 资料编码
    title: str = Field(min_length=2, max_length=200)  # 更新当前逻辑中的 标题
    url: Optional[str] = None  # 更新当前逻辑中的 链接地址
    doc_type: Optional[str] = None  # 更新当前逻辑中的 doc type
    issuer: Optional[str] = None  # 更新当前逻辑中的 issuer
    region: Optional[str] = None  # 更新当前逻辑中的 地区
    publish_date: Optional[date] = None  # 更新当前逻辑中的 publish date
    effective_date: Optional[date] = None  # 更新当前逻辑中的 effective date
    validity_status: str = "有效"  # 更新当前逻辑中的 validity status
    review_status: str = "待人工复核"  # 更新当前逻辑中的 review status
    captured_at: Optional[date] = None  # 更新当前逻辑中的 captured at
    owner: Optional[str] = None  # 更新当前逻辑中的 owner
    local_file: Optional[str] = None  # 更新当前逻辑中的 local file
    note: Optional[str] = None  # 更新当前逻辑中的 note
    description: Optional[str] = None  # 更新当前逻辑中的 说明描述

    @model_validator(mode="after")  # 为后续函数或类声明附加装饰器配置
    def validate_source_path(self):  # 定义业务处理函数 validate_source_path
        if not _has_text(self.url) and not _has_text(self.local_file):  # 根据当前条件决定是否进入对应业务分支
            raise ValueError("外部链接与上传文件必须至少填写一个")  # 执行当前控制流分支
        return self  # 返回当前分支整理好的结果


class SourceUpdate(BaseModel):  # 定义业务类 SourceUpdate
    """来源更新请求"""  # 类文档字符串，概述 SourceUpdate 的用途
    source_code: Optional[str] = None  # 更新当前逻辑中的 资料编码
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)  # 更新当前逻辑中的 标题
    url: Optional[str] = None  # 更新当前逻辑中的 链接地址
    doc_type: Optional[str] = None  # 更新当前逻辑中的 doc type
    issuer: Optional[str] = None  # 更新当前逻辑中的 issuer
    region: Optional[str] = None  # 更新当前逻辑中的 地区
    publish_date: Optional[date] = None  # 更新当前逻辑中的 publish date
    effective_date: Optional[date] = None  # 更新当前逻辑中的 effective date
    validity_status: Optional[str] = None  # 更新当前逻辑中的 validity status
    review_status: Optional[str] = None  # 更新当前逻辑中的 review status
    captured_at: Optional[date] = None  # 更新当前逻辑中的 captured at
    owner: Optional[str] = None  # 更新当前逻辑中的 owner
    local_file: Optional[str] = None  # 更新当前逻辑中的 local file
    note: Optional[str] = None  # 更新当前逻辑中的 note
    description: Optional[str] = None  # 更新当前逻辑中的 说明描述

    @model_validator(mode="after")  # 为后续函数或类声明附加装饰器配置
    def validate_source_path(self):  # 定义业务处理函数 validate_source_path
        if self.url is not None and self.local_file is not None and not _has_text(self.url) and not _has_text(self.local_file):  # 根据当前条件决定是否进入对应业务分支
            raise ValueError("外部链接与上传文件必须至少填写一个")  # 执行当前控制流分支
        return self  # 返回当前分支整理好的结果


class SourceResponse(BaseModel):  # 定义业务类 SourceResponse
    """来源响应"""  # 类文档字符串，概述 SourceResponse 的用途
    id: int  # 执行当前业务步骤并推进后续处理
    tenant_id: int  # 执行当前业务步骤并推进后续处理
    source_code: Optional[str]  # 执行当前业务步骤并推进后续处理
    title: str  # 执行当前业务步骤并推进后续处理
    url: Optional[str]  # 执行当前业务步骤并推进后续处理
    doc_type: Optional[str]  # 执行当前业务步骤并推进后续处理
    issuer: Optional[str]  # 执行当前业务步骤并推进后续处理
    region: Optional[str]  # 执行当前业务步骤并推进后续处理
    publish_date: Optional[date]  # 执行当前业务步骤并推进后续处理
    effective_date: Optional[date]  # 执行当前业务步骤并推进后续处理
    validity_status: str  # 执行当前业务步骤并推进后续处理
    review_status: str  # 执行当前业务步骤并推进后续处理
    reviewed_at: Optional[datetime]  # 执行当前业务步骤并推进后续处理
    reviewed_by: Optional[str]  # 执行当前业务步骤并推进后续处理
    captured_at: Optional[date]  # 执行当前业务步骤并推进后续处理
    owner: Optional[str]  # 执行当前业务步骤并推进后续处理
    local_file: Optional[str]  # 执行当前业务步骤并推进后续处理
    note: Optional[str]  # 执行当前业务步骤并推进后续处理
    description: Optional[str]  # 执行当前业务步骤并推进后续处理
    created_at: datetime  # 执行当前业务步骤并推进后续处理
    
    class Config:  # 定义业务类 Config
        from_attributes = True  # 更新当前逻辑中的 from attributes
