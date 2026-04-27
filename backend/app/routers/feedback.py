"""
反馈路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate, FeedbackResponse
from app.models.feedback import Feedback

router = APIRouter(prefix="/api", tags=["反馈"])


@router.post("/feedback")
async def create_feedback(
    request: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    提交反馈
    """
    feedback = Feedback(
        question_id=request.question_id,
        user_id=request.user_id,
        is_helpful=request.is_helpful,
        remark=request.remark,
        status="pending"
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return {
        "success": True,
        "message": "反馈提交成功",
        "data": {"id": feedback.id}
    }


# 管理端反馈路由
from app.routers.admin import get_current_admin


@router.get("/admin/feedbacks", response_model=list)
async def get_feedbacks(
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    获取反馈列表（管理端）
    """
    query = db.query(Feedback)
    
    if status:
        query = query.filter(Feedback.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    feedbacks = query.order_by(Feedback.created_at.desc()).offset(offset).limit(page_size).all()
    
    return feedbacks


@router.put("/admin/feedbacks/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    request: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    更新反馈状态（管理端）
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    if request.status:
        feedback.status = request.status
    
    db.commit()
    db.refresh(feedback)
    
    return {
        "success": True,
        "message": "更新成功"
    }