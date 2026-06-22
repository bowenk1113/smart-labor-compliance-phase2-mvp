"""安全模块：JWT、密码哈希、角色权限与脱敏工具。"""  # 模块文档字符串，概述当前文件职责
import hashlib  # 导入当前模块运行所依赖的工具或类型
import hmac  # 导入当前模块运行所依赖的工具或类型
import re  # 导入当前模块运行所依赖的工具或类型
from datetime import datetime, timedelta  # 导入当前模块运行所依赖的工具或类型
from typing import Iterable, Optional  # 导入当前模块运行所依赖的工具或类型

from jose import JWTError, jwt  # 导入当前模块运行所依赖的工具或类型
from passlib.context import CryptContext  # 导入当前模块运行所依赖的工具或类型
from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力
from app.database import SessionLocal, settings  # 导入数据库依赖与全局运行配置
from app.models import Admin, Tenant  # 导入当前业务会读写的 ORM 模型

ALGORITHM = "HS256"  # 更新当前逻辑中的 ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # 更新当前逻辑中的 pwd context

ROLE_LABELS = {  # 更新当前逻辑中的 ROLE LABELS
    "super_admin": "超级管理员",  # 填充返回或配置中的 super admin 字段
    "tenant_admin": "租户管理员",  # 填充返回或配置中的 tenant admin 字段
    "operator": "运营人员",  # 填充返回或配置中的 operator 字段
    "viewer": "只读人员",  # 填充返回或配置中的 viewer 字段
}  # 结束 ROLE_LABELS 的定义或组装

ROLE_PERMISSIONS = {  # 更新当前逻辑中的 ROLE PERMISSIONS
    "super_admin": [  # 填充返回或配置中的 super admin 字段
        "dashboard",  # 填充返回或配置中的 字段 字段
        "tenants",  # 填充返回或配置中的 字段 字段
        "admins",  # 填充返回或配置中的 字段 字段
        "logs",  # 填充返回或配置中的 字段 字段
        "feedbacks",  # 填充返回或配置中的 字段 字段
        "faqs",  # 填充返回或配置中的 字段 字段
        "faqs_import",  # 填充返回或配置中的 字段 字段
        "faqs_export",  # 填充返回或配置中的 字段 字段
        "faqs_batch",  # 填充返回或配置中的 字段 字段
        "sources",  # 填充返回或配置中的 字段 字段
        "sources_import",  # 填充返回或配置中的 字段 字段
        "sources_export",  # 填充返回或配置中的 字段 字段
        "sources_batch",  # 填充返回或配置中的 字段 字段
        "packages",  # 填充返回或配置中的 字段 字段
        "packages_import",  # 填充返回或配置中的 字段 字段
        "packages_export",  # 填充返回或配置中的 字段 字段
        "packages_batch",  # 填充返回或配置中的 字段 字段
        "test_questions",  # 填充返回或配置中的 字段 字段
        "settings",  # 填充返回或配置中的 字段 字段
    ],  # 填充返回或配置中的 字段 字段
    "tenant_admin": [  # 填充返回或配置中的 tenant admin 字段
        "dashboard",  # 填充返回或配置中的 字段 字段
        "admins",  # 填充返回或配置中的 字段 字段
        "logs",  # 填充返回或配置中的 字段 字段
        "feedbacks",  # 填充返回或配置中的 字段 字段
        "faqs",  # 填充返回或配置中的 字段 字段
        "faqs_import",  # 填充返回或配置中的 字段 字段
        "faqs_export",  # 填充返回或配置中的 字段 字段
        "faqs_batch",  # 填充返回或配置中的 字段 字段
        "sources",  # 填充返回或配置中的 字段 字段
        "sources_import",  # 填充返回或配置中的 字段 字段
        "sources_export",  # 填充返回或配置中的 字段 字段
        "sources_batch",  # 填充返回或配置中的 字段 字段
        "packages",  # 填充返回或配置中的 字段 字段
        "packages_import",  # 填充返回或配置中的 字段 字段
        "packages_export",  # 填充返回或配置中的 字段 字段
        "packages_batch",  # 填充返回或配置中的 字段 字段
        "test_questions",  # 填充返回或配置中的 字段 字段
    ],  # 填充返回或配置中的 字段 字段
    "operator": [  # 填充返回或配置中的 operator 字段
        "dashboard",  # 填充返回或配置中的 字段 字段
        "logs",  # 填充返回或配置中的 字段 字段
        "feedbacks",  # 填充返回或配置中的 字段 字段
        "faqs",  # 填充返回或配置中的 字段 字段
        "faqs_import",  # 填充返回或配置中的 字段 字段
        "faqs_export",  # 填充返回或配置中的 字段 字段
        "faqs_batch",  # 填充返回或配置中的 字段 字段
        "sources",  # 填充返回或配置中的 字段 字段
        "sources_import",  # 填充返回或配置中的 字段 字段
        "sources_export",  # 填充返回或配置中的 字段 字段
        "sources_batch",  # 填充返回或配置中的 字段 字段
        "packages",  # 填充返回或配置中的 字段 字段
        "packages_import",  # 填充返回或配置中的 字段 字段
        "packages_export",  # 填充返回或配置中的 字段 字段
        "packages_batch",  # 填充返回或配置中的 字段 字段
        "test_questions",  # 填充返回或配置中的 字段 字段
    ],  # 填充返回或配置中的 字段 字段
    "viewer": ["dashboard", "logs"],  # 填充返回或配置中的 viewer 字段
}  # 结束 ROLE_PERMISSIONS 的定义或组装

SUPER_ADMIN_ROLES = {"super_admin"}  # 更新当前逻辑中的 SUPER ADMIN ROLES
TENANT_ADMIN_ROLES = {"super_admin", "tenant_admin"}  # 更新当前逻辑中的 TENANT ADMIN ROLES

SENSITIVE_PATTERNS = [  # 更新当前逻辑中的 SENSITIVE PATTERNS
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "[身份证号已脱敏]"),  # 补充列表中的 compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "[身份证号已脱敏]") 项
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[手机号已脱敏]"),  # 补充列表中的 compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[手机号已脱敏]") 项
    (re.compile(r"(?<!\d)\d{12,19}(?!\d)"), "[银行卡号已脱敏]"),  # 补充列表中的 compile(r"(?<!\d)\d{12,19}(?!\d)"), "[银行卡号已脱敏]") 项
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[邮箱已脱敏]"),  # 补充列表中的 [A-Za-z]{2,}"), "[邮箱已脱敏]") 项
]  # 结束 SENSITIVE_PATTERNS 的定义或组装


def verify_password(plain_password: str, hashed_password: str) -> bool:  # 定义业务处理函数 verify_password
    """验证密码"""  # 函数文档字符串，说明 verify_password 的职责
    return pwd_context.verify(plain_password, hashed_password)  # 返回当前分支整理好的结果


def get_password_hash(password: str) -> str:  # 定义获取 password hash 的接口或辅助函数
    """获取密码哈希"""  # 函数文档字符串，说明 get_password_hash 的职责
    return pwd_context.hash(password)  # 返回当前分支整理好的结果


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:  # 定义创建 access token 的接口或辅助函数
    """创建访问令牌"""  # 函数文档字符串，说明 create_access_token 的职责
    to_encode = data.copy()  # 更新当前逻辑中的 to encode
    if expires_delta:  # 根据当前条件决定是否进入对应业务分支
        expire = datetime.utcnow() + expires_delta  # 更新当前逻辑中的 expire
    else:  # 处理其他未命中的业务情况
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)  # 更新当前逻辑中的 expire
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})  # 执行当前业务步骤并推进后续处理
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)  # 更新当前逻辑中的 encoded jwt
    return encoded_jwt  # 返回当前分支整理好的结果


def decode_token(token: str) -> Optional[dict]:  # 定义业务处理函数 decode_token
    """解码令牌"""  # 函数文档字符串，说明 decode_token 的职责
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])  # 组装发往外部问答服务的请求载荷
        return payload  # 返回当前分支整理好的结果
    except JWTError:  # 捕获异常并执行降级或错误处理逻辑
        return None  # 返回当前分支整理好的结果


def role_label(role: str) -> str:  # 定义业务处理函数 role_label
    return ROLE_LABELS.get(role, role)  # 返回当前分支整理好的结果


def role_permissions(role: str) -> list[str]:  # 定义业务处理函数 role_permissions
    return ROLE_PERMISSIONS.get(role, [])  # 返回当前分支整理好的结果


def require_role(role: str, allowed_roles: Iterable[str]) -> None:  # 定义业务处理函数 require_role
    if role not in allowed_roles:  # 根据当前条件决定是否进入对应业务分支
        from fastapi import HTTPException  # 导入 FastAPI 的路由、请求和依赖注入对象

        raise HTTPException(status_code=403, detail="当前账号没有该操作权限")  # 抛出 HTTP 异常并把错误信息返回给前端


def sanitize_text(text: Optional[str]) -> Optional[str]:  # 定义业务处理函数 sanitize_text
    """脱敏个人敏感信息，避免写入日志或知识库。"""  # 函数文档字符串，说明 sanitize_text 的职责
    if text is None:  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    cleaned = text.strip()  # 更新当前逻辑中的 cleaned
    for pattern, replacement in SENSITIVE_PATTERNS:  # 遍历当前集合中的每一项并逐个处理
        cleaned = pattern.sub(replacement, cleaned)  # 更新当前逻辑中的 cleaned
    return cleaned  # 返回当前分支整理好的结果


def hash_ip(ip: Optional[str]) -> Optional[str]:  # 定义业务处理函数 hash_ip
    if not ip:  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    digest = hmac.new(settings.jwt_secret_key.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256)  # 更新当前逻辑中的 digest
    return digest.hexdigest()  # 返回当前分支整理好的结果


def authenticate_admin(username: str, password: str, tenant_code: Optional[str] = None) -> Optional[dict]:  # 定义业务处理函数 authenticate_admin
    """验证管理员"""  # 函数文档字符串，说明 authenticate_admin 的职责
    db = SessionLocal()  # 创建新的数据库会话
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        query = db.query(Admin).filter(Admin.username == username, Admin.is_active.is_(True))  # 构造当前业务的基础数据库查询对象
        if tenant_code:  # 根据当前条件决定是否进入对应业务分支
            query = query.join(Tenant).filter(Tenant.code == tenant_code)  # 保存当前逐步拼装的数据库查询对象
        admin = query.order_by(Admin.id.asc()).first()  # 更新当前逻辑中的 admin
        if not admin:  # 根据当前条件决定是否进入对应业务分支
            return None  # 返回当前分支整理好的结果
        if not verify_password(password, admin.password_hash):  # 根据当前条件决定是否进入对应业务分支
            return None  # 返回当前分支整理好的结果
        admin.last_login_at = datetime.utcnow()  # 更新当前逻辑中的 last login at
        db.commit()  # 提交本次数据库事务，持久化前面的变更
        tenant = admin.tenant  # 保存当前请求实际使用的租户对象
        return {  # 返回当前分支整理好的结果
            "id": admin.id,  # 填充返回或配置中的 主键 ID 字段
            "username": admin.username,  # 填充返回或配置中的 username 字段
            "role": admin.role,  # 填充返回或配置中的 role 字段
            "tenant_id": admin.tenant_id,  # 填充返回或配置中的 租户 ID 字段
            "tenant_code": tenant.code if tenant else None,  # 填充返回或配置中的 tenant code 字段
            "tenant_name": tenant.name if tenant else None,  # 填充返回或配置中的 租户名称 字段
        }  # 结束 返回结果 的定义或组装
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        db.close()  # 执行当前业务步骤并推进后续处理


def create_admin(  # 定义创建 admin 的接口或辅助函数
    username: str,  # 声明参数 username，供当前逻辑使用
    password: str,  # 声明参数 password，供当前逻辑使用
    role: str = "operator",  # 声明参数 role，供当前逻辑使用
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    display_name: Optional[str] = None,  # 声明参数 display_name，供当前逻辑使用
) -> bool:  # 结束 create_admin 的参数声明
    """创建管理员账号"""  # 模块文档字符串，概述当前文件职责
    db = SessionLocal()  # 创建新的数据库会话
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        # 检查是否已存在
        existing = db.query(Admin).filter(Admin.username == username, Admin.tenant_id == tenant_id).first()  # 构造当前业务的基础数据库查询对象
        if existing:  # 根据当前条件决定是否进入对应业务分支
            return False  # 返回当前分支整理好的结果
        
        admin = Admin(  # 更新当前逻辑中的 admin
            username=username,  # 设置 Admin 的 username
            password_hash=get_password_hash(password),  # 设置 Admin 的 password hash
            role=role,  # 设置 Admin 的 role
            tenant_id=tenant_id,  # 设置 Admin 的 租户 ID
            display_name=display_name,  # 设置 Admin 的 display name
        )  # 结束 Admin 的定义或组装
        db.add(admin)  # 把新实体加入当前数据库事务等待提交
        db.commit()  # 提交本次数据库事务，持久化前面的变更
        return True  # 返回当前分支整理好的结果
    except Exception as e:  # 捕获异常并执行降级或错误处理逻辑
        db.rollback()  # 执行当前业务步骤并推进后续处理
        print(f"创建管理员失败: {e}")  # 执行当前业务步骤并推进后续处理
        return False  # 返回当前分支整理好的结果
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        db.close()  # 执行当前业务步骤并推进后续处理
