"""
管理端路由
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas.admin import AdminLogin, AdminToken, StatisticsResponse
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse
from app.models.admin import Admin
from app.models.chat_log import ChatLog
from app.models.feedback import Feedback
from app.models.faq import FAQ
from app.models.source import Source
from app.models.knowledge_package import KnowledgePackage
from app.security import authenticate_admin, create_access_token, decode_token

router = APIRouter(prefix="/api/admin", tags=["管理端"])


# 依赖：获取当前管理员
async def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """获取当前管理员"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="无效的认证方案")
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的授权头")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    
    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="令牌无效")
    
    admin = db.query(Admin).filter(Admin.id == int(admin_id)).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    
    return {
        "id": admin.id,
        "username": admin.username,
        "role": admin.role
    }


# ========== 认证相关 ==========

@router.post("/login", response_model=AdminToken)
async def login(request: AdminLogin, db: Session = Depends(get_db)):
    """
    管理员登录
    """
    admin = authenticate_admin(request.username, request.password)
    
    if not admin:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 创建令牌
    access_token = create_access_token(data={"sub": str(admin["id"])})
    
    return AdminToken(
        access_token=access_token,
        admin_id=admin["id"],
        username=admin["username"],
        role=admin["role"]
    )


@router.get("/verify-token")
async def verify_token(current_admin: dict = Depends(get_current_admin)):
    """
    验证 JWT 令牌
    """
    return {
        "success": True,
        "data": current_admin
    }


# ========== 统计相关 ==========

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取统计数据
    """
    # 总问题数
    total_questions = db.query(ChatLog).count()
    
    # 今日问题数
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_questions = db.query(ChatLog).filter(ChatLog.created_at >= today).count()
    
    # 总反馈数
    total_feedbacks = db.query(Feedback).count()
    
    # 待处理反馈数
    pending_feedbacks = db.query(Feedback).filter(Feedback.status == "pending").count()
    
    # FAQ数量
    total_faqs = db.query(FAQ).count()
    
    # 来源数量
    total_sources = db.query(Source).count()
    
    return StatisticsResponse(
        total_questions=total_questions,
        today_questions=today_questions,
        total_feedbacks=total_feedbacks,
        pending_feedbacks=pending_feedbacks,
        total_faqs=total_faqs,
        total_sources=total_sources
    )


# ========== 问答日志 ==========

@router.get("/logs")
async def get_logs(
    user_id: str = None,
    keyword: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取问答日志列表
    """
    query = db.query(ChatLog)
    
    if user_id:
        query = query.filter(ChatLog.user_id == user_id)
    
    if keyword:
        query = query.filter(ChatLog.question.contains(keyword))
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ChatLog.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            end = end + timedelta(days=1)
            query = query.filter(ChatLog.created_at < end)
        except ValueError:
            pass
    
    total = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(ChatLog.created_at.desc()).offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "list": logs
    }


@router.get("/logs/{log_id}")
async def get_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取日志详情
    """
    log = db.query(ChatLog).filter(ChatLog.id == log_id).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    return log


# ========== FAQ管理 ==========

@router.get("/faqs", response_model=list)
async def get_faqs(
    category: str = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取FAQ列表
    """
    query = db.query(FAQ)
    
    if category:
        query = query.filter(FAQ.category == category)
    
    if keyword:
        query = query.filter(FAQ.question.contains(keyword))
    
    total = query.count()
    offset = (page - 1) * page_size
    faqs = query.order_by(FAQ.created_at.desc()).offset(offset).limit(page_size).all()
    
    return faqs


@router.post("/faqs")
async def create_faq(
    request: FAQCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    添加FAQ
    """
    faq = FAQ(
        question=request.question,
        answer=request.answer,
        category=request.category,
        keywords=request.keywords
    )
    
    db.add(faq)
    db.commit()
    db.refresh(faq)
    
    return {
        "success": True,
        "message": "FAQ添加成功",
        "data": {"id": faq.id}
    }


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: int,
    request: FAQUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    更新FAQ
    """
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ不存在")
    
    if request.question is not None:
        faq.question = request.question
    if request.answer is not None:
        faq.answer = request.answer
    if request.category is not None:
        faq.category = request.category
    if request.keywords is not None:
        faq.keywords = request.keywords
    
    db.commit()
    db.refresh(faq)
    
    return {
        "success": True,
        "message": "FAQ更新成功"
    }


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    删除FAQ
    """
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ不存在")
    
    db.delete(faq)
    db.commit()
    
    return {
        "success": True,
        "message": "FAQ删除成功"
    }


# ========== 来源管理 ==========

@router.get("/sources", response_model=list)
async def get_sources(
    doc_type: str = None,
    region: str = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取来源列表
    """
    query = db.query(Source)
    
    if doc_type:
        query = query.filter(Source.doc_type == doc_type)
    
    if region:
        query = query.filter(Source.region == region)
    
    if keyword:
        query = query.filter(Source.title.contains(keyword))
    
    total = query.count()
    offset = (page - 1) * page_size
    sources = query.order_by(Source.created_at.desc()).offset(offset).limit(page_size).all()
    
    return sources


@router.post("/sources")
async def create_source(
    request: SourceCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    添加来源
    """
    source = Source(
        title=request.title,
        url=request.url,
        doc_type=request.doc_type,
        region=request.region,
        publish_date=request.publish_date,
        description=request.description
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    return {
        "success": True,
        "message": "来源添加成功",
        "data": {"id": source.id}
    }


@router.put("/sources/{source_id}")
async def update_source(
    source_id: int,
    request: SourceUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    更新来源
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    
    if request.title is not None:
        source.title = request.title
    if request.url is not None:
        source.url = request.url
    if request.doc_type is not None:
        source.doc_type = request.doc_type
    if request.region is not None:
        source.region = request.region
    if request.publish_date is not None:
        source.publish_date = request.publish_date
    if request.description is not None:
        source.description = request.description
    
    db.commit()
    db.refresh(source)
    
    return {
        "success": True,
        "message": "来源更新成功"
    }


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    删除来源
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    
    db.delete(source)
    db.commit()
    
    return {
        "success": True,
        "message": "来源删除成功"
    }


# ========== 知识包管理 ==========

@router.get("/knowledge-packages")
async def get_knowledge_packages(
    region: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取知识包列表
    """
    query = db.query(KnowledgePackage)
    
    if region:
        query = query.filter(KnowledgePackage.region == region)
    
    if status:
        query = query.filter(KnowledgePackage.status == status)
    
    packages = query.order_by(KnowledgePackage.created_at.desc()).all()
    
    # 转换为响应格式
    result = []
    for pkg in packages:
        # 统计FAQ和文档数量
        faq_count = db.query(FAQ).filter(FAQ.category == pkg.name).count()
        doc_count = db.query(Source).filter(Source.region == pkg.region).count()
        
        result.append({
            "id": pkg.id,
            "name": pkg.name,
            "region": pkg.region,
            "description": pkg.description,
            "status": pkg.status,
            "faq_count": faq_count,
            "doc_count": doc_count,
            "created_at": pkg.created_at,
            "updated_at": pkg.updated_at
        })
    
    return result


@router.put("/knowledge-packages/{package_id}/status")
async def update_package_status(
    package_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    更新知识包状态
    """
    package = db.query(KnowledgePackage).filter(KnowledgePackage.id == package_id).first()
    
    if not package:
        raise HTTPException(status_code=404, detail="知识包不存在")
    
    status = request.get("status")
    if status:
        package.status = status
    
    db.commit()
    db.refresh(package)
    
    return {
        "success": True,
        "message": "状态更新成功"
    }