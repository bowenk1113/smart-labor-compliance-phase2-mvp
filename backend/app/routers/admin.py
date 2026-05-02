"""管理端路由。"""
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.database import get_db, settings
from app.dependencies import get_admin_tenant_filter, get_current_admin, normalize_pagination
from app.models import Admin, ChatLog, FAQ, Feedback, KnowledgePackage, Source, Tenant, TestQuestion
from app.response import ok, page as page_response
from app.schemas.admin import AdminCreate, AdminLogin, AdminToken, AdminUpdate, TenantCreate, TenantUpdate
from app.schemas.faq import FAQCreate, FAQUpdate
from app.schemas.source import SourceCreate, SourceUpdate
from app.security import (
    ROLE_LABELS,
    ROLE_PERMISSIONS,
    SUPER_ADMIN_ROLES,
    TENANT_ADMIN_ROLES,
    authenticate_admin,
    create_access_token,
    get_password_hash,
    require_role,
    role_label,
    role_permissions,
    sanitize_text,
)
from app.services.dify_service import check_external_services

router = APIRouter(prefix="/api/admin", tags=["管理端"])

ALLOWED_SOURCE_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".html", ".htm", ".csv", ".xlsx", ".xls"}


def _tenant_query(db: Session, current_admin: dict):
    query = db.query(Tenant)
    if current_admin["role"] != "super_admin":
        query = query.filter(Tenant.id == current_admin["tenant_id"])
    return query


def _serialize_admin(admin: Admin) -> dict:
    return {
        "id": admin.id,
        "tenant_id": admin.tenant_id,
        "tenant_name": admin.tenant.name if admin.tenant else "平台",
        "username": admin.username,
        "role": admin.role,
        "role_label": role_label(admin.role),
        "display_name": admin.display_name,
        "email": admin.email,
        "is_active": admin.is_active,
        "created_at": admin.created_at,
        "last_login_at": admin.last_login_at,
    }


def _serialize_tenant(tenant: Tenant) -> dict:
    return {
        "id": tenant.id,
        "code": tenant.code,
        "name": tenant.name,
        "industry": tenant.industry,
        "region": tenant.region,
        "contact_name": tenant.contact_name,
        "contact_email": tenant.contact_email,
        "contact_phone": tenant.contact_phone,
        "status": tenant.status,
        "is_demo": tenant.is_demo,
        "dify_configured": bool(tenant.dify_api_key),
        "ragflow_dataset_id": tenant.ragflow_dataset_id,
        "notes": tenant.notes,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
    }


def _tenant_scoped_query(db: Session, model, current_admin: dict, tenant_id: Optional[int] = None):
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)
    query = db.query(model)
    if allowed_tenant_id:
        query = query.filter(model.tenant_id == allowed_tenant_id)
    return query


def _find_duplicate_faq(db: Session, tenant_id: int, payload: dict, exclude_id: Optional[int] = None) -> Optional[FAQ]:
    filters = []
    if payload.get("faq_code"):
        filters.append(FAQ.faq_code == payload["faq_code"])
    if payload.get("question"):
        filters.append((FAQ.language == payload.get("language", "zh-CN")) & (FAQ.question == payload["question"]))
    if not filters:
        return None
    query = db.query(FAQ).filter(FAQ.tenant_id == tenant_id, or_(*filters))
    if exclude_id:
        query = query.filter(FAQ.id != exclude_id)
    return query.order_by(FAQ.id.asc()).first()


def _find_duplicate_source(db: Session, tenant_id: int, payload: dict, exclude_id: Optional[int] = None) -> Optional[Source]:
    filters = []
    if payload.get("source_code"):
        filters.append(Source.source_code == payload["source_code"])
    if payload.get("url"):
        filters.append(Source.url == payload["url"])
    if payload.get("title"):
        filters.append((Source.title == payload["title"]) & (Source.issuer == (payload.get("issuer") or "")))
    if not filters:
        return None
    query = db.query(Source).filter(Source.tenant_id == tenant_id, or_(*filters))
    if exclude_id:
        query = query.filter(Source.id != exclude_id)
    return query.order_by(Source.id.asc()).first()


def _is_source_reviewed(value: Optional[str]) -> bool:
    return value in {"已复核", "reviewed"}


def _reviewer_name(current_admin: dict) -> str:
    return current_admin.get("display_name") or current_admin.get("username") or f"管理员{current_admin.get('id')}"


def _source_similarity(left: str, right: str) -> float:
    left = (left or "").strip()
    right = (right or "").strip()
    if not left or not right:
        return 0
    if left == right:
        return 1
    if left in right or right in left:
        return 0.92
    return SequenceMatcher(None, left, right).ratio()


def _source_url_similarity(left: str, right: str) -> float:
    left = (left or "").strip()
    right = (right or "").strip()
    if not left or not right:
        return 0
    if left == right:
        return 1
    left_parts = urlparse(left)
    right_parts = urlparse(right)
    if left_parts.netloc != right_parts.netloc:
        return 0
    left_path = left_parts.path.strip("/")
    right_path = right_parts.path.strip("/")
    if len(left_path) < 8 or len(right_path) < 8:
        return 0
    if left_path in right_path or right_path in left_path:
        return 0.78
    return 0


def _sources_from_current_catalog(db: Session, tenant_id: int, log: ChatLog) -> list[dict]:
    """Return source snapshots with URLs corrected from the maintained source catalog."""
    raw_sources = log.sources if isinstance(log.sources, list) else []
    catalog = db.query(Source).filter(Source.tenant_id == tenant_id).all()
    used_ids: set[int] = set()
    corrected: list[dict] = []

    def source_to_dict(source: Source, snapshot: Optional[dict] = None) -> dict:
        used_ids.add(source.id)
        return {
            "id": source.id,
            "title": source.title,
            "url": source.url,
            "snippet": source.description or (snapshot or {}).get("snippet"),
            "review_status": source.review_status,
        }

    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        url = item.get("url") or ""
        best = None
        best_score = 0.0
        for source in catalog:
            score = max(_source_similarity(title, source.title), _source_url_similarity(url, source.url or ""))
            if score > best_score:
                best = source
                best_score = score
        if best and best_score >= 0.62:
            corrected.append(source_to_dict(best, item))
        elif title or url:
            corrected.append({
                "title": title or url,
                "url": url,
                "snippet": item.get("snippet"),
                "review_status": item.get("review_status"),
            })

    faq = (
        db.query(FAQ)
        .filter(FAQ.tenant_id == tenant_id, FAQ.question == log.question)
        .order_by(FAQ.id.asc())
        .first()
    )
    if faq and faq.source_ids:
        faq_sources = (
            db.query(Source)
            .filter(Source.tenant_id == tenant_id, Source.id.in_(faq.source_ids))
            .order_by(Source.id.asc())
            .all()
        )
        for source in faq_sources:
            if source.id not in used_ids:
                corrected.append(source_to_dict(source))

    return corrected


def _safe_upload_filename(filename: str) -> str:
    raw_name = Path(filename or "source-file").name
    stem = sanitize_text(Path(raw_name).stem) or "source"
    suffix = Path(raw_name).suffix.lower()
    if suffix not in ALLOWED_SOURCE_FILE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    safe_stem = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in stem).strip("_") or "source"
    return f"{uuid4().hex}_{safe_stem[:80]}{suffix}"


@router.post("/login", response_model=AdminToken)
async def login(request: AdminLogin):
    admin = authenticate_admin(request.username.strip(), request.password, request.tenant_code)
    if not admin:
        raise HTTPException(status_code=401, detail="用户名、密码或租户不正确")

    access_token = create_access_token(
        data={
            "sub": str(admin["id"]),
            "role": admin["role"],
            "tenant_id": admin["tenant_id"],
        }
    )

    return AdminToken(
        access_token=access_token,
        admin_id=admin["id"],
        username=admin["username"],
        role=admin["role"],
        role_label=role_label(admin["role"]),
        permissions=role_permissions(admin["role"]),
        tenant_id=admin["tenant_id"],
        tenant_code=admin["tenant_code"],
        tenant_name=admin["tenant_name"],
    )


@router.get("/verify-token")
async def verify_token(current_admin: dict = Depends(get_current_admin)):
    return ok(current_admin)


@router.get("/roles")
async def get_roles(current_admin: dict = Depends(get_current_admin)):
    roles = [
        {"value": role, "label": label, "permissions": ROLE_PERMISSIONS.get(role, [])}
        for role, label in ROLE_LABELS.items()
    ]
    if current_admin["role"] != "super_admin":
        roles = [item for item in roles if item["value"] != "super_admin"]
    return ok(roles)


@router.get("/statistics")
async def get_statistics(
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)

    def scoped(model):
        query = db.query(model)
        return query.filter(model.tenant_id == allowed_tenant_id) if allowed_tenant_id else query

    chat_query = scoped(ChatLog)
    feedback_query = scoped(Feedback)
    faq_query = scoped(FAQ)
    source_query = scoped(Source)

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_feedbacks = feedback_query.count()
    helpful = feedback_query.filter(Feedback.is_helpful.is_(True)).count()
    helpful_rate = int(round((helpful / total_feedbacks) * 100)) if total_feedbacks else 0
    avg_response = chat_query.with_entities(func.avg(ChatLog.response_time)).scalar() or 0

    top_questions = (
        chat_query.with_entities(ChatLog.question, func.count(ChatLog.id).label("count"))
        .group_by(ChatLog.question)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    data = {
        "total_questions": chat_query.count(),
        "today_questions": chat_query.filter(ChatLog.created_at >= today).count(),
        "total_feedbacks": total_feedbacks,
        "pending_feedbacks": feedback_query.filter(Feedback.status == "pending").count(),
        "total_faqs": faq_query.count(),
        "total_sources": source_query.count(),
        "total_tenants": db.query(Tenant).count() if current_admin["role"] == "super_admin" else 1,
        "helpful_rate": helpful_rate,
        "avg_response_time": int(avg_response),
        "top_questions": [{"question": row.question, "count": row.count} for row in top_questions],
        "services": check_external_services(),
    }
    return ok(data)


@router.get("/tenants")
async def get_tenants(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    page, page_size = normalize_pagination(page, page_size)
    query = _tenant_query(db, current_admin)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((Tenant.name.like(like)) | (Tenant.code.like(like)))
    if status:
        query = query.filter(Tenant.status == status)
    total = query.count()
    tenants = query.order_by(Tenant.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_response([_serialize_tenant(item) for item in tenants], total, page, page_size)


@router.post("/tenants")
async def create_tenant(
    request: TenantCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    require_role(current_admin["role"], SUPER_ADMIN_ROLES)
    code = request.code.strip()
    if db.query(Tenant).filter(Tenant.code == code).first():
        raise HTTPException(status_code=400, detail="租户编码已存在")
    tenant = Tenant(
        code=code,
        name=request.name.strip(),
        industry=request.industry,
        region=request.region,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        status=request.status,
        notes=sanitize_text(request.notes),
    )
    db.add(tenant)
    db.flush()

    if request.admin_username and request.admin_password:
        db.add(
            Admin(
                tenant_id=tenant.id,
                username=request.admin_username.strip(),
                password_hash=get_password_hash(request.admin_password),
                role="tenant_admin",
                display_name=f"{tenant.name}管理员",
                is_active=True,
            )
        )

    db.commit()
    db.refresh(tenant)
    return ok(_serialize_tenant(tenant), "租户创建成功")


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: int,
    request: TenantUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    if current_admin["role"] != "super_admin" and tenant_id != current_admin.get("tenant_id"):
        raise HTTPException(status_code=403, detail="不能修改其他租户")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(tenant, field, sanitize_text(value) if isinstance(value, str) else value)
    db.commit()
    db.refresh(tenant)
    return ok(_serialize_tenant(tenant), "租户更新成功")


@router.get("/admins")
async def get_admins(
    tenant_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)
    page, page_size = normalize_pagination(page, page_size)
    query = db.query(Admin)
    if current_admin["role"] == "super_admin":
        if tenant_id is not None:
            query = query.filter(Admin.tenant_id == tenant_id)
    else:
        query = query.filter(Admin.tenant_id == current_admin["tenant_id"], Admin.role != "super_admin")
    total = query.count()
    admins = query.order_by(Admin.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_response([_serialize_admin(item) for item in admins], total, page, page_size)


@router.post("/admins")
async def create_admin_account(
    request: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)
    role = request.role
    if role not in ROLE_LABELS:
        raise HTTPException(status_code=400, detail="无效的角色")
    if role == "super_admin" and current_admin["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="不能创建超级管理员")

    tenant_id = request.tenant_id if current_admin["role"] == "super_admin" else current_admin["tenant_id"]
    if role != "super_admin" and not tenant_id:
        raise HTTPException(status_code=400, detail="非平台管理员必须绑定租户")

    username = request.username.strip()
    if db.query(Admin).filter(Admin.username == username, Admin.tenant_id == tenant_id).first():
        raise HTTPException(status_code=400, detail="该租户下用户名已存在")

    admin = Admin(
        tenant_id=tenant_id,
        username=username,
        password_hash=get_password_hash(request.password),
        role=role,
        display_name=sanitize_text(request.display_name),
        email=request.email,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return ok(_serialize_admin(admin), "账号创建成功")


@router.put("/admins/{admin_id}")
async def update_admin_account(
    admin_id: int,
    request: AdminUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="账号不存在")
    if current_admin["role"] != "super_admin" and admin.tenant_id != current_admin["tenant_id"]:
        raise HTTPException(status_code=403, detail="不能修改其他租户账号")
    if admin.role == "super_admin" and current_admin["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="不能修改超级管理员")

    update_data = request.model_dump(exclude_unset=True)
    if "role" in update_data and update_data["role"]:
        if update_data["role"] == "super_admin" and current_admin["role"] != "super_admin":
            raise HTTPException(status_code=403, detail="不能授予超级管理员")
        admin.role = update_data["role"]
    if update_data.get("password"):
        admin.password_hash = get_password_hash(update_data["password"])
    for field in ["display_name", "email", "is_active"]:
        if field in update_data:
            setattr(admin, field, sanitize_text(update_data[field]) if isinstance(update_data[field], str) else update_data[field])
    db.commit()
    db.refresh(admin)
    return ok(_serialize_admin(admin), "账号更新成功")


@router.delete("/admins/{admin_id}")
async def delete_admin_account(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    require_role(current_admin["role"], TENANT_ADMIN_ROLES)
    if admin_id == current_admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="账号不存在")
    if current_admin["role"] != "super_admin" and admin.tenant_id != current_admin["tenant_id"]:
        raise HTTPException(status_code=403, detail="不能删除其他租户账号")
    if admin.role == "super_admin":
        raise HTTPException(status_code=403, detail="不能删除超级管理员")
    db.delete(admin)
    db.commit()
    return ok(message="账号删除成功")


@router.get("/logs")
async def get_logs(
    tenant_id: Optional[int] = None,
    user_id: Optional[str] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    page, page_size = normalize_pagination(page, page_size)
    query = _tenant_scoped_query(db, ChatLog, current_admin, tenant_id)
    if user_id:
        query = query.filter(ChatLog.user_id == user_id)
    if keyword:
        query = query.filter(ChatLog.question.contains(keyword))
    if status:
        query = query.filter(ChatLog.status == status)
    if start_date:
        query = query.filter(ChatLog.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(ChatLog.created_at < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
    total = query.count()
    logs = query.order_by(ChatLog.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_response(
        [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "tenant_name": item.tenant.name if item.tenant else "",
                "user_id": item.user_id,
                "question": item.question,
                "answer": item.answer,
                "provider": item.provider,
                "risk_level": item.risk_level,
                "response_time": item.response_time,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in logs
        ],
        total,
        page,
        page_size,
    )


@router.get("/logs/{log_id}")
async def get_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    log = db.query(ChatLog).filter(ChatLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    get_admin_tenant_filter(current_admin, log.tenant_id)
    return ok(
        {
            "id": log.id,
            "tenant_id": log.tenant_id,
            "tenant_name": log.tenant.name if log.tenant else "",
            "user_id": log.user_id,
            "session_id": log.session_id,
            "conversation_id": log.conversation_id,
            "language": log.language,
            "question": log.question,
            "answer": log.answer,
            "sources": _sources_from_current_catalog(db, log.tenant_id, log),
            "related_tasks": log.related_tasks,
            "provider": log.provider,
            "risk_level": log.risk_level,
            "response_time": log.response_time,
            "status": log.status,
            "created_at": log.created_at,
        }
    )


@router.get("/faqs")
async def get_faqs(
    tenant_id: Optional[int] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    page, page_size = normalize_pagination(page, page_size)
    query = _tenant_scoped_query(db, FAQ, current_admin, tenant_id)
    if category:
        query = query.filter(FAQ.category == category)
    if keyword:
        query = query.filter(FAQ.question.contains(keyword))
    total = query.count()
    items = query.order_by(FAQ.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_response(items, total, page, page_size)


@router.post("/faqs")
async def create_faq(
    request: FAQCreate,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)
    payload = {
        "faq_code": request.faq_code,
        "question": sanitize_text(request.question),
        "answer": sanitize_text(request.answer),
        "category": request.category,
        "region": request.region,
        "risk_level": request.risk_level,
        "keywords": request.keywords,
        "aliases": request.aliases,
        "source_ids": request.source_ids,
        "language": request.language,
        "effective_date": request.effective_date,
    }
    faq = _find_duplicate_faq(db, allowed_tenant_id, payload)
    if faq:
        for field, value in payload.items():
            setattr(faq, field, value)
        message = "FAQ 已存在，已覆盖更新"
    else:
        faq = FAQ(tenant_id=allowed_tenant_id, **payload)
        db.add(faq)
        message = "FAQ 添加成功"
    db.commit()
    db.refresh(faq)
    return ok(faq, message)


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: int,
    request: FAQUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    get_admin_tenant_filter(current_admin, faq.tenant_id)
    update_data = request.model_dump(exclude_unset=True)
    candidate = {
        "faq_code": update_data.get("faq_code", faq.faq_code),
        "question": sanitize_text(update_data.get("question", faq.question)),
        "language": update_data.get("language", faq.language),
    }
    if _find_duplicate_faq(db, faq.tenant_id, candidate, exclude_id=faq.id):
        raise HTTPException(status_code=400, detail="该租户下已存在相同 FAQ 编码或问题")
    for field, value in update_data.items():
        setattr(faq, field, sanitize_text(value) if field in {"question", "answer"} else value)
    db.commit()
    db.refresh(faq)
    return ok(faq, "FAQ 更新成功")


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    get_admin_tenant_filter(current_admin, faq.tenant_id)
    db.delete(faq)
    db.commit()
    return ok(message="FAQ 删除成功")


@router.get("/sources")
async def get_sources(
    tenant_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    region: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    page, page_size = normalize_pagination(page, page_size)
    query = _tenant_scoped_query(db, Source, current_admin, tenant_id)
    if doc_type:
        query = query.filter(Source.doc_type == doc_type)
    if region:
        query = query.filter(Source.region == region)
    if keyword:
        query = query.filter(Source.title.contains(keyword))
    total = query.count()
    items = query.order_by(Source.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_response(items, total, page, page_size)


@router.post("/sources")
async def create_source(
    request: SourceCreate,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)
    payload = request.model_dump()
    payload["issuer"] = payload.get("issuer") or ""
    if _is_source_reviewed(payload.get("review_status")):
        payload["reviewed_at"] = datetime.utcnow()
        payload["reviewed_by"] = _reviewer_name(current_admin)
    else:
        payload["reviewed_at"] = None
        payload["reviewed_by"] = None
    source = _find_duplicate_source(db, allowed_tenant_id, payload)
    if source:
        if _is_source_reviewed(source.review_status):
            raise HTTPException(status_code=400, detail="已复核的数据不支持编辑，请在详情中查看复核记录")
        for field, value in payload.items():
            setattr(source, field, value)
        message = "来源已存在，已覆盖更新"
    else:
        source = Source(tenant_id=allowed_tenant_id, **payload)
        db.add(source)
        message = "来源添加成功"
    db.commit()
    db.refresh(source)
    return ok(source, message)


@router.post("/sources/upload")
async def upload_source_file(
    tenant_id: Optional[int] = None,
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin),
):
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)
    if not allowed_tenant_id:
        raise HTTPException(status_code=400, detail="上传文件必须绑定租户")

    safe_name = _safe_upload_filename(file.filename)
    upload_root = Path(settings.upload_dir).resolve()
    target_dir = upload_root / f"tenant_{allowed_tenant_id}" / "sources"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name

    size = 0
    try:
        with target_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="上传文件过大")
                output.write(chunk)
    finally:
        await file.close()

    relative_path = target_path.relative_to(upload_root).as_posix()
    return ok(
        {
            "filename": file.filename,
            "stored_name": safe_name,
            "local_file": relative_path,
            "size": size,
        },
        "文件上传成功",
    )


@router.put("/sources/{source_id}")
async def update_source(
    source_id: int,
    request: SourceUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    get_admin_tenant_filter(current_admin, source.tenant_id)
    update_data = request.model_dump(exclude_unset=True)
    is_review_only = set(update_data) == {"review_status"}
    if _is_source_reviewed(source.review_status) and not is_review_only:
        raise HTTPException(status_code=400, detail="已复核的数据不支持编辑，请在详情中查看复核记录")
    next_url = update_data.get("url", source.url)
    next_local_file = update_data.get("local_file", source.local_file)
    if not (next_url or "").strip() and not (next_local_file or "").strip():
        raise HTTPException(status_code=400, detail="外部链接与上传文件必须至少填写一个")
    candidate = {
        "source_code": update_data.get("source_code", source.source_code),
        "url": next_url,
        "title": update_data.get("title", source.title),
        "issuer": update_data.get("issuer", source.issuer) or "",
    }
    if _find_duplicate_source(db, source.tenant_id, candidate, exclude_id=source.id):
        raise HTTPException(status_code=400, detail="该租户下已存在相同来源编码、链接或标题发布机构")
    for field, value in update_data.items():
        if field == "issuer":
            value = value or ""
        setattr(source, field, value)
    if "review_status" in update_data:
        if _is_source_reviewed(source.review_status):
            source.reviewed_at = datetime.utcnow()
            source.reviewed_by = _reviewer_name(current_admin)
        else:
            source.reviewed_at = None
            source.reviewed_by = None
    db.commit()
    db.refresh(source)
    return ok(source, "来源更新成功")


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    get_admin_tenant_filter(current_admin, source.tenant_id)
    db.delete(source)
    db.commit()
    return ok(message="来源删除成功")


@router.get("/knowledge-packages")
async def get_knowledge_packages(
    tenant_id: Optional[int] = None,
    region: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    page, page_size = normalize_pagination(page, page_size)
    query = _tenant_scoped_query(db, KnowledgePackage, current_admin, tenant_id)
    if region:
        query = query.filter(KnowledgePackage.region == region)
    if status:
        query = query.filter(KnowledgePackage.status == status)
    total = query.count()
    packages = query.order_by(KnowledgePackage.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    data = []
    for pkg in packages:
        data.append(
            {
                "id": pkg.id,
                "tenant_id": pkg.tenant_id,
                "tenant_name": pkg.tenant.name if pkg.tenant else "",
                "name": pkg.name,
                "region": pkg.region,
                "version": pkg.version,
                "description": pkg.description,
                "categories": pkg.categories or [],
                "status": pkg.status,
                "faq_count": db.query(FAQ).filter(FAQ.tenant_id == pkg.tenant_id).count(),
                "doc_count": db.query(Source).filter(Source.tenant_id == pkg.tenant_id).count(),
                "created_at": pkg.created_at,
                "updated_at": pkg.updated_at,
            }
        )
    return page_response(data, total, page, page_size)


@router.put("/knowledge-packages/{package_id}/status")
async def update_package_status(
    package_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    package = db.query(KnowledgePackage).filter(KnowledgePackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="知识包不存在")
    get_admin_tenant_filter(current_admin, package.tenant_id)
    status = request.get("status")
    if status not in {"active", "disabled", "draft"}:
        raise HTTPException(status_code=400, detail="无效的状态")
    package.status = status
    db.commit()
    return ok(message="状态更新成功")


@router.get("/test-questions")
async def get_test_questions(
    tenant_id: Optional[int] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    page, page_size = normalize_pagination(page, page_size)
    query = _tenant_scoped_query(db, TestQuestion, current_admin, tenant_id)
    if category:
        query = query.filter(TestQuestion.category == category)
    total = query.count()
    items = query.order_by(TestQuestion.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_response(items, total, page, page_size)


@router.get("/service-status")
async def service_status(current_admin: dict = Depends(get_current_admin)):
    return ok(
        {
            "database": {
                "host": settings.db_host,
                "port": settings.db_port,
                "name": settings.db_name,
                "engine": "MySQL 8 / Docker",
            },
            "external_services": check_external_services(),
        }
    )
