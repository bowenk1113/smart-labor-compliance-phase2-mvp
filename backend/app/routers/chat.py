"""
问答路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, HistoryResponse
from app.models.chat_log import ChatLog
import uuid
import time

router = APIRouter(prefix="/api", tags=["问答"])


# 推荐问题列表
RECOMMENDED_QUESTIONS = [
    "陕西产假多少天",
    "西安劳动仲裁去哪里",
    "居民医保断缴后怎么处理",
    "试用期工资标准",
    "加班费计算方式"
]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    提交问题，获取智能回答
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    # 生成会话ID
    session_id = request.session_id or str(uuid.uuid4())
    user_id = request.user_id or "anonymous"
    
    # Dify 功能已暂时禁用
    response = ChatResponse(
        answer="抱歉，智能问答功能暂时维护中，请稍后再试。您可以先查看常见问题或联系管理员获取帮助。",
        response_time=0
    )
    
    # 保存问答记录
    try:
        chat_log = ChatLog(
            user_id=user_id,
            session_id=session_id,
            question=request.question,
            answer=response.answer,
            sources=None,
            related_tasks=None,
            response_time=response.response_time,
            status="success" if response.answer else "failed"
        )
        db.add(chat_log)
        db.commit()
    except Exception as e:
        print(f"保存问答记录失败: {e}")
        db.rollback()
    
    return response


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    user_id: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """
    获取用户历史记录
    """
    query = db.query(ChatLog)
    
    if user_id:
        query = query.filter(ChatLog.user_id == user_id)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    offset = (page - 1) * page_size
    logs = query.order_by(ChatLog.created_at.desc()).offset(offset).limit(page_size).all()
    
    return HistoryResponse(
        total=total,
        list=logs
    )


@router.delete("/history")
async def clear_history(user_id: str = None, db: Session = Depends(get_db)):
    """
    清空用户历史记录
    """
    query = db.query(ChatLog)
    
    if user_id:
        query = query.filter(ChatLog.user_id == user_id)
    
    query.delete()
    db.commit()
    
    return {"success": True, "message": "历史记录已清空"}


@router.get("/recommended-questions")
async def get_recommended_questions():
    """
    获取推荐问题
    """
    return {
        "success": True,
        "data": RECOMMENDED_QUESTIONS
    }