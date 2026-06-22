"""管理端路由。"""  # 模块文档字符串，概述当前文件职责
import csv  # 导入 CSV 读写工具，供导入导出接口复用
import io  # 导入内存流工具，便于处理上传与下载内容
import json  # 导入 JSON 编解码工具，处理结构化字段
from datetime import date, datetime, timedelta  # 导入当前模块运行所依赖的工具或类型
from difflib import SequenceMatcher  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from typing import Optional  # 导入当前模块运行所依赖的工具或类型
from urllib.parse import urlparse  # 导入当前模块运行所依赖的工具或类型
from uuid import uuid4  # 导入当前模块运行所依赖的工具或类型

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile  # 导入 FastAPI 的路由、请求和依赖注入对象
from fastapi.responses import StreamingResponse  # 导入 FastAPI 的路由、请求和依赖注入对象
from sqlalchemy import desc, func, or_  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力

from app.database import get_db, settings  # 导入数据库依赖与全局运行配置
from app.dependencies import get_admin_tenant_filter, get_current_admin, normalize_pagination  # 导入请求依赖与租户隔离辅助函数
from app.models import Admin, ChatLog, FAQ, Feedback, KnowledgePackage, Source, Tenant, TestQuestion  # 导入当前业务会读写的 ORM 模型
from app.response import ok, page as page_response  # 导入统一成功响应与分页响应封装
from app.rag.knowledge_sync import clear_local_index_cache, rag_sync_status, rebuild_milvus_knowledge_base, sync_after_faq_change  # 导入二期 RAG 检索与问答服务组件
from app.schemas.admin import AdminCreate, AdminLogin, AdminToken, AdminUpdate, TenantCreate, TenantUpdate  # 导入接口请求体与响应体模型
from app.schemas.faq import FAQCreate, FAQUpdate  # 导入接口请求体与响应体模型
from app.schemas.source import SourceCreate, SourceUpdate  # 导入接口请求体与响应体模型
from app.security import (  # 导入鉴权、脱敏和角色权限相关工具
    ROLE_LABELS,  # 执行当前业务步骤并推进后续处理
    ROLE_PERMISSIONS,  # 执行当前业务步骤并推进后续处理
    SUPER_ADMIN_ROLES,  # 执行当前业务步骤并推进后续处理
    TENANT_ADMIN_ROLES,  # 执行当前业务步骤并推进后续处理
    authenticate_admin,  # 执行当前业务步骤并推进后续处理
    create_access_token,  # 执行当前业务步骤并推进后续处理
    get_password_hash,  # 执行当前业务步骤并推进后续处理
    require_role,  # 执行当前业务步骤并推进后续处理
    role_label,  # 执行当前业务步骤并推进后续处理
    role_permissions,  # 执行当前业务步骤并推进后续处理
    sanitize_text,  # 执行当前业务步骤并推进后续处理
)  # 执行当前业务步骤并推进后续处理
from app.services.dify_service import check_external_services  # 导入外部问答或种子数据相关服务

router = APIRouter(prefix="/api/admin", tags=["管理端"])  # 注册当前模块的路由前缀与分组标签

ALLOWED_SOURCE_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".html", ".htm", ".csv", ".xlsx", ".xls"}  # 声明资料上传允许的文件扩展名
ALLOWED_IMPORT_FILE_EXTENSIONS = {".csv"}  # 声明批量导入允许的文件扩展名
FAQ_EXPORT_FIELDS = ["id", "faq_code", "question", "answer", "category", "region", "risk_level", "keywords", "language", "effective_date"]  # 声明 FAQ 导出字段顺序
SOURCE_EXPORT_FIELDS = ["id", "source_code", "title", "url", "doc_type", "issuer", "region", "validity_status", "review_status", "reviewed_at", "reviewed_by", "local_file", "description"]  # 声明资料来源导出字段顺序
PACKAGE_EXPORT_FIELDS = ["id", "name", "region", "version", "description", "categories", "status", "dify_dataset_id", "ragflow_dataset_id"]  # 声明知识包导出字段顺序


def _require_permission(current_admin: dict, permission: str) -> None:  # 定义后台权限校验辅助函数
    if permission not in current_admin.get("permissions", []):  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=403, detail="当前账号没有该操作权限")  # 抛出 HTTP 异常并把错误信息返回给前端


def _parse_ids(ids: Optional[str]) -> list[int]:  # 定义批量 ID 参数解析函数
    if not ids:  # 没有传入 ID 列表时直接返回空结果
        return []  # 返回当前分支整理好的结果
    parsed: list[int] = []  # 更新当前逻辑中的 parsed
    for raw in ids.split(","):  # 遍历当前集合中的每一项并逐个处理
        raw = raw.strip()  # 更新当前逻辑中的 raw
        if not raw:  # 跳过当前空白 ID 片段，避免解析报错
            continue  # 跳过当前项，继续处理下一项数据
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            parsed.append(int(raw))  # 把解析成功的 ID 追加到结果列表中
        except ValueError as exc:  # 捕获异常并执行降级或错误处理逻辑
            raise HTTPException(status_code=400, detail="无效的 ID 列表") from exc  # 抛出 HTTP 异常并把错误信息返回给前端
    return parsed  # 返回当前分支整理好的结果


def _read_json_list(value):  # 定义业务处理函数 _read_json_list
    if value is None or value == "":  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    if isinstance(value, list):  # 根据当前条件决定是否进入对应业务分支
        return value  # 返回当前分支整理好的结果
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        parsed = json.loads(value)  # 更新当前逻辑中的 parsed
        if isinstance(parsed, list):  # 根据当前条件决定是否进入对应业务分支
            return parsed  # 返回当前分支整理好的结果
    except (TypeError, json.JSONDecodeError):  # 捕获异常并执行降级或错误处理逻辑
        pass  # 当前分支无需额外处理，保留语法占位
    return [item.strip() for item in str(value).split("|") if item.strip()]  # 返回当前分支整理好的结果


def _csv_text_response(filename: str, rows: list[dict], fields: list[str]) -> StreamingResponse:  # 定义 CSV 文件下载响应构造函数
    output = io.StringIO()  # 创建内存文本缓冲区以拼装导出内容
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")  # 创建 CSV 写出器，按字段顺序输出数据
    writer.writeheader()  # 先写出 CSV 表头，保证导出文件字段齐全
    for row in rows:  # 遍历当前集合中的每一项并逐个处理
        normalized = {}  # 初始化当前导出行的标准化结果字典
        for field in fields:  # 遍历当前集合中的每一项并逐个处理
            value = row.get(field)  # 读取当前字段原始值，准备转成导出格式
            if isinstance(value, (list, dict)):  # 根据当前条件决定是否进入对应业务分支
                value = json.dumps(value, ensure_ascii=False)  # 读取当前字段原始值，准备转成导出格式
            elif isinstance(value, datetime):  # 前一个条件不满足时继续判断其他分支
                value = value.isoformat(sep=" ", timespec="seconds")  # 读取当前字段原始值，准备转成导出格式
            elif isinstance(value, date):  # 前一个条件不满足时继续判断其他分支
                value = value.isoformat()  # 读取当前字段原始值，准备转成导出格式
            normalized[field] = "" if value is None else value  # 更新当前逻辑中的 normalized[field]
        writer.writerow(normalized)  # 把当前整理好的记录写入一行 CSV 数据
    content = output.getvalue().encode("utf-8-sig")  # 生成最终返回或上传的字节内容
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}  # 准备当前响应或外部请求需要的 HTTP 头
    return StreamingResponse(io.BytesIO(content), media_type="text/csv; charset=utf-8", headers=headers)  # 返回可下载的流式响应内容


async def _read_import_rows(file: UploadFile) -> list[dict]:  # 定义异步处理函数 _read_import_rows
    suffix = Path(file.filename or "").suffix.lower()  # 提取上传文件扩展名，校验导入格式是否允许
    if suffix not in ALLOWED_IMPORT_FILE_EXTENSIONS:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="目前仅支持 CSV 文件导入")  # 抛出 HTTP 异常并把错误信息返回给前端
    content = await file.read()  # 生成最终返回或上传的字节内容
    await file.close()  # 关闭上传文件句柄，释放临时资源
    if not content:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="导入文件为空")  # 抛出 HTTP 异常并把错误信息返回给前端
    text = content.decode("utf-8-sig")  # 把文件字节内容解码成可解析的文本
    return [dict(row) for row in csv.DictReader(io.StringIO(text)) if any((value or "").strip() for value in row.values())]  # 返回当前分支整理好的结果


def _module_query(db: Session, model, current_admin: dict, ids: Optional[str] = None, tenant_id: Optional[int] = None):  # 定义支持 ID 过滤的模块查询函数
    query = _tenant_scoped_query(db, model, current_admin, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    parsed_ids = _parse_ids(ids)  # 解析批量操作请求中的 ID 列表
    if parsed_ids:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(model.id.in_(parsed_ids))  # 保存当前逐步拼装的数据库查询对象
    return query  # 返回当前分支整理好的结果


def _tenant_query(db: Session, current_admin: dict):  # 定义租户查询构造函数
    query = db.query(Tenant)  # 构造当前业务的基础数据库查询对象
    if current_admin["role"] != "super_admin":  # 非超级管理员只能查看自己所属租户的数据
        query = query.filter(Tenant.id == current_admin["tenant_id"])  # 保存当前逐步拼装的数据库查询对象
    return query  # 返回当前分支整理好的结果


def _serialize_admin(admin: Admin) -> dict:  # 定义管理员对象序列化函数
    return {  # 返回当前分支整理好的结果
        "id": admin.id,  # 填充返回或配置中的 主键 ID 字段
        "tenant_id": admin.tenant_id,  # 填充返回或配置中的 租户 ID 字段
        "tenant_name": admin.tenant.name if admin.tenant else "平台",  # 填充返回或配置中的 租户名称 字段
        "username": admin.username,  # 填充返回或配置中的 username 字段
        "role": admin.role,  # 填充返回或配置中的 role 字段
        "role_label": role_label(admin.role),  # 填充返回或配置中的 role label 字段
        "display_name": admin.display_name,  # 填充返回或配置中的 display name 字段
        "email": admin.email,  # 填充返回或配置中的 email 字段
        "is_active": admin.is_active,  # 填充返回或配置中的 is active 字段
        "created_at": admin.created_at,  # 填充返回或配置中的 创建时间 字段
        "last_login_at": admin.last_login_at,  # 填充返回或配置中的 last login at 字段
    }  # 结束 返回结果 的定义或组装


def _serialize_tenant(tenant: Tenant) -> dict:  # 定义租户对象序列化函数
    return {  # 返回当前分支整理好的结果
        "id": tenant.id,  # 填充返回或配置中的 主键 ID 字段
        "code": tenant.code,  # 填充返回或配置中的 code 字段
        "name": tenant.name,  # 填充返回或配置中的 名称 字段
        "industry": tenant.industry,  # 填充返回或配置中的 industry 字段
        "region": tenant.region,  # 填充返回或配置中的 地区 字段
        "contact_name": tenant.contact_name,  # 填充返回或配置中的 contact name 字段
        "contact_email": tenant.contact_email,  # 填充返回或配置中的 contact email 字段
        "contact_phone": tenant.contact_phone,  # 填充返回或配置中的 contact phone 字段
        "status": tenant.status,  # 填充返回或配置中的 状态 字段
        "is_demo": tenant.is_demo,  # 填充返回或配置中的 is demo 字段
        "dify_configured": bool(tenant.dify_api_key),  # 填充返回或配置中的 dify configured 字段
        "ragflow_dataset_id": tenant.ragflow_dataset_id,  # 填充返回或配置中的 ragflow dataset id 字段
        "notes": tenant.notes,  # 填充返回或配置中的 notes 字段
        "created_at": tenant.created_at,  # 填充返回或配置中的 创建时间 字段
        "updated_at": tenant.updated_at,  # 填充返回或配置中的 更新时间 字段
    }  # 结束 返回结果 的定义或组装


def _tenant_scoped_query(db: Session, model, current_admin: dict, tenant_id: Optional[int] = None):  # 定义带租户隔离的数据查询函数
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    query = db.query(model)  # 构造当前业务的基础数据库查询对象
    if allowed_tenant_id:  # 租户管理员场景下追加租户隔离过滤
        query = query.filter(model.tenant_id == allowed_tenant_id)  # 保存当前逐步拼装的数据库查询对象
    return query  # 返回当前分支整理好的结果


def _find_duplicate_faq(db: Session, tenant_id: int, payload: dict, exclude_id: Optional[int] = None) -> Optional[FAQ]:  # 定义 FAQ 去重查询函数
    filters = []  # 初始化用于去重判断的筛选条件列表
    if payload.get("faq_code"):  # 仅在对应字段存在时追加去重匹配条件
        filters.append(FAQ.faq_code == payload["faq_code"])  # 向去重筛选条件列表追加一条匹配规则
    if payload.get("question"):  # 仅在对应字段存在时追加去重匹配条件
        filters.append((FAQ.language == payload.get("language", "zh-CN")) & (FAQ.question == payload["question"]))  # 向去重筛选条件列表追加一条匹配规则
    if not filters:  # 没有可用去重条件时直接结束查询
        return None  # 返回当前分支整理好的结果
    query = db.query(FAQ).filter(FAQ.tenant_id == tenant_id, or_(*filters))  # 构造当前业务的基础数据库查询对象
    if exclude_id:  # 更新场景下排除当前正在编辑的记录
        query = query.filter(FAQ.id != exclude_id)  # 保存当前逐步拼装的数据库查询对象
    return query.order_by(FAQ.id.asc()).first()  # 返回当前分支整理好的结果


def _find_duplicate_source(db: Session, tenant_id: int, payload: dict, exclude_id: Optional[int] = None) -> Optional[Source]:  # 定义资料来源去重查询函数
    filters = []  # 初始化用于去重判断的筛选条件列表
    if payload.get("source_code"):  # 仅在对应字段存在时追加去重匹配条件
        filters.append(Source.source_code == payload["source_code"])  # 向去重筛选条件列表追加一条匹配规则
    if payload.get("url"):  # 仅在对应字段存在时追加去重匹配条件
        filters.append(Source.url == payload["url"])  # 向去重筛选条件列表追加一条匹配规则
    if payload.get("title"):  # 仅在对应字段存在时追加去重匹配条件
        filters.append((Source.title == payload["title"]) & (Source.issuer == (payload.get("issuer") or "")))  # 向去重筛选条件列表追加一条匹配规则
    if not filters:  # 没有可用去重条件时直接结束查询
        return None  # 返回当前分支整理好的结果
    query = db.query(Source).filter(Source.tenant_id == tenant_id, or_(*filters))  # 构造当前业务的基础数据库查询对象
    if exclude_id:  # 更新场景下排除当前正在编辑的记录
        query = query.filter(Source.id != exclude_id)  # 保存当前逐步拼装的数据库查询对象
    return query.order_by(Source.id.asc()).first()  # 返回当前分支整理好的结果


def _is_source_reviewed(value: Optional[str]) -> bool:  # 定义资料是否已复核的判断函数
    return value in {"已复核", "reviewed"}  # 返回当前分支整理好的结果


def _reviewer_name(current_admin: dict) -> str:  # 定义复核人名称展示函数
    return current_admin.get("display_name") or current_admin.get("username") or f"管理员{current_admin.get('id')}"  # 返回当前分支整理好的结果


def _source_similarity(left: str, right: str) -> float:  # 定义来源资料相似度计算函数
    left = (left or "").strip()  # 更新当前逻辑中的 left
    right = (right or "").strip()  # 更新当前逻辑中的 right
    if not left or not right:  # 根据当前条件决定是否进入对应业务分支
        return 0  # 返回当前分支整理好的结果
    if left == right:  # 根据当前条件决定是否进入对应业务分支
        return 1  # 返回当前分支整理好的结果
    if left in right or right in left:  # 根据当前条件决定是否进入对应业务分支
        return 0.92  # 返回当前分支整理好的结果
    return SequenceMatcher(None, left, right).ratio()  # 返回当前分支整理好的结果


def _source_url_similarity(left: str, right: str) -> float:  # 定义业务处理函数 _source_url_similarity
    left = (left or "").strip()  # 更新当前逻辑中的 left
    right = (right or "").strip()  # 更新当前逻辑中的 right
    if not left or not right:  # 根据当前条件决定是否进入对应业务分支
        return 0  # 返回当前分支整理好的结果
    if left == right:  # 根据当前条件决定是否进入对应业务分支
        return 1  # 返回当前分支整理好的结果
    left_parts = urlparse(left)  # 更新当前逻辑中的 left parts
    right_parts = urlparse(right)  # 更新当前逻辑中的 right parts
    if left_parts.netloc != right_parts.netloc:  # 根据当前条件决定是否进入对应业务分支
        return 0  # 返回当前分支整理好的结果
    left_path = left_parts.path.strip("/")  # 更新当前逻辑中的 left path
    right_path = right_parts.path.strip("/")  # 更新当前逻辑中的 right path
    if len(left_path) < 8 or len(right_path) < 8:  # 根据当前条件决定是否进入对应业务分支
        return 0  # 返回当前分支整理好的结果
    if left_path in right_path or right_path in left_path:  # 根据当前条件决定是否进入对应业务分支
        return 0.78  # 返回当前分支整理好的结果
    return 0  # 返回当前分支整理好的结果


def _sources_from_current_catalog(db: Session, tenant_id: int, log: ChatLog) -> list[dict]:  # 定义业务处理函数 _sources_from_current_catalog
    """Return source snapshots with URLs corrected from the maintained source catalog."""  # 函数文档字符串，说明 _sources_from_current_catalog 的职责
    raw_sources = log.sources if isinstance(log.sources, list) else []  # 更新当前逻辑中的 raw sources
    catalog = db.query(Source).filter(Source.tenant_id == tenant_id).all()  # 构造当前业务的基础数据库查询对象
    used_ids: set[int] = set()  # 更新当前逻辑中的 used ids
    corrected: list[dict] = []  # 更新当前逻辑中的 corrected

    def source_to_dict(source: Source, snapshot: Optional[dict] = None) -> dict:  # 定义业务处理函数 source_to_dict
        used_ids.add(source.id)  # 执行当前业务步骤并推进后续处理
        return {  # 返回当前分支整理好的结果
            "id": source.id,  # 填充返回或配置中的 主键 ID 字段
            "title": source.title,  # 填充返回或配置中的 标题 字段
            "url": source.url,  # 填充返回或配置中的 链接地址 字段
            "snippet": source.description or (snapshot or {}).get("snippet"),  # 填充返回或配置中的 snippet 字段
            "review_status": source.review_status,  # 填充返回或配置中的 review status 字段
        }  # 结束 返回结果 的定义或组装

    for item in raw_sources:  # 遍历当前集合中的每一项并逐个处理
        if not isinstance(item, dict):  # 根据当前条件决定是否进入对应业务分支
            continue  # 跳过当前项，继续处理下一项数据
        title = item.get("title") or ""  # 更新当前逻辑中的 标题
        url = item.get("url") or ""  # 更新当前逻辑中的 链接地址
        best = None  # 更新当前逻辑中的 best
        best_score = 0.0  # 更新当前逻辑中的 best score
        for source in catalog:  # 遍历当前集合中的每一项并逐个处理
            score = max(_source_similarity(title, source.title), _source_url_similarity(url, source.url or ""))  # 更新当前逻辑中的 score
            if score > best_score:  # 根据当前条件决定是否进入对应业务分支
                best = source  # 更新当前逻辑中的 best
                best_score = score  # 更新当前逻辑中的 best score
        if best and best_score >= 0.62:  # 根据当前条件决定是否进入对应业务分支
            corrected.append(source_to_dict(best, item))  # 执行当前业务步骤并推进后续处理
        elif title or url:  # 前一个条件不满足时继续判断其他分支
            corrected.append({  # 执行当前业务步骤并推进后续处理
                "title": title or url,  # 执行当前业务步骤并推进后续处理
                "url": url,  # 执行当前业务步骤并推进后续处理
                "snippet": item.get("snippet"),  # 执行当前业务步骤并推进后续处理
                "review_status": item.get("review_status"),  # 执行当前业务步骤并推进后续处理
            })  # 执行当前业务步骤并推进后续处理

    faq = (  # 更新当前逻辑中的 faq
        db.query(FAQ)  # 执行当前业务步骤并推进后续处理
        .filter(FAQ.tenant_id == tenant_id, FAQ.question == log.question)  # 执行当前业务步骤并推进后续处理
        .order_by(FAQ.id.asc())  # 执行当前业务步骤并推进后续处理
        .first()  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    if faq and faq.source_ids:  # 根据当前条件决定是否进入对应业务分支
        faq_sources = (  # 更新当前逻辑中的 faq sources
            db.query(Source)  # 执行当前业务步骤并推进后续处理
            .filter(Source.tenant_id == tenant_id, Source.id.in_(faq.source_ids))  # 执行当前业务步骤并推进后续处理
            .order_by(Source.id.asc())  # 执行当前业务步骤并推进后续处理
            .all()  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
        for source in faq_sources:  # 遍历当前集合中的每一项并逐个处理
            if source.id not in used_ids:  # 根据当前条件决定是否进入对应业务分支
                corrected.append(source_to_dict(source))  # 执行当前业务步骤并推进后续处理

    return corrected  # 返回当前分支整理好的结果


def _safe_upload_filename(filename: str) -> str:  # 定义业务处理函数 _safe_upload_filename
    raw_name = Path(filename or "source-file").name  # 更新当前逻辑中的 raw name
    stem = sanitize_text(Path(raw_name).stem) or "source"  # 清洗并规范化 stem 的输入值
    suffix = Path(raw_name).suffix.lower()  # 提取上传文件扩展名，校验导入格式是否允许
    if suffix not in ALLOWED_SOURCE_FILE_EXTENSIONS:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="不支持的文件类型")  # 抛出 HTTP 异常并把错误信息返回给前端
    safe_stem = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in stem).strip("_") or "source"  # 更新当前逻辑中的 safe stem
    return f"{uuid4().hex}_{safe_stem[:80]}{suffix}"  # 返回当前分支整理好的结果


@router.post("/login", response_model=AdminToken)  # 为后续函数或类声明附加装饰器配置
async def login(request: AdminLogin):  # 定义异步处理函数 login
    admin = authenticate_admin(request.username.strip(), request.password, request.tenant_code)  # 更新当前逻辑中的 admin
    if not admin:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=401, detail="用户名、密码或租户不正确")  # 抛出 HTTP 异常并把错误信息返回给前端

    access_token = create_access_token(  # 更新当前逻辑中的 access token
        data={  # 设置 create_access_token 的 data
            "sub": str(admin["id"]),  # 填充返回或配置中的 sub 字段
            "role": admin["role"],  # 填充返回或配置中的 role 字段
            "tenant_id": admin["tenant_id"],  # 填充返回或配置中的 租户 ID 字段
        }  # 结束 data 的定义或组装
    )  # 结束 create_access_token 的定义或组装

    return AdminToken(  # 返回当前分支整理好的结果
        access_token=access_token,  # 设置 AdminToken 的 access token
        admin_id=admin["id"],  # 设置 AdminToken 的 admin id
        username=admin["username"],  # 设置 AdminToken 的 username
        role=admin["role"],  # 设置 AdminToken 的 role
        role_label=role_label(admin["role"]),  # 设置 AdminToken 的 role label
        permissions=role_permissions(admin["role"]),  # 设置 AdminToken 的 permissions
        tenant_id=admin["tenant_id"],  # 设置 AdminToken 的 租户 ID
        tenant_code=admin["tenant_code"],  # 设置 AdminToken 的 tenant code
        tenant_name=admin["tenant_name"],  # 设置 AdminToken 的 租户名称
    )  # 结束 AdminToken 的定义或组装


@router.get("/verify-token")  # 为后续函数或类声明附加装饰器配置
async def verify_token(current_admin: dict = Depends(get_current_admin)):  # 定义异步处理函数 verify_token
    return ok(current_admin)  # 按统一成功响应格式返回结果


@router.get("/roles")  # 为后续函数或类声明附加装饰器配置
async def get_roles(current_admin: dict = Depends(get_current_admin)):  # 定义获取 roles 的接口或辅助函数
    roles = [  # 更新当前逻辑中的 roles
        {"value": role, "label": label, "permissions": ROLE_PERMISSIONS.get(role, [])}  # 补充列表中的 value 项
        for role, label in ROLE_LABELS.items()  # 补充列表中的 items() 项
    ]  # 结束 roles 的定义或组装
    if current_admin["role"] != "super_admin":  # 非超级管理员只能查看自己所属租户的数据
        roles = [item for item in roles if item["value"] != "super_admin"]  # 更新当前逻辑中的 roles
    return ok(roles)  # 按统一成功响应格式返回结果


@router.get("/statistics")  # 为后续函数或类声明附加装饰器配置
async def get_statistics(  # 定义获取 statistics 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_statistics 的参数声明
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围

    def scoped(model):  # 定义业务处理函数 scoped
        query = db.query(model)  # 构造当前业务的基础数据库查询对象
        return query.filter(model.tenant_id == allowed_tenant_id) if allowed_tenant_id else query  # 返回当前分支整理好的结果

    chat_query = scoped(ChatLog)  # 更新当前逻辑中的 chat query
    feedback_query = scoped(Feedback)  # 更新当前逻辑中的 feedback query
    faq_query = scoped(FAQ)  # 更新当前逻辑中的 faq query
    source_query = scoped(Source)  # 更新当前逻辑中的 source query

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # 更新当前逻辑中的 today
    total_feedbacks = feedback_query.count()  # 统计满足当前筛选条件的记录总数
    helpful = feedback_query.filter(Feedback.is_helpful.is_(True)).count()  # 统计满足当前筛选条件的记录总数
    helpful_rate = int(round((helpful / total_feedbacks) * 100)) if total_feedbacks else 0  # 更新当前逻辑中的 helpful rate
    avg_response = chat_query.with_entities(func.avg(ChatLog.response_time)).scalar() or 0  # 更新当前逻辑中的 avg response

    top_questions = (  # 更新当前逻辑中的 top questions
        chat_query.with_entities(ChatLog.question, func.count(ChatLog.id).label("count"))  # 执行当前业务步骤并推进后续处理
        .group_by(ChatLog.question)  # 执行当前业务步骤并推进后续处理
        .order_by(desc("count"))  # 执行当前业务步骤并推进后续处理
        .limit(5)  # 执行当前业务步骤并推进后续处理
        .all()  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理

    data = {  # 整理当前接口最终要返回的数据结构
        "total_questions": chat_query.count(),  # 填充返回或配置中的 total questions 字段
        "today_questions": chat_query.filter(ChatLog.created_at >= today).count(),  # 填充返回或配置中的 today questions 字段
        "total_feedbacks": total_feedbacks,  # 填充返回或配置中的 total feedbacks 字段
        "pending_feedbacks": feedback_query.filter(Feedback.status == "pending").count(),  # 填充返回或配置中的 pending feedbacks 字段
        "total_faqs": faq_query.count(),  # 填充返回或配置中的 total faqs 字段
        "total_sources": source_query.count(),  # 填充返回或配置中的 total sources 字段
        "total_tenants": db.query(Tenant).count() if current_admin["role"] == "super_admin" else 1,  # 填充返回或配置中的 total tenants 字段
        "helpful_rate": helpful_rate,  # 填充返回或配置中的 helpful rate 字段
        "avg_response_time": int(avg_response),  # 填充返回或配置中的 avg response time 字段
        "top_questions": [{"question": row.question, "count": row.count} for row in top_questions],  # 填充返回或配置中的 top questions 字段
        "services": check_external_services(),  # 填充返回或配置中的 services 字段
    }  # 结束 data 的定义或组装
    return ok(data)  # 按统一成功响应格式返回结果


@router.get("/tenants")  # 为后续函数或类声明附加装饰器配置
async def get_tenants(  # 定义获取 tenants 的接口或辅助函数
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_tenants 的参数声明
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _tenant_query(db, current_admin)  # 保存当前逐步拼装的数据库查询对象
    if keyword:  # 有关键字时继续追加模糊搜索条件
        like = f"%{keyword}%"  # 构造用于模糊匹配的 SQL 关键字模式
        query = query.filter((Tenant.name.like(like)) | (Tenant.code.like(like)))  # 保存当前逐步拼装的数据库查询对象
    if status:  # 根据状态参数决定是否追加筛选条件
        query = query.filter(Tenant.status == status)  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    tenants = query.order_by(Tenant.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    return page_response([_serialize_tenant(item) for item in tenants], total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.post("/tenants")  # 为后续函数或类声明附加装饰器配置
async def create_tenant(  # 定义创建 tenant 的接口或辅助函数
    request: TenantCreate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 create_tenant 的参数声明
    require_role(current_admin["role"], SUPER_ADMIN_ROLES)  # 执行当前业务步骤并推进后续处理
    code = request.code.strip()  # 更新当前逻辑中的 code
    if db.query(Tenant).filter(Tenant.code == code).first():  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="租户编码已存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    tenant = Tenant(  # 保存当前请求实际使用的租户对象
        code=code,  # 设置 Tenant 的 code
        name=request.name.strip(),  # 设置 Tenant 的 名称
        industry=request.industry,  # 设置 Tenant 的 industry
        region=request.region,  # 设置 Tenant 的 地区
        contact_name=request.contact_name,  # 设置 Tenant 的 contact name
        contact_email=request.contact_email,  # 设置 Tenant 的 contact email
        contact_phone=request.contact_phone,  # 设置 Tenant 的 contact phone
        status=request.status,  # 设置 Tenant 的 状态
        notes=sanitize_text(request.notes),  # 设置 Tenant 的 notes
    )  # 结束 Tenant 的定义或组装
    db.add(tenant)  # 把新实体加入当前数据库事务等待提交
    db.flush()  # 执行当前业务步骤并推进后续处理

    if request.admin_username and request.admin_password:  # 根据当前条件决定是否进入对应业务分支
        db.add(  # 把新实体加入当前数据库事务等待提交
            Admin(  # 执行当前业务步骤并推进后续处理
                tenant_id=tenant.id,  # 更新当前逻辑中的 租户 ID
                username=request.admin_username.strip(),  # 更新当前逻辑中的 username
                password_hash=get_password_hash(request.admin_password),  # 执行当前控制流分支
                role="tenant_admin",  # 更新当前逻辑中的 role
                display_name=f"{tenant.name}管理员",  # 更新当前逻辑中的 display name
                is_active=True,  # 更新当前逻辑中的 is active
            )  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理

    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(tenant)  # 回填数据库生成的主键和默认字段
    return ok(_serialize_tenant(tenant), "租户创建成功")  # 按统一成功响应格式返回结果


@router.put("/tenants/{tenant_id}")  # 为后续函数或类声明附加装饰器配置
async def update_tenant(  # 定义更新 tenant 的接口或辅助函数
    tenant_id: int,  # 接收需要筛选或校验的租户 ID
    request: TenantUpdate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 update_tenant 的参数声明
    if current_admin["role"] != "super_admin" and tenant_id != current_admin.get("tenant_id"):  # 非超级管理员只能查看自己所属租户的数据
        raise HTTPException(status_code=403, detail="不能修改其他租户")  # 抛出 HTTP 异常并把错误信息返回给前端
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()  # 构造当前业务的基础数据库查询对象
    if not tenant:  # 租户不存在或不可用时直接终止请求
        raise HTTPException(status_code=404, detail="租户不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    for field, value in request.model_dump(exclude_unset=True).items():  # 遍历当前集合中的每一项并逐个处理
        setattr(tenant, field, sanitize_text(value) if isinstance(value, str) else value)  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(tenant)  # 回填数据库生成的主键和默认字段
    return ok(_serialize_tenant(tenant), "租户更新成功")  # 按统一成功响应格式返回结果


@router.get("/admins")  # 为后续函数或类声明附加装饰器配置
async def get_admins(  # 定义获取 admins 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_admins 的参数声明
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)  # 执行当前业务步骤并推进后续处理
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = db.query(Admin)  # 构造当前业务的基础数据库查询对象
    if current_admin["role"] == "super_admin":  # 非超级管理员只能查看自己所属租户的数据
        if tenant_id is not None:  # 根据当前条件决定是否进入对应业务分支
            query = query.filter(Admin.tenant_id == tenant_id)  # 保存当前逐步拼装的数据库查询对象
    else:  # 处理其他未命中的业务情况
        query = query.filter(Admin.tenant_id == current_admin["tenant_id"], Admin.role != "super_admin")  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    admins = query.order_by(Admin.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    return page_response([_serialize_admin(item) for item in admins], total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.post("/admins")  # 为后续函数或类声明附加装饰器配置
async def create_admin_account(  # 定义创建 admin account 的接口或辅助函数
    request: AdminCreate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 create_admin_account 的参数声明
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)  # 执行当前业务步骤并推进后续处理
    role = request.role  # 更新当前逻辑中的 role
    if role not in ROLE_LABELS:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="无效的角色")  # 抛出 HTTP 异常并把错误信息返回给前端
    if role == "super_admin" and current_admin["role"] != "super_admin":  # 非超级管理员只能查看自己所属租户的数据
        raise HTTPException(status_code=403, detail="不能创建超级管理员")  # 抛出 HTTP 异常并把错误信息返回给前端

    tenant_id = request.tenant_id if current_admin["role"] == "super_admin" else current_admin["tenant_id"]  # 更新当前逻辑中的 租户 ID
    if role != "super_admin" and not tenant_id:  # 租户不存在或不可用时直接终止请求
        raise HTTPException(status_code=400, detail="非平台管理员必须绑定租户")  # 抛出 HTTP 异常并把错误信息返回给前端

    username = request.username.strip()  # 更新当前逻辑中的 username
    if db.query(Admin).filter(Admin.username == username, Admin.tenant_id == tenant_id).first():  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="该租户下用户名已存在")  # 抛出 HTTP 异常并把错误信息返回给前端

    admin = Admin(  # 更新当前逻辑中的 admin
        tenant_id=tenant_id,  # 设置 Admin 的 租户 ID
        username=username,  # 设置 Admin 的 username
        password_hash=get_password_hash(request.password),  # 设置 Admin 的 password hash
        role=role,  # 设置 Admin 的 role
        display_name=sanitize_text(request.display_name),  # 设置 Admin 的 display name
        email=request.email,  # 设置 Admin 的 email
        is_active=True,  # 设置 Admin 的 is active
    )  # 结束 Admin 的定义或组装
    db.add(admin)  # 把新实体加入当前数据库事务等待提交
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(admin)  # 回填数据库生成的主键和默认字段
    return ok(_serialize_admin(admin), "账号创建成功")  # 按统一成功响应格式返回结果


@router.put("/admins/{admin_id}")  # 为后续函数或类声明附加装饰器配置
async def update_admin_account(  # 定义更新 admin account 的接口或辅助函数
    admin_id: int,  # 声明参数 admin_id，供当前逻辑使用
    request: AdminUpdate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 update_admin_account 的参数声明
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)  # 执行当前业务步骤并推进后续处理
    admin = db.query(Admin).filter(Admin.id == admin_id).first()  # 构造当前业务的基础数据库查询对象
    if not admin:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="账号不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    if current_admin["role"] != "super_admin" and admin.tenant_id != current_admin["tenant_id"]:  # 非超级管理员只能查看自己所属租户的数据
        raise HTTPException(status_code=403, detail="不能修改其他租户账号")  # 抛出 HTTP 异常并把错误信息返回给前端
    if admin.role == "super_admin" and current_admin["role"] != "super_admin":  # 非超级管理员只能查看自己所属租户的数据
        raise HTTPException(status_code=403, detail="不能修改超级管理员")  # 抛出 HTTP 异常并把错误信息返回给前端

    update_data = request.model_dump(exclude_unset=True)  # 更新当前逻辑中的 update data
    if "role" in update_data and update_data["role"]:  # 根据当前条件决定是否进入对应业务分支
        if update_data["role"] == "super_admin" and current_admin["role"] != "super_admin":  # 非超级管理员只能查看自己所属租户的数据
            raise HTTPException(status_code=403, detail="不能授予超级管理员")  # 抛出 HTTP 异常并把错误信息返回给前端
        admin.role = update_data["role"]  # 更新当前逻辑中的 role
    if update_data.get("password"):  # 根据当前条件决定是否进入对应业务分支
        admin.password_hash = get_password_hash(update_data["password"])  # 更新当前逻辑中的 password hash
    for field in ["display_name", "email", "is_active"]:  # 遍历当前集合中的每一项并逐个处理
        if field in update_data:  # 根据当前条件决定是否进入对应业务分支
            setattr(admin, field, sanitize_text(update_data[field]) if isinstance(update_data[field], str) else update_data[field])  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(admin)  # 回填数据库生成的主键和默认字段
    return ok(_serialize_admin(admin), "账号更新成功")  # 按统一成功响应格式返回结果


@router.delete("/admins/{admin_id}")  # 为后续函数或类声明附加装饰器配置
async def delete_admin_account(  # 定义异步处理函数 delete_admin_account
    admin_id: int,  # 声明参数 admin_id，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 delete_admin_account 的参数声明
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)  # 执行当前业务步骤并推进后续处理
    if admin_id == current_admin["id"]:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")  # 抛出 HTTP 异常并把错误信息返回给前端
    admin = db.query(Admin).filter(Admin.id == admin_id).first()  # 构造当前业务的基础数据库查询对象
    if not admin:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="账号不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    if current_admin["role"] != "super_admin" and admin.tenant_id != current_admin["tenant_id"]:  # 非超级管理员只能查看自己所属租户的数据
        raise HTTPException(status_code=403, detail="不能删除其他租户账号")  # 抛出 HTTP 异常并把错误信息返回给前端
    if admin.role == "super_admin":  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=403, detail="不能删除超级管理员")  # 抛出 HTTP 异常并把错误信息返回给前端
    db.delete(admin)  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok(message="账号删除成功")  # 按统一成功响应格式返回结果


@router.get("/logs")  # 为后续函数或类声明附加装饰器配置
async def get_logs(  # 定义获取 logs 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    user_id: Optional[str] = None,  # 接收当前提问用户的标识信息
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    start_date: Optional[str] = None,  # 声明参数 start_date，供当前逻辑使用
    end_date: Optional[str] = None,  # 声明参数 end_date，供当前逻辑使用
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_logs 的参数声明
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _tenant_scoped_query(db, ChatLog, current_admin, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if user_id:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(ChatLog.user_id == user_id)  # 保存当前逐步拼装的数据库查询对象
    if keyword:  # 有关键字时继续追加模糊搜索条件
        query = query.filter(ChatLog.question.contains(keyword))  # 保存当前逐步拼装的数据库查询对象
    if status:  # 根据状态参数决定是否追加筛选条件
        query = query.filter(ChatLog.status == status)  # 保存当前逐步拼装的数据库查询对象
    if start_date:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(ChatLog.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))  # 保存当前逐步拼装的数据库查询对象
    if end_date:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(ChatLog.created_at < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    logs = query.order_by(ChatLog.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    return page_response(  # 按统一分页响应格式返回列表数据
        [  # 设置 page_response 的 字段
            {  # 设置 page_response 的 字段
                "id": item.id,  # 设置 page_response 的 主键 ID
                "tenant_id": item.tenant_id,  # 设置 page_response 的 租户 ID
                "tenant_name": item.tenant.name if item.tenant else "",  # 设置 page_response 的 租户名称
                "user_id": item.user_id,  # 设置 page_response 的 用户 ID
                "question": item.question,  # 设置 page_response 的 问题内容
                "answer": item.answer,  # 设置 page_response 的 回答内容
                "provider": item.provider,  # 设置 page_response 的 服务提供方
                "risk_level": item.risk_level,  # 设置 page_response 的 风险等级
                "response_time": item.response_time,  # 设置 page_response 的 响应耗时
                "status": item.status,  # 设置 page_response 的 状态
                "created_at": item.created_at,  # 设置 page_response 的 创建时间
            }  # 设置 page_response 的 字段
            for item in logs  # 设置 page_response 的 字段
        ],  # 设置 page_response 的 字段
        total,  # 设置 page_response 的 字段
        page,  # 设置 page_response 的 字段
        page_size,  # 设置 page_response 的 字段
    )  # 结束 page_response 的定义或组装


@router.get("/logs/{log_id}")  # 为后续函数或类声明附加装饰器配置
async def get_log_detail(  # 定义获取 log detail 的接口或辅助函数
    log_id: int,  # 声明参数 log_id，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_log_detail 的参数声明
    log = db.query(ChatLog).filter(ChatLog.id == log_id).first()  # 构造当前业务的基础数据库查询对象
    if not log:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="日志不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, log.tenant_id)  # 执行当前业务步骤并推进后续处理
    return ok(  # 按统一成功响应格式返回结果
        {  # 设置 ok 的 字段
            "id": log.id,  # 设置 ok 的 主键 ID
            "tenant_id": log.tenant_id,  # 设置 ok 的 租户 ID
            "tenant_name": log.tenant.name if log.tenant else "",  # 设置 ok 的 租户名称
            "user_id": log.user_id,  # 设置 ok 的 用户 ID
            "session_id": log.session_id,  # 设置 ok 的 会话 ID
            "conversation_id": log.conversation_id,  # 设置 ok 的 会话 ID
            "language": log.language,  # 设置 ok 的 语言代码
            "question": log.question,  # 设置 ok 的 问题内容
            "answer": log.answer,  # 设置 ok 的 回答内容
            "sources": _sources_from_current_catalog(db, log.tenant_id, log),  # 设置 ok 的 来源列表
            "related_tasks": log.related_tasks,  # 设置 ok 的 关联任务列表
            "provider": log.provider,  # 设置 ok 的 服务提供方
            "risk_level": log.risk_level,  # 设置 ok 的 风险等级
            "response_time": log.response_time,  # 设置 ok 的 响应耗时
            "status": log.status,  # 设置 ok 的 状态
            "created_at": log.created_at,  # 设置 ok 的 创建时间
        }  # 设置 ok 的 字段
    )  # 结束 ok 的定义或组装


@router.get("/faqs")  # 为后续函数或类声明附加装饰器配置
async def get_faqs(  # 定义获取 faqs 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    category: Optional[str] = None,  # 声明参数 category，供当前逻辑使用
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_faqs 的参数声明
    _require_permission(current_admin, "faqs")  # 执行当前业务步骤并推进后续处理
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _tenant_scoped_query(db, FAQ, current_admin, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if category:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(FAQ.category == category)  # 保存当前逐步拼装的数据库查询对象
    if keyword:  # 有关键字时继续追加模糊搜索条件
        query = query.filter(or_(FAQ.question.contains(keyword), FAQ.faq_code.contains(keyword)))  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    items = query.order_by(FAQ.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    return page_response(items, total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.get("/faqs/export")  # 为后续函数或类声明附加装饰器配置
async def export_faqs(  # 定义异步处理函数 export_faqs
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    category: Optional[str] = None,  # 声明参数 category，供当前逻辑使用
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    ids: Optional[str] = None,  # 声明参数 ids，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 export_faqs 的参数声明
    _require_permission(current_admin, "faqs_export")  # 执行当前业务步骤并推进后续处理
    query = _module_query(db, FAQ, current_admin, ids, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if category:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(FAQ.category == category)  # 保存当前逐步拼装的数据库查询对象
    if keyword:  # 有关键字时继续追加模糊搜索条件
        query = query.filter(or_(FAQ.question.contains(keyword), FAQ.faq_code.contains(keyword)))  # 保存当前逐步拼装的数据库查询对象
    rows = [  # 更新当前逻辑中的 rows
        {  # 补充列表中的 { 项
            "id": item.id,  # 补充列表中的 主键 ID 项
            "faq_code": item.faq_code,  # 补充列表中的 FAQ 编码 项
            "question": item.question,  # 补充列表中的 问题内容 项
            "answer": item.answer,  # 补充列表中的 回答内容 项
            "category": item.category,  # 补充列表中的 分类 项
            "region": item.region,  # 补充列表中的 地区 项
            "risk_level": item.risk_level,  # 补充列表中的 风险等级 项
            "keywords": item.keywords or [],  # 补充列表中的 关键字 项
            "language": item.language,  # 补充列表中的 语言代码 项
            "effective_date": item.effective_date,  # 补充列表中的 effective date 项
        }  # 补充列表中的 } 项
        for item in query.order_by(FAQ.id.asc()).all()  # 补充列表中的 all() 项
    ]  # 结束 rows 的定义或组装
    return _csv_text_response("faqs.csv", rows, FAQ_EXPORT_FIELDS)  # 返回当前分支整理好的结果


@router.post("/faqs/import")  # 为后续函数或类声明附加装饰器配置
async def import_faqs(  # 定义异步处理函数 import_faqs
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    file: UploadFile = File(...),  # 声明参数 file，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 import_faqs 的参数声明
    _require_permission(current_admin, "faqs_import")  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    rows = await _read_import_rows(file)  # 更新当前逻辑中的 rows
    imported = 0  # 更新当前逻辑中的 imported
    updated = 0  # 更新当前逻辑中的 updated
    skipped = 0  # 更新当前逻辑中的 skipped
    errors: list[str] = []  # 更新当前逻辑中的 errors
    for index, row in enumerate(rows, start=2):  # 遍历当前集合中的每一项并逐个处理
        # CSV 导入同时兼容英文字段和中文字段，方便运营人员直接用表格维护 FAQ。
        question = sanitize_text(row.get("question") or row.get("问题"))  # 清洗并规范化 问题内容 的输入值
        answer = sanitize_text(row.get("answer") or row.get("回答") or row.get("答案"))  # 清洗并规范化 回答内容 的输入值
        if not question or not answer:  # 根据当前条件决定是否进入对应业务分支
            skipped += 1  # 执行当前业务步骤并推进后续处理
            errors.append(f"第 {index} 行缺少 question/answer")  # 执行当前业务步骤并推进后续处理
            continue  # 跳过当前项，继续处理下一项数据
        payload = {  # 组装发往外部问答服务的请求载荷
            "faq_code": row.get("faq_code") or row.get("编码") or None,  # 向 Dify 请求体写入 FAQ 编码
            "question": question,  # 向 Dify 请求体写入 问题内容
            "answer": answer,  # 向 Dify 请求体写入 回答内容
            "category": row.get("category") or row.get("分类") or None,  # 向 Dify 请求体写入 分类
            "region": row.get("region") or row.get("地区") or "陕西",  # 向 Dify 请求体写入 地区
            "risk_level": row.get("risk_level") or row.get("风险等级") or "medium",  # 向 Dify 请求体写入 风险等级
            "keywords": _read_json_list(row.get("keywords") or row.get("关键词")),  # 向 Dify 请求体写入 关键字
            "aliases": _read_json_list(row.get("aliases")),  # 向 Dify 请求体写入 aliases
            "source_ids": _read_json_list(row.get("source_ids")),  # 向 Dify 请求体写入 source ids
            "language": row.get("language") or "zh-CN",  # 向 Dify 请求体写入 语言代码
            "effective_date": row.get("effective_date") or None,  # 向 Dify 请求体写入 effective date
        }  # 结束 payload 的定义或组装
        faq = _find_duplicate_faq(db, allowed_tenant_id, payload)  # 更新当前逻辑中的 faq
        if faq:  # 根据当前条件决定是否进入对应业务分支
            for field, value in payload.items():  # 遍历当前集合中的每一项并逐个处理
                setattr(faq, field, value)  # 执行当前业务步骤并推进后续处理
            updated += 1  # 执行当前业务步骤并推进后续处理
        else:  # 处理其他未命中的业务情况
            db.add(FAQ(tenant_id=allowed_tenant_id, **payload))  # 把新实体加入当前数据库事务等待提交
            imported += 1  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    # 数据库提交后再同步 RAG，确保导出的 faq_runtime.csv 读取到的是最新数据。
    sync_result = sync_after_faq_change(db, action="import_faqs", tenant_id=allowed_tenant_id)  # 更新当前逻辑中的 sync result
    # rag_sync 返回给前端/验收脚本，用于证明本次 FAQ 导入已经触发知识库刷新。
    return ok({"imported": imported, "updated": updated, "skipped": skipped, "errors": errors[:20], "rag_sync": sync_result}, "FAQ 导入完成")  # 按统一成功响应格式返回结果


@router.post("/faqs/batch")  # 为后续函数或类声明附加装饰器配置
async def batch_faqs(  # 定义异步处理函数 batch_faqs
    request: dict,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 batch_faqs 的参数声明
    _require_permission(current_admin, "faqs_batch")  # 执行当前业务步骤并推进后续处理
    ids = request.get("ids") or []  # 更新当前逻辑中的 ids
    action = request.get("action")  # 更新当前逻辑中的 action
    if not ids:  # 没有传入 ID 列表时直接返回空结果
        raise HTTPException(status_code=400, detail="请选择要批量操作的数据")  # 抛出 HTTP 异常并把错误信息返回给前端
    query = _tenant_scoped_query(db, FAQ, current_admin).filter(FAQ.id.in_(ids))  # 保存当前逐步拼装的数据库查询对象
    items = query.all()  # 保存当前页查询出来的记录列表
    # items 先查出来，既用于批量操作，也用于后面判断涉及哪些租户。
    if action == "delete":  # 根据当前条件决定是否进入对应业务分支
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            db.delete(item)  # 执行当前业务步骤并推进后续处理
    elif action == "set_risk":  # 前一个条件不满足时继续判断其他分支
        risk_level = request.get("risk_level")  # 更新当前逻辑中的 风险等级
        if risk_level not in {"low", "medium", "high"}:  # 根据当前条件决定是否进入对应业务分支
            raise HTTPException(status_code=400, detail="无效的风险等级")  # 抛出 HTTP 异常并把错误信息返回给前端
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            item.risk_level = risk_level  # 更新当前逻辑中的 风险等级
    else:  # 处理其他未命中的业务情况
        raise HTTPException(status_code=400, detail="不支持的批量操作")  # 抛出 HTTP 异常并把错误信息返回给前端
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    # 如果只操作一个租户，就只导出该租户的 runtime FAQ；跨租户时导出全部，避免漏同步。
    tenant_ids = {item.tenant_id for item in items}  # 更新当前逻辑中的 tenant ids
    sync_result = sync_after_faq_change(db, action=f"batch_{action}", tenant_id=next(iter(tenant_ids)) if len(tenant_ids) == 1 else None)  # 更新当前逻辑中的 sync result
    return ok({"affected": len(items), "rag_sync": sync_result}, "批量操作完成")  # 按统一成功响应格式返回结果


@router.post("/faqs")  # 为后续函数或类声明附加装饰器配置
async def create_faq(  # 定义创建 faq 的接口或辅助函数
    request: FAQCreate,  # 接收当前接口的请求对象或请求体
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 create_faq 的参数声明
    _require_permission(current_admin, "faqs")  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    payload = {  # 组装发往外部问答服务的请求载荷
        # 入库前先做基础文本清洗，避免控制字符和多余空白影响检索。
        "faq_code": request.faq_code,  # 向 Dify 请求体写入 FAQ 编码
        "question": sanitize_text(request.question),  # 向 Dify 请求体写入 问题内容
        "answer": sanitize_text(request.answer),  # 向 Dify 请求体写入 回答内容
        "category": request.category,  # 向 Dify 请求体写入 分类
        "region": request.region,  # 向 Dify 请求体写入 地区
        "risk_level": request.risk_level,  # 向 Dify 请求体写入 风险等级
        "keywords": request.keywords,  # 向 Dify 请求体写入 关键字
        "aliases": request.aliases,  # 向 Dify 请求体写入 aliases
        "source_ids": request.source_ids,  # 向 Dify 请求体写入 source ids
        "language": request.language,  # 向 Dify 请求体写入 语言代码
        "effective_date": request.effective_date,  # 向 Dify 请求体写入 effective date
    }  # 结束 payload 的定义或组装
    faq = _find_duplicate_faq(db, allowed_tenant_id, payload)  # 更新当前逻辑中的 faq
    if faq:  # 根据当前条件决定是否进入对应业务分支
        # 如果同租户下已存在同编码或同问题 FAQ，则覆盖更新，避免重复 FAQ 干扰向量检索。
        for field, value in payload.items():  # 遍历当前集合中的每一项并逐个处理
            setattr(faq, field, value)  # 执行当前业务步骤并推进后续处理
        message = "FAQ 已存在，已覆盖更新"  # 更新当前逻辑中的 message
    else:  # 处理其他未命中的业务情况
        faq = FAQ(tenant_id=allowed_tenant_id, **payload)  # 更新当前逻辑中的 faq
        db.add(faq)  # 把新实体加入当前数据库事务等待提交
        message = "FAQ 添加成功"  # 更新当前逻辑中的 message
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(faq)  # 回填数据库生成的主键和默认字段
    # FAQ 新增或覆盖后立即刷新本地 RAG 索引，下一次问答即可命中新 FAQ。
    sync_result = sync_after_faq_change(db, action="create_faq", tenant_id=faq.tenant_id)  # 更新当前逻辑中的 sync result
    return ok({"faq": faq, "rag_sync": sync_result}, message)  # 按统一成功响应格式返回结果


@router.put("/faqs/{faq_id}")  # 为后续函数或类声明附加装饰器配置
async def update_faq(  # 定义更新 faq 的接口或辅助函数
    faq_id: int,  # 声明参数 faq_id，供当前逻辑使用
    request: FAQUpdate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 update_faq 的参数声明
    _require_permission(current_admin, "faqs")  # 执行当前业务步骤并推进后续处理
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()  # 构造当前业务的基础数据库查询对象
    if not faq:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="FAQ 不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, faq.tenant_id)  # 执行当前业务步骤并推进后续处理
    update_data = request.model_dump(exclude_unset=True)  # 更新当前逻辑中的 update data
    candidate = {  # 更新当前逻辑中的 candidate
        # 更新前先构造候选唯一键，防止同租户下出现重复问题。
        "faq_code": update_data.get("faq_code", faq.faq_code),  # 执行当前业务步骤并推进后续处理
        "question": sanitize_text(update_data.get("question", faq.question)),  # 执行当前业务步骤并推进后续处理
        "language": update_data.get("language", faq.language),  # 执行当前业务步骤并推进后续处理
    }  # 结束 candidate 的定义或组装
    if _find_duplicate_faq(db, faq.tenant_id, candidate, exclude_id=faq.id):  # 更新场景下排除当前正在编辑的记录
        raise HTTPException(status_code=400, detail="该租户下已存在相同 FAQ 编码或问题")  # 抛出 HTTP 异常并把错误信息返回给前端
    for field, value in update_data.items():  # 遍历当前集合中的每一项并逐个处理
        # question/answer 是检索主文本，需要清洗；JSON 类字段保持原结构。
        setattr(faq, field, sanitize_text(value) if field in {"question", "answer"} else value)  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(faq)  # 回填数据库生成的主键和默认字段
    # FAQ 更新后同步 runtime CSV 并清缓存，让前台问答立即使用新答案。
    sync_result = sync_after_faq_change(db, action="update_faq", tenant_id=faq.tenant_id)  # 更新当前逻辑中的 sync result
    return ok({"faq": faq, "rag_sync": sync_result}, "FAQ 更新成功")  # 按统一成功响应格式返回结果


@router.delete("/faqs/{faq_id}")  # 为后续函数或类声明附加装饰器配置
async def delete_faq(  # 定义异步处理函数 delete_faq
    faq_id: int,  # 声明参数 faq_id，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 delete_faq 的参数声明
    _require_permission(current_admin, "faqs")  # 执行当前业务步骤并推进后续处理
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()  # 构造当前业务的基础数据库查询对象
    if not faq:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="FAQ 不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, faq.tenant_id)  # 执行当前业务步骤并推进后续处理
    # 删除前先保存 tenant_id，因为 db.delete 后对象状态可能变化。
    tenant_id = faq.tenant_id  # 更新当前逻辑中的 租户 ID
    db.delete(faq)  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    # 删除后也必须同步，否则 runtime CSV 和缓存里还会保留旧 FAQ。
    sync_result = sync_after_faq_change(db, action="delete_faq", tenant_id=tenant_id)  # 更新当前逻辑中的 sync result
    return ok({"rag_sync": sync_result}, "FAQ 删除成功")  # 按统一成功响应格式返回结果


@router.get("/rag/sync-status")  # 为后续函数或类声明附加装饰器配置
async def get_rag_sync_status(  # 定义获取 rag sync status 的接口或辅助函数
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_rag_sync_status 的参数声明
    _require_permission(current_admin, "faqs")  # 执行当前业务步骤并推进后续处理
    # 状态接口只读，不触发重建；用于后台页面查看当前缓存和 runtime 文件情况。
    return ok(rag_sync_status(), "RAG 知识库同步状态")  # 按统一成功响应格式返回结果


@router.post("/rag/reload-local-cache")  # 为后续函数或类声明附加装饰器配置
async def reload_rag_local_cache(  # 定义异步处理函数 reload_rag_local_cache
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 reload_rag_local_cache 的参数声明
    _require_permission(current_admin, "faqs")  # 执行当前业务步骤并推进后续处理
    # 手动清缓存适合运营人员修改知识文件后，不想重启服务的场景。
    return ok(clear_local_index_cache(), "本地 RAG 索引缓存已清空")  # 按统一成功响应格式返回结果


@router.post("/rag/rebuild-milvus")  # 为后续函数或类声明附加装饰器配置
async def rebuild_rag_milvus(  # 定义异步处理函数 rebuild_rag_milvus
    request: dict | None = None,  # 接收当前接口的请求对象或请求体
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 rebuild_rag_milvus 的参数声明
    _require_permission(current_admin, "packages")  # 执行当前业务步骤并推进后续处理
    # reset_collections=True 表示先删除旧 collection 再全量写入，适合 MVP 验收环境。
    reset_collections = bool((request or {}).get("reset_collections"))  # 更新当前逻辑中的 reset collections
    # Milvus 重建可能较慢，因此只在用户显式点击按钮或调用接口时执行。
    result = rebuild_milvus_knowledge_base(reset_collections=reset_collections)  # 更新当前逻辑中的 result
    return ok(result, "Milvus 向量知识库重建完成")  # 按统一成功响应格式返回结果


@router.get("/sources")  # 为后续函数或类声明附加装饰器配置
async def get_sources(  # 定义获取 来源列表 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    doc_type: Optional[str] = None,  # 声明参数 doc_type，供当前逻辑使用
    region: Optional[str] = None,  # 声明参数 region，供当前逻辑使用
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_sources 的参数声明
    _require_permission(current_admin, "sources")  # 执行当前业务步骤并推进后续处理
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _tenant_scoped_query(db, Source, current_admin, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if doc_type:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(Source.doc_type == doc_type)  # 保存当前逐步拼装的数据库查询对象
    if region:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(Source.region == region)  # 保存当前逐步拼装的数据库查询对象
    if keyword:  # 有关键字时继续追加模糊搜索条件
        query = query.filter(or_(Source.title.contains(keyword), Source.source_code.contains(keyword), Source.url.contains(keyword)))  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    items = query.order_by(Source.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    return page_response(items, total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.get("/sources/export")  # 为后续函数或类声明附加装饰器配置
async def export_sources(  # 定义异步处理函数 export_sources
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    doc_type: Optional[str] = None,  # 声明参数 doc_type，供当前逻辑使用
    region: Optional[str] = None,  # 声明参数 region，供当前逻辑使用
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    ids: Optional[str] = None,  # 声明参数 ids，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 export_sources 的参数声明
    _require_permission(current_admin, "sources_export")  # 执行当前业务步骤并推进后续处理
    query = _module_query(db, Source, current_admin, ids, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if doc_type:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(Source.doc_type == doc_type)  # 保存当前逐步拼装的数据库查询对象
    if region:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(Source.region == region)  # 保存当前逐步拼装的数据库查询对象
    if keyword:  # 有关键字时继续追加模糊搜索条件
        query = query.filter(or_(Source.title.contains(keyword), Source.source_code.contains(keyword), Source.url.contains(keyword)))  # 保存当前逐步拼装的数据库查询对象
    rows = [  # 更新当前逻辑中的 rows
        {  # 补充列表中的 { 项
            "id": item.id,  # 补充列表中的 主键 ID 项
            "source_code": item.source_code,  # 补充列表中的 资料编码 项
            "title": item.title,  # 补充列表中的 标题 项
            "url": item.url,  # 补充列表中的 链接地址 项
            "doc_type": item.doc_type,  # 补充列表中的 doc type 项
            "issuer": item.issuer,  # 补充列表中的 issuer 项
            "region": item.region,  # 补充列表中的 地区 项
            "validity_status": item.validity_status,  # 补充列表中的 validity status 项
            "review_status": item.review_status,  # 补充列表中的 review status 项
            "reviewed_at": item.reviewed_at,  # 补充列表中的 reviewed at 项
            "reviewed_by": item.reviewed_by,  # 补充列表中的 reviewed by 项
            "local_file": item.local_file,  # 补充列表中的 local file 项
            "description": item.description,  # 补充列表中的 说明描述 项
        }  # 补充列表中的 } 项
        for item in query.order_by(Source.id.asc()).all()  # 补充列表中的 all() 项
    ]  # 结束 rows 的定义或组装
    return _csv_text_response("sources.csv", rows, SOURCE_EXPORT_FIELDS)  # 返回当前分支整理好的结果


@router.post("/sources/import")  # 为后续函数或类声明附加装饰器配置
async def import_sources(  # 定义异步处理函数 import_sources
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    file: UploadFile = File(...),  # 声明参数 file，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 import_sources 的参数声明
    _require_permission(current_admin, "sources_import")  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    rows = await _read_import_rows(file)  # 更新当前逻辑中的 rows
    imported = 0  # 更新当前逻辑中的 imported
    updated = 0  # 更新当前逻辑中的 updated
    skipped = 0  # 更新当前逻辑中的 skipped
    errors: list[str] = []  # 更新当前逻辑中的 errors
    for index, row in enumerate(rows, start=2):  # 遍历当前集合中的每一项并逐个处理
        title = sanitize_text(row.get("title") or row.get("标题"))  # 清洗并规范化 标题 的输入值
        url = (row.get("url") or row.get("链接") or "").strip()  # 更新当前逻辑中的 链接地址
        local_file = (row.get("local_file") or row.get("本地文件") or "").strip()  # 更新当前逻辑中的 local file
        if not title or (not url and not local_file):  # 根据当前条件决定是否进入对应业务分支
            skipped += 1  # 执行当前业务步骤并推进后续处理
            errors.append(f"第 {index} 行缺少 title 或来源路径")  # 执行当前业务步骤并推进后续处理
            continue  # 跳过当前项，继续处理下一项数据
        payload = {  # 组装发往外部问答服务的请求载荷
            "source_code": row.get("source_code") or row.get("编码") or None,  # 向 Dify 请求体写入 资料编码
            "title": title,  # 向 Dify 请求体写入 标题
            "url": url or None,  # 向 Dify 请求体写入 链接地址
            "doc_type": row.get("doc_type") or row.get("类型") or None,  # 向 Dify 请求体写入 doc type
            "issuer": row.get("issuer") or row.get("发布机关") or "",  # 向 Dify 请求体写入 issuer
            "region": row.get("region") or row.get("地区") or None,  # 向 Dify 请求体写入 地区
            "validity_status": row.get("validity_status") or "有效",  # 向 Dify 请求体写入 validity status
            "review_status": row.get("review_status") or "待人工复核",  # 向 Dify 请求体写入 review status
            "owner": row.get("owner") or None,  # 向 Dify 请求体写入 owner
            "local_file": local_file or None,  # 向 Dify 请求体写入 local file
            "description": sanitize_text(row.get("description") or row.get("说明")),  # 向 Dify 请求体写入 说明描述
        }  # 结束 payload 的定义或组装
        if _is_source_reviewed(payload.get("review_status")):  # 根据状态参数决定是否追加筛选条件
            payload["reviewed_at"] = datetime.utcnow()  # 执行当前业务步骤并推进后续处理
            payload["reviewed_by"] = _reviewer_name(current_admin)  # 执行当前业务步骤并推进后续处理
        source = _find_duplicate_source(db, allowed_tenant_id, payload)  # 更新当前逻辑中的 source
        if source:  # 根据当前条件决定是否进入对应业务分支
            if _is_source_reviewed(source.review_status):  # 根据状态参数决定是否追加筛选条件
                skipped += 1  # 执行当前业务步骤并推进后续处理
                errors.append(f"第 {index} 行匹配到已复核来源，已跳过")  # 执行当前业务步骤并推进后续处理
                continue  # 跳过当前项，继续处理下一项数据
            for field, value in payload.items():  # 遍历当前集合中的每一项并逐个处理
                setattr(source, field, value)  # 执行当前业务步骤并推进后续处理
            updated += 1  # 执行当前业务步骤并推进后续处理
        else:  # 处理其他未命中的业务情况
            db.add(Source(tenant_id=allowed_tenant_id, **payload))  # 把新实体加入当前数据库事务等待提交
            imported += 1  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok({"imported": imported, "updated": updated, "skipped": skipped, "errors": errors[:20]}, "来源导入完成")  # 按统一成功响应格式返回结果


@router.post("/sources/batch")  # 为后续函数或类声明附加装饰器配置
async def batch_sources(  # 定义异步处理函数 batch_sources
    request: dict,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 batch_sources 的参数声明
    _require_permission(current_admin, "sources_batch")  # 执行当前业务步骤并推进后续处理
    ids = request.get("ids") or []  # 更新当前逻辑中的 ids
    action = request.get("action")  # 更新当前逻辑中的 action
    if not ids:  # 没有传入 ID 列表时直接返回空结果
        raise HTTPException(status_code=400, detail="请选择要批量操作的数据")  # 抛出 HTTP 异常并把错误信息返回给前端
    items = _tenant_scoped_query(db, Source, current_admin).filter(Source.id.in_(ids)).all()  # 保存当前页查询出来的记录列表
    if action == "delete":  # 根据当前条件决定是否进入对应业务分支
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            if _is_source_reviewed(item.review_status):  # 根据状态参数决定是否追加筛选条件
                raise HTTPException(status_code=400, detail="已复核的数据不支持批量删除")  # 抛出 HTTP 异常并把错误信息返回给前端
            db.delete(item)  # 执行当前业务步骤并推进后续处理
    elif action == "mark_reviewed":  # 前一个条件不满足时继续判断其他分支
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            item.review_status = "已复核"  # 更新当前逻辑中的 review status
            item.reviewed_at = datetime.utcnow()  # 更新当前逻辑中的 reviewed at
            item.reviewed_by = _reviewer_name(current_admin)  # 更新当前逻辑中的 reviewed by
    elif action == "mark_pending":  # 前一个条件不满足时继续判断其他分支
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            item.review_status = "待人工复核"  # 更新当前逻辑中的 review status
            item.reviewed_at = None  # 更新当前逻辑中的 reviewed at
            item.reviewed_by = None  # 更新当前逻辑中的 reviewed by
    else:  # 处理其他未命中的业务情况
        raise HTTPException(status_code=400, detail="不支持的批量操作")  # 抛出 HTTP 异常并把错误信息返回给前端
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok({"affected": len(items)}, "批量操作完成")  # 按统一成功响应格式返回结果


@router.post("/sources")  # 为后续函数或类声明附加装饰器配置
async def create_source(  # 定义创建 source 的接口或辅助函数
    request: SourceCreate,  # 接收当前接口的请求对象或请求体
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 create_source 的参数声明
    _require_permission(current_admin, "sources")  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    payload = request.model_dump()  # 组装发往外部问答服务的请求载荷
    payload["issuer"] = payload.get("issuer") or ""  # 执行当前业务步骤并推进后续处理
    if _is_source_reviewed(payload.get("review_status")):  # 根据状态参数决定是否追加筛选条件
        payload["reviewed_at"] = datetime.utcnow()  # 执行当前业务步骤并推进后续处理
        payload["reviewed_by"] = _reviewer_name(current_admin)  # 执行当前业务步骤并推进后续处理
    else:  # 处理其他未命中的业务情况
        payload["reviewed_at"] = None  # 执行当前业务步骤并推进后续处理
        payload["reviewed_by"] = None  # 执行当前业务步骤并推进后续处理
    source = _find_duplicate_source(db, allowed_tenant_id, payload)  # 更新当前逻辑中的 source
    if source:  # 根据当前条件决定是否进入对应业务分支
        if _is_source_reviewed(source.review_status):  # 根据状态参数决定是否追加筛选条件
            raise HTTPException(status_code=400, detail="已复核的数据不支持编辑，请在详情中查看复核记录")  # 抛出 HTTP 异常并把错误信息返回给前端
        for field, value in payload.items():  # 遍历当前集合中的每一项并逐个处理
            setattr(source, field, value)  # 执行当前业务步骤并推进后续处理
        message = "来源已存在，已覆盖更新"  # 更新当前逻辑中的 message
    else:  # 处理其他未命中的业务情况
        source = Source(tenant_id=allowed_tenant_id, **payload)  # 更新当前逻辑中的 source
        db.add(source)  # 把新实体加入当前数据库事务等待提交
        message = "来源添加成功"  # 更新当前逻辑中的 message
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(source)  # 回填数据库生成的主键和默认字段
    return ok(source, message)  # 按统一成功响应格式返回结果


@router.post("/sources/upload")  # 为后续函数或类声明附加装饰器配置
async def upload_source_file(  # 定义异步处理函数 upload_source_file
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    file: UploadFile = File(...),  # 声明参数 file，供当前逻辑使用
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 upload_source_file 的参数声明
    _require_permission(current_admin, "sources")  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    if not allowed_tenant_id:  # 租户管理员场景下追加租户隔离过滤
        raise HTTPException(status_code=400, detail="上传文件必须绑定租户")  # 抛出 HTTP 异常并把错误信息返回给前端

    safe_name = _safe_upload_filename(file.filename)  # 更新当前逻辑中的 safe name
    upload_root = Path(settings.upload_dir).resolve()  # 更新当前逻辑中的 upload root
    target_dir = upload_root / f"tenant_{allowed_tenant_id}" / "sources"  # 更新当前逻辑中的 target dir
    target_dir.mkdir(parents=True, exist_ok=True)  # 执行当前业务步骤并推进后续处理
    target_path = target_dir / safe_name  # 更新当前逻辑中的 target path

    size = 0  # 更新当前逻辑中的 size
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        with target_path.open("wb") as output:  # 执行当前业务步骤并推进后续处理
            while chunk := await file.read(1024 * 1024):  # 在条件满足时持续循环处理
                size += len(chunk)  # 执行当前业务步骤并推进后续处理
                if size > settings.max_upload_bytes:  # 根据当前条件决定是否进入对应业务分支
                    target_path.unlink(missing_ok=True)  # 执行当前业务步骤并推进后续处理
                    raise HTTPException(status_code=413, detail="上传文件过大")  # 抛出 HTTP 异常并把错误信息返回给前端
                output.write(chunk)  # 执行当前业务步骤并推进后续处理
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        await file.close()  # 关闭上传文件句柄，释放临时资源

    relative_path = target_path.relative_to(upload_root).as_posix()  # 更新当前逻辑中的 relative path
    return ok(  # 按统一成功响应格式返回结果
        {  # 设置 ok 的 字段
            "filename": file.filename,  # 设置 ok 的 filename
            "stored_name": safe_name,  # 设置 ok 的 stored name
            "local_file": relative_path,  # 设置 ok 的 local file
            "size": size,  # 设置 ok 的 size
        },  # 设置 ok 的 字段
        "文件上传成功",  # 设置 ok 的 字段
    )  # 结束 ok 的定义或组装


@router.put("/sources/{source_id}")  # 为后续函数或类声明附加装饰器配置
async def update_source(  # 定义更新 source 的接口或辅助函数
    source_id: int,  # 声明参数 source_id，供当前逻辑使用
    request: SourceUpdate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 update_source 的参数声明
    _require_permission(current_admin, "sources")  # 执行当前业务步骤并推进后续处理
    source = db.query(Source).filter(Source.id == source_id).first()  # 构造当前业务的基础数据库查询对象
    if not source:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="来源不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, source.tenant_id)  # 执行当前业务步骤并推进后续处理
    update_data = request.model_dump(exclude_unset=True)  # 更新当前逻辑中的 update data
    is_review_only = set(update_data) == {"review_status"}  # 更新当前逻辑中的 is review only
    if _is_source_reviewed(source.review_status) and not is_review_only:  # 根据状态参数决定是否追加筛选条件
        raise HTTPException(status_code=400, detail="已复核的数据不支持编辑，请在详情中查看复核记录")  # 抛出 HTTP 异常并把错误信息返回给前端
    next_url = update_data.get("url", source.url)  # 更新当前逻辑中的 next url
    next_local_file = update_data.get("local_file", source.local_file)  # 更新当前逻辑中的 next local file
    if not (next_url or "").strip() and not (next_local_file or "").strip():  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="外部链接与上传文件必须至少填写一个")  # 抛出 HTTP 异常并把错误信息返回给前端
    candidate = {  # 更新当前逻辑中的 candidate
        "source_code": update_data.get("source_code", source.source_code),  # 填充返回或配置中的 资料编码 字段
        "url": next_url,  # 填充返回或配置中的 链接地址 字段
        "title": update_data.get("title", source.title),  # 填充返回或配置中的 标题 字段
        "issuer": update_data.get("issuer", source.issuer) or "",  # 填充返回或配置中的 issuer 字段
    }  # 结束 candidate 的定义或组装
    if _find_duplicate_source(db, source.tenant_id, candidate, exclude_id=source.id):  # 更新场景下排除当前正在编辑的记录
        raise HTTPException(status_code=400, detail="该租户下已存在相同来源编码、链接或标题发布机构")  # 抛出 HTTP 异常并把错误信息返回给前端
    for field, value in update_data.items():  # 遍历当前集合中的每一项并逐个处理
        if field == "issuer":  # 根据当前条件决定是否进入对应业务分支
            value = value or ""  # 读取当前字段原始值，准备转成导出格式
        setattr(source, field, value)  # 执行当前业务步骤并推进后续处理
    if "review_status" in update_data:  # 根据状态参数决定是否追加筛选条件
        if _is_source_reviewed(source.review_status):  # 根据状态参数决定是否追加筛选条件
            source.reviewed_at = datetime.utcnow()  # 更新当前逻辑中的 reviewed at
            source.reviewed_by = _reviewer_name(current_admin)  # 更新当前逻辑中的 reviewed by
        else:  # 处理其他未命中的业务情况
            source.reviewed_at = None  # 更新当前逻辑中的 reviewed at
            source.reviewed_by = None  # 更新当前逻辑中的 reviewed by
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(source)  # 回填数据库生成的主键和默认字段
    return ok(source, "来源更新成功")  # 按统一成功响应格式返回结果


@router.delete("/sources/{source_id}")  # 为后续函数或类声明附加装饰器配置
async def delete_source(  # 定义异步处理函数 delete_source
    source_id: int,  # 声明参数 source_id，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 delete_source 的参数声明
    _require_permission(current_admin, "sources")  # 执行当前业务步骤并推进后续处理
    source = db.query(Source).filter(Source.id == source_id).first()  # 构造当前业务的基础数据库查询对象
    if not source:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="来源不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, source.tenant_id)  # 执行当前业务步骤并推进后续处理
    db.delete(source)  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok(message="来源删除成功")  # 按统一成功响应格式返回结果


@router.get("/knowledge-packages")  # 为后续函数或类声明附加装饰器配置
async def get_knowledge_packages(  # 定义获取 knowledge packages 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    region: Optional[str] = None,  # 声明参数 region，供当前逻辑使用
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_knowledge_packages 的参数声明
    _require_permission(current_admin, "packages")  # 执行当前业务步骤并推进后续处理
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _tenant_scoped_query(db, KnowledgePackage, current_admin, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if region:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(KnowledgePackage.region == region)  # 保存当前逐步拼装的数据库查询对象
    if status:  # 根据状态参数决定是否追加筛选条件
        query = query.filter(KnowledgePackage.status == status)  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    packages = query.order_by(KnowledgePackage.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    data = []  # 整理当前接口最终要返回的数据结构
    for pkg in packages:  # 遍历当前集合中的每一项并逐个处理
        data.append(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "id": pkg.id,  # 执行当前业务步骤并推进后续处理
                "tenant_id": pkg.tenant_id,  # 执行当前业务步骤并推进后续处理
                "tenant_name": pkg.tenant.name if pkg.tenant else "",  # 执行当前业务步骤并推进后续处理
                "name": pkg.name,  # 执行当前业务步骤并推进后续处理
                "region": pkg.region,  # 执行当前业务步骤并推进后续处理
                "version": pkg.version,  # 执行当前业务步骤并推进后续处理
                "description": pkg.description,  # 执行当前业务步骤并推进后续处理
                "categories": pkg.categories or [],  # 执行当前业务步骤并推进后续处理
                "status": pkg.status,  # 执行当前业务步骤并推进后续处理
                "faq_count": db.query(FAQ).filter(FAQ.tenant_id == pkg.tenant_id).count(),  # 执行当前业务步骤并推进后续处理
                "doc_count": db.query(Source).filter(Source.tenant_id == pkg.tenant_id).count(),  # 执行当前业务步骤并推进后续处理
                "created_at": pkg.created_at,  # 执行当前业务步骤并推进后续处理
                "updated_at": pkg.updated_at,  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
    return page_response(data, total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.get("/knowledge-packages/export")  # 为后续函数或类声明附加装饰器配置
async def export_knowledge_packages(  # 定义异步处理函数 export_knowledge_packages
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    region: Optional[str] = None,  # 声明参数 region，供当前逻辑使用
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    ids: Optional[str] = None,  # 声明参数 ids，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 export_knowledge_packages 的参数声明
    _require_permission(current_admin, "packages_export")  # 执行当前业务步骤并推进后续处理
    query = _module_query(db, KnowledgePackage, current_admin, ids, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if region:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(KnowledgePackage.region == region)  # 保存当前逐步拼装的数据库查询对象
    if status:  # 根据状态参数决定是否追加筛选条件
        query = query.filter(KnowledgePackage.status == status)  # 保存当前逐步拼装的数据库查询对象
    rows = [  # 更新当前逻辑中的 rows
        {  # 补充列表中的 { 项
            "id": item.id,  # 补充列表中的 主键 ID 项
            "name": item.name,  # 补充列表中的 名称 项
            "region": item.region,  # 补充列表中的 地区 项
            "version": item.version,  # 补充列表中的 版本 项
            "description": item.description,  # 补充列表中的 说明描述 项
            "categories": item.categories or [],  # 补充列表中的 categories 项
            "status": item.status,  # 补充列表中的 状态 项
            "dify_dataset_id": item.dify_dataset_id,  # 补充列表中的 dify dataset id 项
            "ragflow_dataset_id": item.ragflow_dataset_id,  # 补充列表中的 ragflow dataset id 项
        }  # 补充列表中的 } 项
        for item in query.order_by(KnowledgePackage.id.asc()).all()  # 补充列表中的 all() 项
    ]  # 结束 rows 的定义或组装
    return _csv_text_response("knowledge-packages.csv", rows, PACKAGE_EXPORT_FIELDS)  # 返回当前分支整理好的结果


@router.post("/knowledge-packages/import")  # 为后续函数或类声明附加装饰器配置
async def import_knowledge_packages(  # 定义异步处理函数 import_knowledge_packages
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    file: UploadFile = File(...),  # 声明参数 file，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 import_knowledge_packages 的参数声明
    _require_permission(current_admin, "packages_import")  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    rows = await _read_import_rows(file)  # 更新当前逻辑中的 rows
    imported = 0  # 更新当前逻辑中的 imported
    updated = 0  # 更新当前逻辑中的 updated
    skipped = 0  # 更新当前逻辑中的 skipped
    errors: list[str] = []  # 更新当前逻辑中的 errors
    for index, row in enumerate(rows, start=2):  # 遍历当前集合中的每一项并逐个处理
        name = sanitize_text(row.get("name") or row.get("名称"))  # 清洗并规范化 名称 的输入值
        if not name:  # 根据当前条件决定是否进入对应业务分支
            skipped += 1  # 执行当前业务步骤并推进后续处理
            errors.append(f"第 {index} 行缺少 name")  # 执行当前业务步骤并推进后续处理
            continue  # 跳过当前项，继续处理下一项数据
        payload = {  # 组装发往外部问答服务的请求载荷
            "name": name,  # 向 Dify 请求体写入 名称
            "region": row.get("region") or row.get("地区") or None,  # 向 Dify 请求体写入 地区
            "version": row.get("version") or row.get("版本") or "v1.0",  # 向 Dify 请求体写入 版本
            "description": sanitize_text(row.get("description") or row.get("说明")),  # 向 Dify 请求体写入 说明描述
            "categories": _read_json_list(row.get("categories") or row.get("分类")),  # 向 Dify 请求体写入 categories
            "status": row.get("status") or row.get("状态") or "active",  # 向 Dify 请求体写入 状态
            "dify_dataset_id": row.get("dify_dataset_id") or None,  # 向 Dify 请求体写入 dify dataset id
            "ragflow_dataset_id": row.get("ragflow_dataset_id") or None,  # 向 Dify 请求体写入 ragflow dataset id
        }  # 结束 payload 的定义或组装
        if payload["status"] not in {"active", "disabled", "draft"}:  # 根据状态参数决定是否追加筛选条件
            payload["status"] = "active"  # 执行当前业务步骤并推进后续处理
        package = (  # 更新当前逻辑中的 package
            db.query(KnowledgePackage)  # 执行当前业务步骤并推进后续处理
            .filter(KnowledgePackage.tenant_id == allowed_tenant_id, KnowledgePackage.name == payload["name"])  # 执行当前业务步骤并推进后续处理
            .order_by(KnowledgePackage.id.asc())  # 执行当前业务步骤并推进后续处理
            .first()  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
        if package:  # 根据当前条件决定是否进入对应业务分支
            for field, value in payload.items():  # 遍历当前集合中的每一项并逐个处理
                setattr(package, field, value)  # 执行当前业务步骤并推进后续处理
            updated += 1  # 执行当前业务步骤并推进后续处理
        else:  # 处理其他未命中的业务情况
            db.add(KnowledgePackage(tenant_id=allowed_tenant_id, **payload))  # 把新实体加入当前数据库事务等待提交
            imported += 1  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok({"imported": imported, "updated": updated, "skipped": skipped, "errors": errors[:20]}, "知识包导入完成")  # 按统一成功响应格式返回结果


@router.post("/knowledge-packages/batch")  # 为后续函数或类声明附加装饰器配置
async def batch_knowledge_packages(  # 定义异步处理函数 batch_knowledge_packages
    request: dict,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 batch_knowledge_packages 的参数声明
    _require_permission(current_admin, "packages_batch")  # 执行当前业务步骤并推进后续处理
    ids = request.get("ids") or []  # 更新当前逻辑中的 ids
    action = request.get("action")  # 更新当前逻辑中的 action
    if not ids:  # 没有传入 ID 列表时直接返回空结果
        raise HTTPException(status_code=400, detail="请选择要批量操作的数据")  # 抛出 HTTP 异常并把错误信息返回给前端
    items = _tenant_scoped_query(db, KnowledgePackage, current_admin).filter(KnowledgePackage.id.in_(ids)).all()  # 保存当前页查询出来的记录列表
    if action == "delete":  # 根据当前条件决定是否进入对应业务分支
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            db.delete(item)  # 执行当前业务步骤并推进后续处理
    elif action == "set_status":  # 前一个条件不满足时继续判断其他分支
        status = request.get("status")  # 更新当前逻辑中的 状态
        if status not in {"active", "disabled", "draft"}:  # 根据状态参数决定是否追加筛选条件
            raise HTTPException(status_code=400, detail="无效的状态")  # 抛出 HTTP 异常并把错误信息返回给前端
        for item in items:  # 遍历当前集合中的每一项并逐个处理
            item.status = status  # 更新当前逻辑中的 状态
    else:  # 处理其他未命中的业务情况
        raise HTTPException(status_code=400, detail="不支持的批量操作")  # 抛出 HTTP 异常并把错误信息返回给前端
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok({"affected": len(items)}, "批量操作完成")  # 按统一成功响应格式返回结果


@router.put("/knowledge-packages/{package_id}/status")  # 为后续函数或类声明附加装饰器配置
async def update_package_status(  # 定义更新 package status 的接口或辅助函数
    package_id: int,  # 声明参数 package_id，供当前逻辑使用
    request: dict,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 update_package_status 的参数声明
    _require_permission(current_admin, "packages")  # 执行当前业务步骤并推进后续处理
    package = db.query(KnowledgePackage).filter(KnowledgePackage.id == package_id).first()  # 构造当前业务的基础数据库查询对象
    if not package:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="知识包不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, package.tenant_id)  # 执行当前业务步骤并推进后续处理
    status = request.get("status")  # 更新当前逻辑中的 状态
    if status not in {"active", "disabled", "draft"}:  # 根据状态参数决定是否追加筛选条件
        raise HTTPException(status_code=400, detail="无效的状态")  # 抛出 HTTP 异常并把错误信息返回给前端
    package.status = status  # 更新当前逻辑中的 状态
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok(message="状态更新成功")  # 按统一成功响应格式返回结果


@router.get("/test-questions")  # 为后续函数或类声明附加装饰器配置
async def get_test_questions(  # 定义获取 test questions 的接口或辅助函数
    tenant_id: Optional[int] = None,  # 接收需要筛选或校验的租户 ID
    category: Optional[str] = None,  # 声明参数 category，供当前逻辑使用
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_test_questions 的参数声明
    _require_permission(current_admin, "test_questions")  # 执行当前业务步骤并推进后续处理
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _tenant_scoped_query(db, TestQuestion, current_admin, tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if category:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(TestQuestion.category == category)  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    items = query.order_by(TestQuestion.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    return page_response(items, total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.get("/service-status")  # 为后续函数或类声明附加装饰器配置
async def service_status(current_admin: dict = Depends(get_current_admin)):  # 定义异步处理函数 service_status
    return ok(  # 按统一成功响应格式返回结果
        {  # 设置 ok 的 字段
            "database": {  # 设置 ok 的 database
                "host": settings.db_host,  # 设置 ok 的 host
                "port": settings.db_port,  # 设置 ok 的 port
                "name": settings.db_name,  # 设置 ok 的 名称
                "engine": "MySQL 8 / Docker",  # 设置 ok 的 engine
            },  # 设置 ok 的 字段
            "external_services": check_external_services(),  # 设置 ok 的 external services
        }  # 设置 ok 的 字段
    )  # 结束 ok 的定义或组装
