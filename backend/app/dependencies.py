"""路由依赖：认证、租户解析与分页约束。"""  # 模块文档字符串，概述当前文件职责
from typing import Optional  # 导入当前模块运行所依赖的工具或类型

from fastapi import Depends, Header, HTTPException  # 导入 FastAPI 的路由、请求和依赖注入对象
from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力

from app.database import get_db, settings  # 导入数据库依赖与全局运行配置
from app.models import Admin, Tenant  # 导入当前业务会读写的 ORM 模型
from app.security import decode_token, role_label, role_permissions  # 导入鉴权、脱敏和角色权限相关工具


async def get_current_admin(  # 定义获取 current admin 的接口或辅助函数
    authorization: Optional[str] = Header(None),  # 声明参数 authorization，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
) -> dict:  # 结束 get_current_admin 的参数声明
    if not authorization:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=401, detail="未授权")  # 抛出 HTTP 异常并把错误信息返回给前端

    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        scheme, token = authorization.split()  # 执行当前业务步骤并推进后续处理
    except ValueError as exc:  # 捕获异常并执行降级或错误处理逻辑
        raise HTTPException(status_code=401, detail="无效的授权头") from exc  # 抛出 HTTP 异常并把错误信息返回给前端

    if scheme.lower() != "bearer":  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=401, detail="无效的认证方案")  # 抛出 HTTP 异常并把错误信息返回给前端

    payload = decode_token(token)  # 组装发往外部问答服务的请求载荷
    if not payload or not payload.get("sub"):  # 仅在对应字段存在时追加去重匹配条件
        raise HTTPException(status_code=401, detail="令牌无效或已过期")  # 抛出 HTTP 异常并把错误信息返回给前端

    admin = db.query(Admin).filter(Admin.id == int(payload["sub"]), Admin.is_active.is_(True)).first()  # 构造当前业务的基础数据库查询对象
    if not admin:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=401, detail="管理员不存在或已停用")  # 抛出 HTTP 异常并把错误信息返回给前端

    tenant = admin.tenant  # 保存当前请求实际使用的租户对象
    return {  # 返回当前分支整理好的结果
        "id": admin.id,  # 填充返回或配置中的 主键 ID 字段
        "username": admin.username,  # 填充返回或配置中的 username 字段
        "display_name": admin.display_name,  # 填充返回或配置中的 display name 字段
        "role": admin.role,  # 填充返回或配置中的 role 字段
        "role_label": role_label(admin.role),  # 填充返回或配置中的 role label 字段
        "permissions": role_permissions(admin.role),  # 填充返回或配置中的 permissions 字段
        "tenant_id": admin.tenant_id,  # 填充返回或配置中的 租户 ID 字段
        "tenant_code": tenant.code if tenant else None,  # 填充返回或配置中的 tenant code 字段
        "tenant_name": tenant.name if tenant else None,  # 填充返回或配置中的 租户名称 字段
    }  # 结束 返回结果 的定义或组装


def get_admin_tenant_filter(current_admin: dict, requested_tenant_id: Optional[int] = None) -> Optional[int]:  # 定义获取 admin tenant filter 的接口或辅助函数
    """返回当前管理员可操作的 tenant_id。超级管理员可传 None 表示全部。"""  # 函数文档字符串，说明 get_admin_tenant_filter 的职责
    if current_admin["role"] == "super_admin":  # 非超级管理员只能查看自己所属租户的数据
        return requested_tenant_id  # 返回当前分支整理好的结果
    if requested_tenant_id and requested_tenant_id != current_admin.get("tenant_id"):  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=403, detail="不能访问其他租户数据")  # 抛出 HTTP 异常并把错误信息返回给前端
    tenant_id = current_admin.get("tenant_id")  # 更新当前逻辑中的 租户 ID
    if not tenant_id:  # 租户不存在或不可用时直接终止请求
        raise HTTPException(status_code=403, detail="当前账号未绑定租户")  # 抛出 HTTP 异常并把错误信息返回给前端
    return tenant_id  # 返回当前分支整理好的结果


def get_public_tenant(  # 定义获取 public tenant 的接口或辅助函数
    tenant_code: Optional[str] = Header(default=None, alias="X-Tenant-Code"),  # 声明参数 tenant_code，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
) -> Tenant:  # 结束 get_public_tenant 的参数声明
    code = tenant_code or settings.default_tenant_code  # 更新当前逻辑中的 code
    tenant = db.query(Tenant).filter(Tenant.code == code, Tenant.status == "active").first()  # 构造当前业务的基础数据库查询对象
    if not tenant:  # 租户不存在或不可用时直接终止请求
        raise HTTPException(status_code=404, detail="租户不存在或已停用")  # 抛出 HTTP 异常并把错误信息返回给前端
    return tenant  # 返回当前分支整理好的结果


def normalize_pagination(page: int, page_size: int) -> tuple[int, int]:  # 定义业务处理函数 normalize_pagination
    page = max(1, page)  # 更新当前逻辑中的 page
    page_size = min(max(1, page_size), 100)  # 更新当前逻辑中的 page size
    return page, page_size  # 返回当前分支整理好的结果
