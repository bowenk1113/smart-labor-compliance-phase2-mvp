"""用户端问答路由。"""  # 模块文档字符串，概述当前文件职责
import csv  # 导入 CSV 读写工具，供导入导出接口复用
import io  # 导入内存流工具，便于处理上传与下载内容
import json  # 导入 JSON 编解码工具，处理结构化字段
import uuid  # 导入 UUID 生成工具，补齐会话或任务标识
from datetime import date, datetime  # 导入当前模块运行所依赖的工具或类型
from typing import Optional  # 导入当前模块运行所依赖的工具或类型

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile  # 导入 FastAPI 的路由、请求和依赖注入对象
from fastapi.responses import StreamingResponse  # 导入 FastAPI 的路由、请求和依赖注入对象
from sqlalchemy import or_  # 导入 SQLAlchemy 查询构造与数据库能力
from starlette.concurrency import run_in_threadpool  # 导入 Starlette 提供的响应或线程池工具
from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力

from app.database import get_db, settings  # 导入数据库依赖与全局运行配置
from app.dependencies import get_public_tenant, normalize_pagination  # 导入请求依赖与租户隔离辅助函数
from app.models import ChatLog, FAQ, Tenant  # 导入当前业务会读写的 ORM 模型
from app.response import ok  # 导入统一成功响应与分页响应封装
from app.schemas.chat import ChatRequest, ChatResponse, ChatStopRequest, HistoryResponse  # 导入接口请求体与响应体模型
from app.security import hash_ip, sanitize_text  # 导入鉴权、脱敏和角色权限相关工具
from app.rag.service import Phase2RAGService  # 导入二期 RAG 检索与问答服务组件
from app.services.dify_service import ChatAttachment, ComplianceAnswerService  # 导入外部问答或种子数据相关服务

router = APIRouter(prefix="/api", tags=["问答"])  # 注册当前模块的路由前缀与分组标签

HISTORY_EXPORT_FIELDS = [  # 声明问答历史导出字段顺序
    "id",  # 声明导出结果中的 主键 ID 字段
    "user_id",  # 声明导出结果中的 用户 ID 字段
    "session_id",  # 声明导出结果中的 会话 ID 字段
    "conversation_id",  # 声明导出结果中的 会话 ID 字段
    "language",  # 声明导出结果中的 语言代码 字段
    "question",  # 声明导出结果中的 问题内容 字段
    "answer",  # 声明导出结果中的 回答内容 字段
    "sources",  # 声明导出结果中的 来源列表 字段
    "related_tasks",  # 声明导出结果中的 关联任务列表 字段
    "provider",  # 声明导出结果中的 服务提供方 字段
    "risk_level",  # 声明导出结果中的 风险等级 字段
    "response_time",  # 声明导出结果中的 响应耗时 字段
    "status",  # 声明导出结果中的 状态 字段
    "created_at",  # 声明导出结果中的 创建时间 字段
]  # 结束 HISTORY_EXPORT_FIELDS 的定义或组装


async def _resolve_tenant(requested_tenant_code: Optional[str], header_tenant: Tenant, db: Session) -> Tenant:  # 定义公开问答场景下的租户解析函数
    # Default to the tenant already resolved from the public request dependency.
    tenant = header_tenant  # 保存当前请求实际使用的租户对象
    if requested_tenant_code and requested_tenant_code != header_tenant.code:  # 根据当前条件决定是否进入对应业务分支
        tenant = db.query(Tenant).filter(Tenant.code == requested_tenant_code, Tenant.status == "active").first()  # 构造当前业务的基础数据库查询对象
        if not tenant:  # 租户不存在或不可用时直接终止请求
            raise HTTPException(status_code=404, detail="租户不存在或已停用")  # 抛出 HTTP 异常并把错误信息返回给前端
    return tenant  # 返回当前分支整理好的结果


def _persist_chat_log(  # 定义问答记录持久化辅助函数
    db: Session,  # 注入数据库会话，供当前逻辑访问业务数据
    tenant: Tenant,  # 传入当前操作所属的租户对象
    request: Request,  # 接收当前接口的请求对象或请求体
    *,  # 以下参数改为关键字传参，避免调用位置出错
    session_id: str,  # 接收前端会话标识，便于串联上下文
    user_id: str,  # 接收当前提问用户的标识信息
    language: str,  # 接收当前问答使用的语言代码
    question: str,  # 接收用户本次提交的问题内容
    response: ChatResponse,  # 声明参数 response，供当前逻辑使用
) -> ChatResponse:  # 结束 _persist_chat_log 的参数声明
    # Persist the final answer so history, audit, and feedback features all read from the same record.
    chat_log = ChatLog(  # 组装待写入数据库的问答日志实体
        tenant_id=tenant.id,  # 设置 ChatLog 的 租户 ID
        user_id=user_id,  # 设置 ChatLog 的 用户 ID
        session_id=session_id,  # 设置 ChatLog 的 会话 ID
        conversation_id=response.conversation_id,  # 设置 ChatLog 的 会话 ID
        language=language,  # 设置 ChatLog 的 语言代码
        question=question,  # 设置 ChatLog 的 问题内容
        answer=response.answer,  # 设置 ChatLog 的 回答内容
        sources=[item.model_dump() for item in response.sources] if response.sources else None,  # 设置 ChatLog 的 来源列表
        related_tasks=[item.model_dump() for item in response.related_tasks] if response.related_tasks else None,  # 设置 ChatLog 的 关联任务列表
        provider=response.provider,  # 设置 ChatLog 的 服务提供方
        risk_level=response.risk_level,  # 设置 ChatLog 的 风险等级
        response_time=response.response_time,  # 设置 ChatLog 的 响应耗时
        status="success",  # 设置 ChatLog 的 状态
        client_ip_hash=hash_ip(request.client.host if request.client else None),  # 设置 ChatLog 的 client ip hash
    )  # 结束 ChatLog 的定义或组装
    db.add(chat_log)  # 把新实体加入当前数据库事务等待提交
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    db.refresh(chat_log)  # 回填数据库生成的主键和默认字段
    response.question_id = chat_log.id  # 把新生成的问答记录 ID 回写到接口响应中
    return response  # 返回当前分支整理好的结果


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


def _history_query(  # 定义问答历史筛选查询构造函数
    db: Session,  # 注入数据库会话，供当前逻辑访问业务数据
    tenant: Tenant,  # 传入当前操作所属的租户对象
    user_id: str,  # 接收当前提问用户的标识信息
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    provider: Optional[str] = None,  # 接收问答服务提供方筛选参数
):  # 结束 _history_query 的参数声明
    query = db.query(ChatLog).filter(ChatLog.tenant_id == tenant.id, ChatLog.user_id == sanitize_text(user_id))  # 构造当前业务的基础数据库查询对象
    keyword = sanitize_text(keyword)  # 清洗并规范化 keyword 的输入值
    if keyword:  # 有关键字时继续追加模糊搜索条件
        like = f"%{keyword}%"  # 构造用于模糊匹配的 SQL 关键字模式
        query = query.filter(or_(ChatLog.question.like(like), ChatLog.answer.like(like)))  # 保存当前逐步拼装的数据库查询对象
    if status:  # 根据状态参数决定是否追加筛选条件
        query = query.filter(ChatLog.status == sanitize_text(status))  # 保存当前逐步拼装的数据库查询对象
    if provider:  # 根据服务来源决定是否追加筛选条件
        query = query.filter(ChatLog.provider == sanitize_text(provider))  # 保存当前逐步拼装的数据库查询对象
    return query  # 返回当前分支整理好的结果


def _serialize_history_item(item: ChatLog) -> dict:  # 定义问答历史记录序列化函数
    return {  # 返回当前分支整理好的结果
        "id": item.id,  # 填充返回或配置中的 主键 ID 字段
        "tenant_id": item.tenant_id,  # 填充返回或配置中的 租户 ID 字段
        "user_id": item.user_id,  # 填充返回或配置中的 用户 ID 字段
        "session_id": item.session_id,  # 填充返回或配置中的 会话 ID 字段
        "conversation_id": item.conversation_id,  # 填充返回或配置中的 会话 ID 字段
        "language": item.language,  # 填充返回或配置中的 语言代码 字段
        "question": item.question,  # 填充返回或配置中的 问题内容 字段
        "answer": item.answer,  # 填充返回或配置中的 回答内容 字段
        "sources": item.sources,  # 填充返回或配置中的 来源列表 字段
        "related_tasks": item.related_tasks,  # 填充返回或配置中的 关联任务列表 字段
        "provider": item.provider,  # 填充返回或配置中的 服务提供方 字段
        "risk_level": item.risk_level,  # 填充返回或配置中的 风险等级 字段
        "response_time": item.response_time,  # 填充返回或配置中的 响应耗时 字段
        "status": item.status,  # 填充返回或配置中的 状态 字段
        "created_at": item.created_at,  # 填充返回或配置中的 创建时间 字段
    }  # 结束 返回结果 的定义或组装


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


@router.post("/chat", response_model=dict)  # 为后续函数或类声明附加装饰器配置
async def chat(  # 定义纯文本问答主接口
    request_data: ChatRequest,  # 接收前端提交的问答请求体
    request: Request,  # 接收当前接口的请求对象或请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    header_tenant: Tenant = Depends(get_public_tenant),  # 注入从请求头解析出的公开租户对象
):  # 结束 chat 的参数声明
    # This is the main text-only QA endpoint used by the homepage ask button.
    if not request_data.question.strip():  # 问题为空时直接返回参数校验错误
        raise HTTPException(status_code=400, detail="问题不能为空")  # 抛出 HTTP 异常并把错误信息返回给前端

    tenant = await _resolve_tenant(request_data.tenant_code, header_tenant, db)  # 解析本次请求最终命中的租户对象

    session_id = request_data.session_id or str(uuid.uuid4())  # 生成或复用本次问答的会话标识
    user_id = sanitize_text(request_data.user_id) or "anonymous"  # 清洗并规范化 用户 ID 的输入值
    question = sanitize_text(request_data.question) or ""  # 清洗并规范化 问题内容 的输入值
    user_role = sanitize_text(request_data.user_role) or "employee"  # 清洗并规范化 用户角色 的输入值
    province = sanitize_text(request_data.province) or "陕西省"  # 清洗并规范化 省份 的输入值
    city = sanitize_text(request_data.city) or "西安市"  # 清洗并规范化 城市 的输入值

    service = Phase2RAGService()  # 实例化二期 RAG 问答服务
    response = await run_in_threadpool(  # 保存当前分支生成的响应对象
        service.answer,  # 执行当前业务步骤并推进后续处理
        question=question,  # 清洗并保存用户提交的问题文本
        scenario_id=request_data.scenario_id,  # 更新当前逻辑中的 scenario id
        session_id=session_id,  # 生成或复用本次问答的会话标识
        history=[],  # 更新当前逻辑中的 历史上下文
        user_role=user_role,  # 更新当前逻辑中的 用户角色
        province=province,  # 更新当前逻辑中的 省份
        city=city,  # 更新当前逻辑中的 城市
    )  # 执行当前业务步骤并推进后续处理

    response = _persist_chat_log(  # 落库问答结果并补齐响应中的 question_id
        db,  # 设置 _persist_chat_log 的 字段
        tenant,  # 设置 _persist_chat_log 的 字段
        request,  # 设置 _persist_chat_log 的 字段
        session_id=session_id,  # 设置 _persist_chat_log 的 会话 ID
        user_id=user_id,  # 设置 _persist_chat_log 的 用户 ID
        language=request_data.language,  # 设置 _persist_chat_log 的 语言代码
        question=question,  # 设置 _persist_chat_log 的 问题内容
        response=response,  # 设置 _persist_chat_log 的 response
    )  # 结束 _persist_chat_log 的定义或组装
    return ok(response.model_dump(), "回答生成成功")  # 按统一成功响应格式返回结果


@router.post("/chat-with-file", response_model=dict)  # 为后续函数或类声明附加装饰器配置
async def chat_with_file(  # 定义带附件的问答接口
    request: Request,  # 接收当前接口的请求对象或请求体
    question: str = Form(...),  # 接收用户本次提交的问题内容
    session_id: Optional[str] = Form(None),  # 接收前端会话标识，便于串联上下文
    user_id: Optional[str] = Form(None),  # 接收当前提问用户的标识信息
    tenant_code: Optional[str] = Form(None),  # 声明参数 tenant_code，供当前逻辑使用
    language: str = Form("zh-CN"),  # 接收当前问答使用的语言代码
    conversation_id: Optional[str] = Form(None),  # 接收外部问答服务的会话标识
    generation_id: Optional[str] = Form(None),  # 接收流式生成任务的跟踪标识
    user_role: str = Form("employee"),  # 接收提问人角色，用于控制回答口径
    province: str = Form("陕西省"),  # 接收用户所在省份，用于补充地域政策上下文
    city: str = Form("西安市"),  # 接收用户所在城市，用于补充地域政策上下文
    file: UploadFile = File(...),  # 声明参数 file，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    header_tenant: Tenant = Depends(get_public_tenant),  # 注入从请求头解析出的公开租户对象
):  # 结束 chat_with_file 的参数声明
    # This endpoint keeps the "ask with attachment" workflow and delegates file interpretation to the configured service.
    if not question.strip():  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="问题不能为空")  # 抛出 HTTP 异常并把错误信息返回给前端
    if not file.filename:  # 根据当前条件决定是否进入对应业务分支
        raise HTTPException(status_code=400, detail="请上传文件")  # 抛出 HTTP 异常并把错误信息返回给前端

    size = getattr(file, "size", None)  # 更新当前逻辑中的 size
    if size is not None and size > settings.max_upload_bytes:  # 根据当前条件决定是否进入对应业务分支
        await file.close()  # 关闭上传文件句柄，释放临时资源
        raise HTTPException(status_code=413, detail="上传文件过大")  # 抛出 HTTP 异常并把错误信息返回给前端

    tenant = await _resolve_tenant(tenant_code, header_tenant, db)  # 解析本次请求最终命中的租户对象
    session_id = session_id or str(uuid.uuid4())  # 生成或复用本次问答的会话标识
    user_id = sanitize_text(user_id) or "anonymous"  # 清洗并规范化 用户 ID 的输入值
    question = sanitize_text(question) or ""  # 清洗并规范化 问题内容 的输入值
    user_role = sanitize_text(user_role) or "employee"  # 清洗并规范化 用户角色 的输入值
    province = sanitize_text(province) or "陕西省"  # 清洗并规范化 省份 的输入值
    city = sanitize_text(city) or "西安市"  # 清洗并规范化 城市 的输入值

    service = ComplianceAnswerService(db, tenant)  # 实例化统一问答服务，优先走 Dify 再回退本地 FAQ
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        response = await run_in_threadpool(  # 保存当前分支生成的响应对象
            service.answer,  # 执行当前业务步骤并推进后续处理
            question=question,  # 清洗并保存用户提交的问题文本
            user_id=user_id,  # 规范化本次问答对应的用户标识
            conversation_id=conversation_id,  # 更新当前逻辑中的 会话 ID
            language=language,  # 更新当前逻辑中的 语言代码
            user_role=user_role,  # 更新当前逻辑中的 用户角色
            province=province,  # 更新当前逻辑中的 省份
            city=city,  # 更新当前逻辑中的 城市
            attachment=ChatAttachment(  # 更新当前逻辑中的 attachment
                filename=file.filename,  # 设置 ChatAttachment 的 filename
                content_type=file.content_type or "application/octet-stream",  # 设置 ChatAttachment 的 content type
                file=file.file,  # 设置 ChatAttachment 的 file
            ),  # 结束 ChatAttachment 的定义或组装
            generation_id=generation_id,  # 更新当前逻辑中的 generation id
        )  # 执行当前业务步骤并推进后续处理
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        await file.close()  # 关闭上传文件句柄，释放临时资源

    response = _persist_chat_log(  # 落库问答结果并补齐响应中的 question_id
        db,  # 设置 _persist_chat_log 的 字段
        tenant,  # 设置 _persist_chat_log 的 字段
        request,  # 设置 _persist_chat_log 的 字段
        session_id=session_id,  # 设置 _persist_chat_log 的 会话 ID
        user_id=user_id,  # 设置 _persist_chat_log 的 用户 ID
        language=language,  # 设置 _persist_chat_log 的 语言代码
        question=question,  # 设置 _persist_chat_log 的 问题内容
        response=response,  # 设置 _persist_chat_log 的 response
    )  # 结束 _persist_chat_log 的定义或组装
    return ok(response.model_dump(), "回答生成成功")  # 按统一成功响应格式返回结果


@router.post("/chat/stop", response_model=dict)  # 为后续函数或类声明附加装饰器配置
async def stop_chat_generation(  # 定义终止生成任务的接口
    request_data: ChatStopRequest,  # 接收前端提交的问答请求体
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    header_tenant: Tenant = Depends(get_public_tenant),  # 注入从请求头解析出的公开租户对象
):  # 结束 stop_chat_generation 的参数声明
    await _resolve_tenant(request_data.tenant_code, header_tenant, db)  # 执行当前业务步骤并推进后续处理
    stopped = ComplianceAnswerService.stop_generation(request_data.generation_id)  # 更新当前逻辑中的 stopped
    return ok({"stopped": stopped}, "停止生成请求已处理")  # 按统一成功响应格式返回结果


@router.get("/history", response_model=dict)  # 为后续函数或类声明附加装饰器配置
async def get_history(  # 定义问答历史分页查询接口
    user_id: str = "anonymous",  # 接收当前提问用户的标识信息
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    provider: Optional[str] = None,  # 接收问答服务提供方筛选参数
    all_items: bool = False,  # 声明参数 all_items，供当前逻辑使用
    page: int = 1,  # 接收分页页码参数
    page_size: int = 20,  # 接收每页返回条数参数
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    tenant: Tenant = Depends(get_public_tenant),  # 传入当前操作所属的租户对象
):  # 结束 get_history 的参数声明
    page, page_size = normalize_pagination(page, page_size)  # 执行当前业务步骤并推进后续处理
    query = _history_query(db, tenant, user_id, keyword, status, provider)  # 保存当前逐步拼装的数据库查询对象
    total = query.count()  # 统计满足当前筛选条件的记录总数
    ordered = query.order_by(ChatLog.created_at.desc(), ChatLog.id.desc())  # 更新当前逻辑中的 ordered
    logs = ordered.all() if all_items else ordered.offset((page - 1) * page_size).limit(page_size).all()  # 更新当前逻辑中的 logs
    data = HistoryResponse(total=total, page=page, page_size=page_size, list=logs)  # 整理当前接口最终要返回的数据结构
    return ok(data.model_dump(), "历史记录获取成功")  # 按统一成功响应格式返回结果


@router.get("/history/export")  # 为后续函数或类声明附加装饰器配置
async def export_history(  # 定义问答历史导出接口
    user_id: str = "anonymous",  # 接收当前提问用户的标识信息
    keyword: Optional[str] = None,  # 接收关键字筛选参数
    status: Optional[str] = None,  # 接收状态筛选或更新参数
    provider: Optional[str] = None,  # 接收问答服务提供方筛选参数
    ids: Optional[str] = None,  # 声明参数 ids，供当前逻辑使用
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    tenant: Tenant = Depends(get_public_tenant),  # 传入当前操作所属的租户对象
):  # 结束 export_history 的参数声明
    query = _history_query(db, tenant, user_id, keyword, status, provider)  # 保存当前逐步拼装的数据库查询对象
    parsed_ids = _parse_ids(ids)  # 解析批量操作请求中的 ID 列表
    if parsed_ids:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(ChatLog.id.in_(parsed_ids))  # 保存当前逐步拼装的数据库查询对象
    logs = query.order_by(ChatLog.created_at.desc(), ChatLog.id.desc()).all()  # 更新当前逻辑中的 logs
    rows = [_serialize_history_item(item) for item in logs]  # 更新当前逻辑中的 rows
    return _csv_text_response("history.csv", rows, HISTORY_EXPORT_FIELDS)  # 返回当前分支整理好的结果


@router.delete("/history")  # 为后续函数或类声明附加装饰器配置
async def clear_history(  # 定义异步处理函数 clear_history
    user_id: str = "anonymous",  # 接收当前提问用户的标识信息
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    tenant: Tenant = Depends(get_public_tenant),  # 传入当前操作所属的租户对象
):  # 结束 clear_history 的参数声明
    db.query(ChatLog).filter(ChatLog.tenant_id == tenant.id, ChatLog.user_id == sanitize_text(user_id)).delete()  # 执行当前业务步骤并推进后续处理
    db.commit()  # 提交本次数据库事务，持久化前面的变更
    return ok(message="历史记录已清空")  # 按统一成功响应格式返回结果


@router.get("/recommended-questions")  # 为后续函数或类声明附加装饰器配置
async def get_recommended_questions(  # 定义获取 recommended questions 的接口或辅助函数
    scenario_id: Optional[str] = None,  # 接收前端选择的问答场景标识
    db: Session = Depends(get_db),  # 注入数据库会话，供当前逻辑访问业务数据
    tenant: Tenant = Depends(get_public_tenant),  # 传入当前操作所属的租户对象
):  # 结束 get_recommended_questions 的参数声明
    if scenario_id:  # 根据当前条件决定是否进入对应业务分支
        return ok(Phase2RAGService().recommended_questions(scenario_id))  # 按统一成功响应格式返回结果
    faqs = (  # 更新当前逻辑中的 faqs
        db.query(FAQ)  # 执行当前业务步骤并推进后续处理
        .filter(FAQ.tenant_id == tenant.id)  # 执行当前业务步骤并推进后续处理
        .order_by(FAQ.updated_at.desc())  # 执行当前业务步骤并推进后续处理
        .limit(8)  # 执行当前业务步骤并推进后续处理
        .all()  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    data = [  # 整理当前接口最终要返回的数据结构
        {"id": item.id, "question": item.question, "category": item.category, "risk_level": item.risk_level}  # 补充列表中的 主键 ID 项
        for item in faqs  # 补充列表中的 for item in faqs 项
    ]  # 结束 data 的定义或组装
    return ok(data)  # 按统一成功响应格式返回结果


@router.get("/scenarios")  # 为后续函数或类声明附加装饰器配置
async def get_scenarios():  # 定义获取 scenarios 的接口或辅助函数
    """返回前端可选的二期 RAG 业务场景。"""  # 函数文档字符串，说明 get_scenarios 的职责

    return ok(Phase2RAGService.scenarios())  # 按统一成功响应格式返回结果


@router.get("/tenant-public")  # 为后续函数或类声明附加装饰器配置
async def get_tenant_public(tenant: Tenant = Depends(get_public_tenant)):  # 定义获取 tenant public 的接口或辅助函数
    return ok(  # 按统一成功响应格式返回结果
        {  # 设置 ok 的 字段
            "id": tenant.id,  # 设置 ok 的 主键 ID
            "code": tenant.code,  # 设置 ok 的 code
            "name": tenant.name,  # 设置 ok 的 名称
            "region": tenant.region,  # 设置 ok 的 地区
            "industry": tenant.industry,  # 设置 ok 的 industry
        }  # 设置 ok 的 字段
    )  # 结束 ok 的定义或组装
