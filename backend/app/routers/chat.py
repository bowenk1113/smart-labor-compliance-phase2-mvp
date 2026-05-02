"""用户端问答路由。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_public_tenant, normalize_pagination
from app.models import ChatLog, FAQ, Tenant
from app.response import ok
from app.schemas.chat import ChatRequest, ChatResponse, HistoryResponse
from app.security import hash_ip, sanitize_text
from app.services.dify_service import ComplianceAnswerService

router = APIRouter(prefix="/api", tags=["问答"])


@router.post("/chat", response_model=dict)
async def chat(
    request_data: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    header_tenant: Tenant = Depends(get_public_tenant),
):
    if not request_data.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    tenant = header_tenant
    if request_data.tenant_code and request_data.tenant_code != header_tenant.code:
        tenant = db.query(Tenant).filter(Tenant.code == request_data.tenant_code, Tenant.status == "active").first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在或已停用")

    session_id = request_data.session_id or str(uuid.uuid4())
    user_id = sanitize_text(request_data.user_id) or "anonymous"
    question = sanitize_text(request_data.question) or ""

    service = ComplianceAnswerService(db, tenant)
    response = service.answer(
        question=question,
        user_id=user_id,
        conversation_id=request_data.conversation_id,
        language=request_data.language,
    )

    chat_log = ChatLog(
        tenant_id=tenant.id,
        user_id=user_id,
        session_id=session_id,
        conversation_id=response.conversation_id,
        language=request_data.language,
        question=question,
        answer=response.answer,
        sources=[item.model_dump() for item in response.sources] if response.sources else None,
        related_tasks=[item.model_dump() for item in response.related_tasks] if response.related_tasks else None,
        provider=response.provider,
        risk_level=response.risk_level,
        response_time=response.response_time,
        status="success",
        client_ip_hash=hash_ip(request.client.host if request.client else None),
    )
    db.add(chat_log)
    db.commit()
    db.refresh(chat_log)
    response.question_id = chat_log.id
    return ok(response.model_dump(), "回答生成成功")


@router.get("/history", response_model=dict)
async def get_history(
    user_id: str = "anonymous",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_public_tenant),
):
    page, page_size = normalize_pagination(page, page_size)
    query = db.query(ChatLog).filter(ChatLog.tenant_id == tenant.id, ChatLog.user_id == sanitize_text(user_id))
    total = query.count()
    logs = query.order_by(ChatLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    data = HistoryResponse(total=total, list=logs)
    return ok(data.model_dump(), "历史记录获取成功")


@router.delete("/history")
async def clear_history(
    user_id: str = "anonymous",
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_public_tenant),
):
    db.query(ChatLog).filter(ChatLog.tenant_id == tenant.id, ChatLog.user_id == sanitize_text(user_id)).delete()
    db.commit()
    return ok(message="历史记录已清空")


@router.get("/recommended-questions")
async def get_recommended_questions(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_public_tenant),
):
    faqs = (
        db.query(FAQ)
        .filter(FAQ.tenant_id == tenant.id)
        .order_by(FAQ.updated_at.desc())
        .limit(8)
        .all()
    )
    data = [
        {"id": item.id, "question": item.question, "category": item.category, "risk_level": item.risk_level}
        for item in faqs
    ]
    return ok(data)


@router.get("/tenant-public")
async def get_tenant_public(tenant: Tenant = Depends(get_public_tenant)):
    return ok(
        {
            "id": tenant.id,
            "code": tenant.code,
            "name": tenant.name,
            "region": tenant.region,
            "industry": tenant.industry,
        }
    )
