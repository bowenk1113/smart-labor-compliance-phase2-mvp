"""反馈路由。"""  # 模块文档字符串，概述当前文件职责
from fastapi import APIRouter, Depends, HTTPException  # 导入 FastAPI 的路由、请求和依赖注入对象
from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力

from app.database import get_db  # 导入数据库依赖与全局运行配置
from app.dependencies import get_admin_tenant_filter, get_current_admin, get_public_tenant, normalize_pagination  # 导入请求依赖与租户隔离辅助函数
from app.models import ChatLog, Feedback, Tenant  # 导入当前业务会读写的 ORM 模型
from app.response import ok, page as page_response  # 导入统一成功响应与分页响应封装
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate  # 导入接口请求体与响应体模型
from app.security import sanitize_text  # 导入鉴权、脱敏和角色权限相关工具

router = APIRouter(prefix="/api", tags=["反馈"])  # 注册当前模块的路由前缀与分组标签


def _require_permission(current_admin: dict, permission: str) -> None:  # 定义后台权限校验辅助函数
    if permission not in current_admin.get("permissions", []):  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=403, detail="当前账号没有该操作权限")  # 抛出 HTTP 异常并把错误信息返回给前端


@router.post("/feedback")  # 为后续函数或类声明附加装饰器配置
async def create_feedback(  # 定义用户提交反馈的接口
    request: FeedbackCreate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    header_tenant: Tenant = Depends(get_public_tenant),  # 注入从请求头解析出的公开租户对象
):  # 结束 create_feedback 的参数声明
    tenant = header_tenant  # 保存当前请求实际使用的租户对象
    if request.tenant_code and request.tenant_code != tenant.code:  # 根据当前条件决定是否进入对应业务分支
        tenant = db.query(Tenant).filter(Tenant.code == request.tenant_code, Tenant.status == "active").first()  # 构造当前业务的基础数据库查询对象
        if not tenant:  # 租户不存在或不可用时直接终止请求
            raise HTTPException(status_code=404, detail="租户不存在或已停用")  # 抛出 HTTP 异常并把错误信息返回给前端

    if request.question_id:  # 仅在提交了问答记录 ID 时校验关联关系
        exists = db.query(ChatLog).filter(ChatLog.id == request.question_id, ChatLog.tenant_id == tenant.id).first()  # 构造当前业务的基础数据库查询对象
        if not exists:  # 根据当前条件决定是否进入对应业务分支
            raise HTTPException(status_code=404, detail="问答记录不存在")  # 抛出 HTTP 异常并把错误信息返回给前端

    feedback = Feedback(  # 组装待写入数据库的反馈实体
        tenant_id=tenant.id,  # 设置 Feedback 的 租户 ID
        question_id=request.question_id,  # 设置 Feedback 的 关联问答 ID
        user_id=sanitize_text(request.user_id) or "anonymous",  # 设置 Feedback 的 用户 ID
        is_helpful=request.is_helpful,  # 设置 Feedback 的 是否有帮助
        remark=sanitize_text(request.remark),  # 设置 Feedback 的 备注
        status="pending",  # 设置 Feedback 的 状态
    )  # 结束 Feedback 的定义或组装
    db.add(feedback)  # 把新实体加入当前数据库事务等待提交
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(feedback)  # 回填数据库生成的主键和默认字段
    return ok({"id": feedback.id}, "反馈提交成功")  # 按统一成功响应格式返回结果


@router.get("/admin/feedbacks")  # 为后续函数或类声明附加装饰器配置
async def get_feedbacks(  # 定义后台反馈列表查询接口
    tenant_id: int | None = None,  # 接收需要筛选或校验的租户 ID
    status: str | None = None,  # 接收状态筛选或更新参数
    is_helpful: bool | None = None,  # 接收反馈是否有帮助的筛选条件
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 get_feedbacks 的参数声明
    _require_permission(current_admin, "feedbacks")  # 执行当前业务步骤并推进后续处理
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    allowed_tenant_id = get_admin_tenant_filter(current_admin, tenant_id)  # 计算当前管理员允许访问的租户范围
    query = db.query(Feedback)  # 构造当前业务的基础数据库查询对象
    if allowed_tenant_id:  # 租户管理员场景下追加租户隔离过滤
        query = query.filter(Feedback.tenant_id == allowed_tenant_id)  # 保存当前逐步拼装的数据库查询对象
    if status:  # 根据状态参数决定是否追加筛选条件
        query = query.filter(Feedback.status == status)  # 保存当前逐步拼装的数据库查询对象
    if is_helpful is not None:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(Feedback.is_helpful.is_(is_helpful))  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    items = query.order_by(Feedback.id.asc()).offset((page - 1) * page_size).limit(page_size).all()  # 按排序和分页参数查询当前页数据
    data = [  # 整理当前接口最终要返回的数据结构
        {  # 补充列表中的 { 项
            "id": item.id,  # 补充列表中的 主键 ID 项
            "tenant_id": item.tenant_id,  # 补充列表中的 租户 ID 项
            "tenant_name": item.tenant.name if item.tenant else "",  # 补充列表中的 租户名称 项
            "question_id": item.question_id,  # 补充列表中的 关联问答 ID 项
            "question": item.chat_log.question if item.chat_log else "",  # 补充列表中的 问题内容 项
            "user_id": item.user_id,  # 补充列表中的 用户 ID 项
            "is_helpful": item.is_helpful,  # 补充列表中的 是否有帮助 项
            "remark": item.remark,  # 补充列表中的 备注 项
            "status": item.status,  # 补充列表中的 状态 项
            "created_at": item.created_at,  # 补充列表中的 创建时间 项
        }  # 补充列表中的 } 项
        for item in items  # 补充列表中的 for item in items 项
    ]  # 结束 data 的定义或组装
    return page_response(data, total, page, page_size)  # 按统一分页响应格式返回列表数据


@router.put("/admin/feedbacks/{feedback_id}")  # 为后续函数或类声明附加装饰器配置
async def update_feedback(  # 定义后台反馈状态更新接口
    feedback_id: int,  # 声明参数 feedback_id，供当前逻辑使用
    request: FeedbackUpdate,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    current_admin: dict = Depends(get_current_admin),  # 注入当前登录管理员的身份与权限信息
):  # 结束 update_feedback 的参数声明
    _require_permission(current_admin, "feedbacks")  # 执行当前业务步骤并推进后续处理
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()  # 构造当前业务的基础数据库查询对象
    if not feedback:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=404, detail="反馈不存在")  # 抛出 HTTP 异常并把错误信息返回给前端
    get_admin_tenant_filter(current_admin, feedback.tenant_id)  # 执行当前业务步骤并推进后续处理
    if request.status:  # 根据状态参数决定是否追加筛选条件
        if request.status not in {"pending", "processing", "resolved", "ignored"}:  # 根据状态参数决定是否追加筛选条件
            raise HTTPException(status_code=400, detail="无效的反馈状态")  # 抛出 HTTP 异常并把错误信息返回给前端
        feedback.status = request.status  # 更新当前逻辑中的 状态
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(feedback)  # 回填数据库生成的主键和默认字段
    return ok(message="反馈更新成功")  # 按统一成功响应格式返回结果
