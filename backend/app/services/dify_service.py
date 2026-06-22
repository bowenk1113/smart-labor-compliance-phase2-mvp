"""Dify 与本地 FAQ 的统一问答服务。"""  # 模块文档字符串，概述当前文件职责
from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import json  # 导入 JSON 编解码工具，处理结构化字段
import logging  # 导入日志模块，记录外部服务调用情况
import re  # 导入当前模块运行所依赖的工具或类型
import threading  # 导入线程同步工具，保护共享状态一致性
import time  # 导入时间工具，统计耗时或生成时间戳
from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型
from difflib import SequenceMatcher  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from typing import Any, BinaryIO, Optional, cast  # 导入当前模块运行所依赖的工具或类型

import requests  # 导入 HTTP 客户端，调用外部 Dify 或 RAGFlow 服务
from sqlalchemy import or_  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力

from app.database import settings  # 导入数据库依赖与全局运行配置
from app.models import FAQ, KnowledgePackage, Source, Tenant  # 导入当前业务会读写的 ORM 模型
from app.schemas.chat import ChatResponse, SourceInfo, TaskInfo  # 导入接口请求体与响应体模型
from app.security import sanitize_text  # 导入鉴权、脱敏和角色权限相关工具


logger = logging.getLogger(__name__)  # 创建当前模块的日志记录器

DISCLAIMER = (  # 定义回答统一附带的合规免责声明
    "本回答用于企业合规辅助和演示，不替代正式法律意见。涉及具体待遇、金额、期限或争议处理时，"  # 执行当前业务步骤并推进后续处理
    "请以当地人社、医保、税务等官方经办口径及企业制度最终复核为准。"  # 执行当前业务步骤并推进后续处理
)  # 执行当前业务步骤并推进后续处理

USER_ROLE_LABELS = {  # 维护用户角色编码与中文名称的映射
    "enterprise_hr": "企业HR",  # 填充返回或配置中的 enterprise hr 字段
    "administrator_staff": "行政人员",  # 填充返回或配置中的 administrator staff 字段
    "legal_staff": "法务人员",  # 填充返回或配置中的 legal staff 字段
    "employee": "员工",  # 填充返回或配置中的 employee 字段
    "admin_user": "管理员",  # 填充返回或配置中的 admin user 字段
}  # 结束 USER_ROLE_LABELS 的定义或组装


_generation_tasks: dict[str, dict[str, str]] = {}  # 缓存当前生成任务的执行状态
_generation_tasks_lock = threading.Lock()  # 保护生成任务状态并发读写的线程锁


@dataclass  # 为后续函数或类声明附加装饰器配置
class ChatAttachment:  # 定义上传到 Dify 的附件数据结构
    """待转交给 Dify 的用户附件。"""  # 类文档字符串，概述 ChatAttachment 的用途

    filename: str  # 执行当前业务步骤并推进后续处理
    content_type: str  # 执行当前业务步骤并推进后续处理
    file: BinaryIO  # 执行当前业务步骤并推进后续处理


class ComplianceAnswerService:  # 定义 Dify 与本地 FAQ 的统一问答服务
    """先尝试 Dify，失败或未配置时回退到本地 FAQ。"""  # 类文档字符串，概述 ComplianceAnswerService 的用途

    def __init__(self, db: Session, tenant: Tenant):  # 定义业务处理函数 __init__
        self.db = db  # 把数据库会话保存到服务实例，供后续查询复用
        self.tenant = tenant  # 把当前租户对象保存到服务实例，供问答上下文复用

    def answer(  # 定义统一问答执行入口
        self,  # 声明参数 self，供当前逻辑使用
        question: str,  # 接收用户本次提交的问题内容
        user_id: Optional[str] = None,  # 接收当前提问用户的标识信息
        conversation_id: Optional[str] = None,  # 接收外部问答服务的会话标识
        language: str = "zh-CN",  # 接收当前问答使用的语言代码
        user_role: str = "employee",  # 接收提问人角色，用于控制回答口径
        province: str = "陕西省",  # 接收用户所在省份，用于补充地域政策上下文
        city: str = "西安市",  # 接收用户所在城市，用于补充地域政策上下文
        attachment: Optional[ChatAttachment] = None,  # 接收上传给外部问答服务的附件对象
        generation_id: Optional[str] = None,  # 接收流式生成任务的跟踪标识
    ) -> ChatResponse:  # 结束 answer 的参数声明
        question = sanitize_text(question) or ""  # 清洗并规范化 问题内容 的输入值
        start_time = int(time.time() * 1000)  # 更新当前逻辑中的 start time
        if not self._has_active_package():  # 根据当前条件决定是否进入对应业务分支
            response = ChatResponse(  # 构建当前分支要返回的问答响应对象
                answer=self._with_context_prefix(self._inactive_package_answer(question), user_role, province, city),  # 设置 ChatResponse 的 回答内容
                sources=None,  # 设置 ChatResponse 的 来源列表
                related_tasks=[],  # 设置 ChatResponse 的 关联任务列表
                response_time=int(time.time() * 1000) - start_time,  # 设置 ChatResponse 的 响应耗时
                provider="knowledge_package_disabled",  # 设置 ChatResponse 的 服务提供方
                risk_level=self._estimate_risk(question),  # 设置 ChatResponse 的 风险等级
                suggestions=[],  # 设置 ChatResponse 的 建议列表
                disclaimer=DISCLAIMER,  # 设置 ChatResponse 的 免责声明
            )  # 结束 ChatResponse 的定义或组装
            return response  # 返回当前分支整理好的结果

        tenant_dify_key_value = getattr(self.tenant, "dify_api_key", None)  # 更新当前逻辑中的 tenant dify key value
        tenant_dify_key = str(tenant_dify_key_value).strip() if tenant_dify_key_value is not None else ""  # 更新当前逻辑中的 tenant dify key
        dify_key = tenant_dify_key if tenant_dify_key != "" else str(settings.dify_api_key or "")  # 更新当前逻辑中的 dify key
        if dify_key != "":  # 根据当前条件决定是否进入对应业务分支
            dify_response = self._call_dify(  # 更新当前逻辑中的 dify response
                question,  # 设置 _call_dify 的 字段
                dify_key,  # 设置 _call_dify 的 字段
                user_id,  # 设置 _call_dify 的 字段
                conversation_id,  # 设置 _call_dify 的 字段
                user_role,  # 设置 _call_dify 的 字段
                province,  # 设置 _call_dify 的 字段
                city,  # 设置 _call_dify 的 字段
                attachment,  # 设置 _call_dify 的 字段
                generation_id,  # 设置 _call_dify 的 字段
            )  # 结束 _call_dify 的定义或组装
            if dify_response:  # 根据当前条件决定是否进入对应业务分支
                dify_response.response_time = int(time.time() * 1000) - start_time  # 更新当前逻辑中的 响应耗时
                return dify_response  # 返回当前分支整理好的结果

        if attachment:  # 附件模式下切换到文件问答处理分支
            return ChatResponse(  # 返回当前分支整理好的结果
                answer=self._with_context_prefix(  # 设置 ChatResponse 的 回答内容
                    "已收到附件，但文件内容解析必须由 Dify 完成。当前 Dify 未配置或调用失败，"  # 设置 _with_context_prefix 的 字段
                    "系统未对附件内容进行本地解析，请检查 Dify 应用密钥、文件上传能力和工作流配置后重试。",  # 设置 _with_context_prefix 的 字段
                    user_role,  # 设置 _with_context_prefix 的 字段
                    province,  # 设置 _with_context_prefix 的 字段
                    city,  # 设置 _with_context_prefix 的 字段
                ),  # 结束 _with_context_prefix 的定义或组装
                sources=None,  # 设置 ChatResponse 的 来源列表
                related_tasks=[],  # 设置 ChatResponse 的 关联任务列表
                response_time=int(time.time() * 1000) - start_time,  # 设置 ChatResponse 的 响应耗时
                provider="dify_unavailable",  # 设置 ChatResponse 的 服务提供方
                risk_level=self._estimate_risk(question),  # 设置 ChatResponse 的 风险等级
                suggestions=[],  # 设置 ChatResponse 的 建议列表
                disclaimer=DISCLAIMER,  # 设置 ChatResponse 的 免责声明
            )  # 结束 ChatResponse 的定义或组装

        local_response = self._answer_from_faq(question, language)  # 更新当前逻辑中的 local response
        local_response.answer = self._with_context_prefix(local_response.answer, user_role, province, city)  # 更新当前逻辑中的 回答内容
        local_response.response_time = int(time.time() * 1000) - start_time  # 更新当前逻辑中的 响应耗时
        return local_response  # 返回当前分支整理好的结果

    def _call_dify(  # 定义 Dify 问答调用逻辑
        self,  # 声明参数 self，供当前逻辑使用
        question: str,  # 接收用户本次提交的问题内容
        api_key: str,  # 声明参数 api_key，供当前逻辑使用
        user_id: Optional[str],  # 接收当前提问用户的标识信息
        conversation_id: Optional[str],  # 接收外部问答服务的会话标识
        user_role: str,  # 接收提问人角色，用于控制回答口径
        province: str,  # 接收用户所在省份，用于补充地域政策上下文
        city: str,  # 接收用户所在城市，用于补充地域政策上下文
        attachment: Optional[ChatAttachment] = None,  # 接收上传给外部问答服务的附件对象
        generation_id: Optional[str] = None,  # 接收流式生成任务的跟踪标识
    ) -> Optional[ChatResponse]:  # 结束 _call_dify 的参数声明
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            region = f"{province}{city}" if province and city else (province or city or self.tenant.region)  # 组合省市信息，作为外部问答服务的地域上下文
            payload = {  # 组装发往外部问答服务的请求载荷
                "query": question,  # 向 Dify 请求体写入 query
                "user": user_id or "anonymous",  # 向 Dify 请求体写入 user
                "response_mode": "streaming",  # 向 Dify 请求体写入 response mode
                "inputs": {  # 向 Dify 请求体写入 inputs
                    "tenant_code": self.tenant.code,  # 向 Dify 请求体写入 tenant code
                    "tenant_name": self.tenant.name,  # 向 Dify 请求体写入 租户名称
                    "region": region,  # 向 Dify 请求体写入 地区
                    "province": province,  # 向 Dify 请求体写入 province
                    "city": city,  # 向 Dify 请求体写入 city
                    "user_role": USER_ROLE_LABELS.get(user_role, user_role),  # 向 Dify 请求体写入 user role
                    "answer_style": "结构清晰、结论先行、引用来源、明确风险等级和待核验项",  # 向 Dify 请求体写入 answer style
                },  # 结束 payload 的定义或组装
            }  # 结束 payload 的定义或组装
            if conversation_id:  # 已有外部会话 ID 时继续沿用同一轮对话上下文
                payload["conversation_id"] = conversation_id  # 执行当前业务步骤并推进后续处理
            if attachment:  # 附件模式下切换到文件问答处理分支
                upload_file_id = self._upload_file_to_dify(api_key, user_id, attachment)  # 更新当前逻辑中的 上传文件 ID
                if not upload_file_id:  # 根据当前条件决定是否进入对应业务分支
                    logger.warning("Dify file upload failed; falling back to local FAQ. filename=%s", attachment.filename)  # 记录外部服务异常或降级信息，便于排查问题
                    return None  # 返回当前分支整理好的结果
                payload["files"] = [  # 执行当前业务步骤并推进后续处理
                    {  # 执行当前业务步骤并推进后续处理
                        "type": self._dify_file_type(attachment.filename, attachment.content_type),  # 执行当前业务步骤并推进后续处理
                        "transfer_method": "local_file",  # 执行当前业务步骤并推进后续处理
                        "upload_file_id": upload_file_id,  # 执行当前业务步骤并推进后续处理
                    }  # 执行当前业务步骤并推进后续处理
                ]  # 执行当前业务步骤并推进后续处理

            response = requests.post(  # 保存当前分支生成的响应对象
                f"{settings.dify_base_url.rstrip('/')}/chat-messages",  # 设置 post 的 字段
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},  # 设置 post 的 Authorization
                json=payload,  # 设置 post 的 json
                stream=True,  # 设置 post 的 stream
                timeout=settings.dify_timeout_seconds,  # 设置 post 的 timeout
            )  # 结束 post 的定义或组装
            if response.status_code != 200:  # 根据状态参数决定是否追加筛选条件
                logger.warning(  # 记录外部服务异常或降级信息，便于排查问题
                    "Dify chat request failed; falling back to local FAQ. status=%s body=%s",  # 执行当前业务步骤并推进后续处理
                    response.status_code,  # 执行当前业务步骤并推进后续处理
                    response.text[:1000],  # 执行当前业务步骤并推进后续处理
                )  # 执行当前业务步骤并推进后续处理
                return None  # 返回当前分支整理好的结果

            data = self._consume_dify_stream(response, generation_id, api_key, user_id or "anonymous")  # 整理当前接口最终要返回的数据结构
            if not data:  # 根据当前条件决定是否进入对应业务分支
                return None  # 返回当前分支整理好的结果

            metadata = data.get("metadata") or {}  # 更新当前逻辑中的 metadata
            sources = []  # 更新当前逻辑中的 来源列表
            for resource in metadata.get("retriever_resources", []):  # 遍历当前集合中的每一项并逐个处理
                sources.append(  # 把当前来源信息追加到结果来源列表
                    SourceInfo(  # 执行当前业务步骤并推进后续处理
                        title=resource.get("document_name") or resource.get("title") or "Dify 知识库来源",  # 更新当前逻辑中的 标题
                        url=resource.get("url"),  # 更新当前逻辑中的 链接地址
                        snippet=(resource.get("content") or "")[:220],  # 更新当前逻辑中的 snippet
                    )  # 执行当前业务步骤并推进后续处理
                )  # 执行当前业务步骤并推进后续处理
            answer = self._normalize_answer(data.get("answer") or "")  # 更新当前逻辑中的 回答内容
            return ChatResponse(  # 返回当前分支整理好的结果
                answer=answer,  # 设置 ChatResponse 的 回答内容
                sources=sources or None,  # 设置 ChatResponse 的 来源列表
                related_tasks=self._extract_tasks(question),  # 设置 ChatResponse 的 关联任务列表
                response_time=0,  # 设置 ChatResponse 的 响应耗时
                conversation_id=data.get("conversation_id"),  # 设置 ChatResponse 的 会话 ID
                question_id=None,  # 设置 ChatResponse 的 关联问答 ID
                provider="dify",  # 设置 ChatResponse 的 服务提供方
                risk_level=self._risk_from_answer(answer) or self._estimate_risk(question),  # 设置 ChatResponse 的 风险等级
                suggestions=self._suggestions(question),  # 设置 ChatResponse 的 建议列表
                disclaimer=DISCLAIMER,  # 设置 ChatResponse 的 免责声明
            )  # 结束 ChatResponse 的定义或组装
        except requests.Timeout as exc:  # 捕获异常并执行降级或错误处理逻辑
            logger.warning(  # 记录外部服务异常或降级信息，便于排查问题
                "Dify chat request timed out after %ss; falling back to local FAQ. url=%s error=%s",  # 执行当前业务步骤并推进后续处理
                settings.dify_timeout_seconds,  # 执行当前业务步骤并推进后续处理
                f"{settings.dify_base_url.rstrip('/')}/chat-messages",  # 执行当前业务步骤并推进后续处理
                exc,  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
            return None  # 返回当前分支整理好的结果
        except requests.RequestException as exc:  # 捕获异常并执行降级或错误处理逻辑
            logger.warning("Dify chat request failed; falling back to local FAQ. error=%s", exc)  # 记录外部服务异常或降级信息，便于排查问题
            return None  # 返回当前分支整理好的结果
        finally:  # 无论成功失败都执行资源释放或收尾逻辑
            if generation_id:  # 根据当前条件决定是否进入对应业务分支
                self._unregister_generation(generation_id)  # 执行当前业务步骤并推进后续处理

    def _consume_dify_stream(  # 定义业务处理函数 _consume_dify_stream
        self,  # 声明参数 self，供当前逻辑使用
        response: requests.Response,  # 声明参数 response，供当前逻辑使用
        generation_id: Optional[str],  # 接收流式生成任务的跟踪标识
        api_key: str,  # 声明参数 api_key，供当前逻辑使用
        user_id: str,  # 接收当前提问用户的标识信息
    ) -> Optional[dict]:  # 结束 _consume_dify_stream 的参数声明
        answer_parts: list[str] = []  # 更新当前逻辑中的 answer parts
        final_data: dict = {}  # 更新当前逻辑中的 final data
        metadata: dict = {}  # 更新当前逻辑中的 metadata
        task_id = ""  # 更新当前逻辑中的 task id

        for raw_line in response.iter_lines(decode_unicode=True):  # 遍历当前集合中的每一项并逐个处理
            if not raw_line:  # 跳过当前空白 ID 片段，避免解析报错
                continue  # 跳过当前项，继续处理下一项数据
            if raw_line.startswith("event:"):  # 根据当前条件决定是否进入对应业务分支
                continue  # 跳过当前项，继续处理下一项数据
            if not raw_line.startswith("data:"):  # 跳过当前空白 ID 片段，避免解析报错
                continue  # 跳过当前项，继续处理下一项数据

            try:  # 尝试执行可能依赖外部服务或数据库的逻辑
                event = json.loads(raw_line[5:].strip())  # 更新当前逻辑中的 event
            except json.JSONDecodeError:  # 捕获异常并执行降级或错误处理逻辑
                logger.warning("Failed to decode Dify stream line: %s", raw_line[:300])  # 记录外部服务异常或降级信息，便于排查问题
                continue  # 跳过当前项，继续处理下一项数据

            task_id = task_id or str(event.get("task_id") or "")  # 更新当前逻辑中的 task id
            if generation_id and task_id:  # 根据当前条件决定是否进入对应业务分支
                self._register_generation(generation_id, task_id, api_key, user_id)  # 执行当前业务步骤并推进后续处理

            event_type = event.get("event")  # 更新当前逻辑中的 event type
            if event_type == "message":  # 根据当前条件决定是否进入对应业务分支
                answer_parts.append(event.get("answer") or "")  # 执行当前业务步骤并推进后续处理
                final_data["conversation_id"] = event.get("conversation_id") or final_data.get("conversation_id")  # 执行当前业务步骤并推进后续处理
                final_data["message_id"] = event.get("message_id") or final_data.get("message_id")  # 执行当前业务步骤并推进后续处理
            elif event_type == "message_end":  # 前一个条件不满足时继续判断其他分支
                metadata = event.get("metadata") or {}  # 更新当前逻辑中的 metadata
                final_data["conversation_id"] = event.get("conversation_id") or final_data.get("conversation_id")  # 执行当前业务步骤并推进后续处理
                final_data["message_id"] = event.get("message_id") or final_data.get("message_id")  # 执行当前业务步骤并推进后续处理
            elif event_type == "workflow_finished":  # 前一个条件不满足时继续判断其他分支
                data = event.get("data") or {}  # 整理当前接口最终要返回的数据结构
                outputs = data.get("outputs") or {}  # 更新当前逻辑中的 outputs
                if outputs.get("answer"):  # 根据当前条件决定是否进入对应业务分支
                    answer_parts = [outputs["answer"]]  # 更新当前逻辑中的 answer parts
            elif event_type == "error":  # 前一个条件不满足时继续判断其他分支
                logger.warning("Dify stream returned error: %s", event)  # 记录外部服务异常或降级信息，便于排查问题
                return None  # 返回当前分支整理好的结果

        final_data["answer"] = "".join(answer_parts)  # 执行当前业务步骤并推进后续处理
        final_data["metadata"] = metadata  # 执行当前业务步骤并推进后续处理
        return final_data if final_data["answer"] else None  # 返回当前分支整理好的结果

    @classmethod  # 为后续函数或类声明附加装饰器配置
    def _register_generation(cls, generation_id: str, task_id: str, api_key: str, user_id: str) -> None:  # 定义业务处理函数 _register_generation
        with _generation_tasks_lock:  # 执行当前业务步骤并推进后续处理
            _generation_tasks[generation_id] = {  # 更新当前逻辑中的  generation tasks[generation id]
                "task_id": task_id,  # 执行当前业务步骤并推进后续处理
                "api_key": api_key,  # 执行当前业务步骤并推进后续处理
                "user_id": user_id,  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理

    @classmethod  # 为后续函数或类声明附加装饰器配置
    def _unregister_generation(cls, generation_id: str) -> None:  # 定义业务处理函数 _unregister_generation
        with _generation_tasks_lock:  # 执行当前业务步骤并推进后续处理
            _generation_tasks.pop(generation_id, None)  # 执行当前业务步骤并推进后续处理

    @classmethod  # 为后续函数或类声明附加装饰器配置
    def stop_generation(cls, generation_id: str) -> bool:  # 定义业务处理函数 stop_generation
        with _generation_tasks_lock:  # 执行当前业务步骤并推进后续处理
            task = _generation_tasks.get(generation_id)  # 更新当前逻辑中的 task

        if not task:  # 根据当前条件决定是否进入对应业务分支
            return False  # 返回当前分支整理好的结果

        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            response = requests.post(  # 保存当前分支生成的响应对象
                f"{settings.dify_base_url.rstrip('/')}/chat-messages/{task['task_id']}/stop",  # 设置 post 的 字段
                headers={"Authorization": f"Bearer {task['api_key']}", "Content-Type": "application/json"},  # 设置 post 的 Authorization
                json={"user": task["user_id"]},  # 设置 post 的 user
                timeout=10,  # 设置 post 的 timeout
            )  # 结束 post 的定义或组装
            if response.status_code >= 400:  # 根据状态参数决定是否追加筛选条件
                logger.warning("Dify stop request failed. status=%s body=%s", response.status_code, response.text[:500])  # 记录外部服务异常或降级信息，便于排查问题
                return False  # 返回当前分支整理好的结果
            return True  # 返回当前分支整理好的结果
        except requests.RequestException as exc:  # 捕获异常并执行降级或错误处理逻辑
            logger.warning("Dify stop request failed. generation_id=%s error=%s", generation_id, exc)  # 记录外部服务异常或降级信息，便于排查问题
            return False  # 返回当前分支整理好的结果
        finally:  # 无论成功失败都执行资源释放或收尾逻辑
            cls._unregister_generation(generation_id)  # 执行当前业务步骤并推进后续处理

    def _upload_file_to_dify(  # 定义业务处理函数 _upload_file_to_dify
        self,  # 声明参数 self，供当前逻辑使用
        api_key: str,  # 声明参数 api_key，供当前逻辑使用
        user_id: Optional[str],  # 接收当前提问用户的标识信息
        attachment: ChatAttachment,  # 接收上传给外部问答服务的附件对象
    ) -> Optional[str]:  # 结束 _upload_file_to_dify 的参数声明
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            if hasattr(attachment.file, "seek"):  # 附件模式下切换到文件问答处理分支
                attachment.file.seek(0)  # 执行当前业务步骤并推进后续处理
            response = requests.post(  # 保存当前分支生成的响应对象
                f"{settings.dify_base_url.rstrip('/')}/files/upload",  # 设置 post 的 字段
                headers={"Authorization": f"Bearer {api_key}"},  # 设置 post 的 Authorization
                data={"user": user_id or "anonymous"},  # 设置 post 的 user
                files={  # 设置 post 的 files
                    "file": (  # 填充返回或配置中的 file 字段
                        attachment.filename,  # 填充返回或配置中的 字段 字段
                        attachment.file,  # 填充返回或配置中的 字段 字段
                        attachment.content_type or "application/octet-stream",  # 填充返回或配置中的 字段 字段
                    )  # 填充返回或配置中的 字段 字段
                },  # 结束 files 的定义或组装
                timeout=settings.dify_timeout_seconds,  # 设置 post 的 timeout
            )  # 结束 post 的定义或组装
            if response.status_code not in (200, 201):  # 根据状态参数决定是否追加筛选条件
                logger.warning(  # 记录外部服务异常或降级信息，便于排查问题
                    "Dify file upload returned non-success status. status=%s body=%s",  # 执行当前业务步骤并推进后续处理
                    response.status_code,  # 执行当前业务步骤并推进后续处理
                    response.text[:1000],  # 执行当前业务步骤并推进后续处理
                )  # 执行当前业务步骤并推进后续处理
                return None  # 返回当前分支整理好的结果
            data = response.json()  # 整理当前接口最终要返回的数据结构
            return data.get("id")  # 返回当前分支整理好的结果
        except requests.Timeout as exc:  # 捕获异常并执行降级或错误处理逻辑
            logger.warning(  # 记录外部服务异常或降级信息，便于排查问题
                "Dify file upload timed out after %ss. filename=%s error=%s",  # 执行当前业务步骤并推进后续处理
                settings.dify_timeout_seconds,  # 执行当前业务步骤并推进后续处理
                attachment.filename,  # 执行当前业务步骤并推进后续处理
                exc,  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
            return None  # 返回当前分支整理好的结果
        except requests.RequestException as exc:  # 捕获异常并执行降级或错误处理逻辑
            logger.warning("Dify file upload failed. filename=%s error=%s", attachment.filename, exc)  # 记录外部服务异常或降级信息，便于排查问题
            return None  # 返回当前分支整理好的结果

    def _dify_file_type(self, filename: str, content_type: str) -> str:  # 定义业务处理函数 _dify_file_type
        content_type = (content_type or "").lower()  # 更新当前逻辑中的 content type
        suffix = Path(filename or "").suffix.lower().lstrip(".")  # 提取上传文件扩展名，校验导入格式是否允许
        if content_type.startswith("image/"):  # 根据当前条件决定是否进入对应业务分支
            return "image"  # 返回当前分支整理好的结果
        if content_type.startswith("audio/"):  # 根据当前条件决定是否进入对应业务分支
            return "audio"  # 返回当前分支整理好的结果
        if content_type.startswith("video/"):  # 根据当前条件决定是否进入对应业务分支
            return "video"  # 返回当前分支整理好的结果
        if suffix in {"pdf", "txt", "md", "markdown", "html", "htm", "csv", "doc", "docx", "xls", "xlsx", "ppt", "pptx"}:  # 根据当前条件决定是否进入对应业务分支
            return "document"  # 返回当前分支整理好的结果
        return "custom"  # 返回当前分支整理好的结果

    def _answer_from_faq(self, question: str, language: str) -> ChatResponse:  # 定义本地 FAQ 回退回答逻辑
        faq = self._best_faq_match(question, language)  # 更新当前逻辑中的 faq
        if faq:  # 根据当前条件决定是否进入对应业务分支
            faq_obj = cast(Any, faq)  # 更新当前逻辑中的 faq obj
            answer = self._normalize_answer(str(faq_obj.answer or ""))  # 更新当前逻辑中的 回答内容
            source_ids = faq_obj.source_ids if isinstance(faq_obj.source_ids, list) else []  # 更新当前逻辑中的 source ids
            source_infos = self._source_infos(source_ids)  # 更新当前逻辑中的 source infos
            return ChatResponse(  # 返回当前分支整理好的结果
                answer=answer,  # 设置 ChatResponse 的 回答内容
                sources=source_infos or None,  # 设置 ChatResponse 的 来源列表
                related_tasks=self._extract_tasks(question),  # 设置 ChatResponse 的 关联任务列表
                response_time=0,  # 设置 ChatResponse 的 响应耗时
                provider="local_faq",  # 设置 ChatResponse 的 服务提供方
                risk_level=str(faq_obj.risk_level or "medium"),  # 设置 ChatResponse 的 风险等级
                suggestions=self._suggestions(question),  # 设置 ChatResponse 的 建议列表
                disclaimer=DISCLAIMER,  # 设置 ChatResponse 的 免责声明
            )  # 结束 ChatResponse 的定义或组装

        return ChatResponse(  # 返回当前分支整理好的结果
            answer=self._fallback_answer(question),  # 设置 ChatResponse 的 回答内容
            sources=self._source_infos([]) or None,  # 设置 ChatResponse 的 来源列表
            related_tasks=self._extract_tasks(question),  # 设置 ChatResponse 的 关联任务列表
            response_time=0,  # 设置 ChatResponse 的 响应耗时
            provider="local_faq",  # 设置 ChatResponse 的 服务提供方
            risk_level=self._estimate_risk(question),  # 设置 ChatResponse 的 风险等级
            suggestions=self._suggestions(question),  # 设置 ChatResponse 的 建议列表
            disclaimer=DISCLAIMER,  # 设置 ChatResponse 的 免责声明
        )  # 结束 ChatResponse 的定义或组装

    def _best_faq_match(self, question: str, language: str) -> Optional[FAQ]:  # 定义业务处理函数 _best_faq_match
        keyword = f"%{question[:80]}%"  # 更新当前逻辑中的 keyword
        candidates = (  # 更新当前逻辑中的 candidates
            self.db.query(FAQ)  # 执行当前业务步骤并推进后续处理
            .filter(FAQ.tenant_id == self.tenant.id)  # 执行当前业务步骤并推进后续处理
            .filter(or_(FAQ.language == language, FAQ.language == "zh-CN"))  # 执行当前业务步骤并推进后续处理
            .filter(or_(FAQ.question.like(keyword), FAQ.answer.like(keyword), FAQ.category.like(keyword)))  # 执行当前业务步骤并推进后续处理
            .limit(20)  # 执行当前业务步骤并推进后续处理
            .all()  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理

        if not candidates:  # 根据当前条件决定是否进入对应业务分支
            candidates = self.db.query(FAQ).filter(FAQ.tenant_id == self.tenant.id).all()  # 更新当前逻辑中的 candidates

        best_score = 0.0  # 更新当前逻辑中的 best score
        best = None  # 更新当前逻辑中的 best
        normalized_question = question.lower()  # 更新当前逻辑中的 normalized question
        for faq_item in candidates:  # 遍历当前集合中的每一项并逐个处理
            faq = cast(Any, faq_item)  # 更新当前逻辑中的 faq
            terms = [faq.question, *(faq.aliases or []), *(faq.keywords or [])]  # 更新当前逻辑中的 terms
            score = max(SequenceMatcher(None, normalized_question, term.lower()).ratio() for term in terms if term)  # 更新当前逻辑中的 score
            if any(term and term in question for term in terms):  # 根据当前条件决定是否进入对应业务分支
                score += 0.35  # 执行当前业务步骤并推进后续处理
            if score > best_score:  # 根据当前条件决定是否进入对应业务分支
                best_score = score  # 更新当前逻辑中的 best score
                best = faq  # 更新当前逻辑中的 best
        return best if best_score >= 0.18 else None  # 返回当前分支整理好的结果

    def _source_infos(self, source_ids: list[int]) -> list[SourceInfo]:  # 定义检索命中到来源卡片的转换函数
        if not self._has_active_package():  # 根据当前条件决定是否进入对应业务分支
            return []  # 返回当前分支整理好的结果
        query = self.db.query(Source).filter(Source.tenant_id == self.tenant.id)  # 保存当前逐步拼装的数据库查询对象
        if source_ids:  # 根据当前条件决定是否进入对应业务分支
            query = query.filter(Source.id.in_(source_ids))  # 保存当前逐步拼装的数据库查询对象
        else:  # 处理其他未命中的业务情况
            query = query.order_by(Source.created_at.desc()).limit(3)  # 按排序和分页参数查询当前页数据
        sources = query.all()  # 更新当前逻辑中的 来源列表
        result = []  # 更新当前逻辑中的 result
        for item in sources:  # 遍历当前集合中的每一项并逐个处理
            source = cast(Any, item)  # 更新当前逻辑中的 source
            result.append(  # 执行当前业务步骤并推进后续处理
                SourceInfo(  # 执行当前业务步骤并推进后续处理
                    title=str(source.title or ""),  # 更新当前逻辑中的 标题
                    url=str(source.url) if source.url else None,  # 更新当前逻辑中的 链接地址
                    snippet=str(source.description) if source.description else None,  # 更新当前逻辑中的 snippet
                )  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
        return result  # 返回当前分支整理好的结果

    def _extract_tasks(self, question: str) -> list[TaskInfo]:  # 定义业务处理函数 _extract_tasks
        if not any(word in question for word in ["仲裁", "办理", "申请", "共济", "医保"]):  # 根据当前条件决定是否进入对应业务分支
            return []  # 返回当前分支整理好的结果
        return [  # 返回当前分支整理好的结果
            TaskInfo(  # 补充列表中的 TaskInfo( 项
                title="合规办理建议路径",  # 补充列表中的 标题 项
                steps=[  # 补充列表中的 steps 项
                    "确认适用地区、员工身份、时间节点和企业制度版本。",  # 补充列表中的 确认适用地区、员工身份、时间节点和企业制度版本。 项
                    "准备劳动合同、考勤、工资、社保缴费或医保参保等证据材料。",  # 补充列表中的 准备劳动合同、考勤、工资、社保缴费或医保参保等证据材料。 项
                    "通过当地人社、医保、税务等官方渠道核验最新办理入口。",  # 补充列表中的 通过当地人社、医保、税务等官方渠道核验最新办理入口。 项
                    "对高风险事项保留书面处理记录，必要时交由 HR/法务复核。",  # 补充列表中的 对高风险事项保留书面处理记录，必要时交由 HR/法务复核。 项
                ],  # 结束 steps 的定义或组装
                url=settings.ragflow_web_url,  # 补充列表中的 链接地址 项
            )  # 补充列表中的 ) 项
        ]  # 结束 返回结果 的定义或组装

    def _normalize_answer(self, answer: str) -> str:  # 定义业务处理函数 _normalize_answer
        answer = sanitize_text(answer) or ""  # 清洗并规范化 回答内容 的输入值
        if DISCLAIMER not in answer:  # 根据当前条件决定是否进入对应业务分支
            answer = f"{answer.strip()}\n\n风险提示：{DISCLAIMER}"  # 更新当前逻辑中的 回答内容
        return answer  # 返回当前分支整理好的结果

    def _with_context_prefix(self, answer: str, user_role: str, province: str, city: str) -> str:  # 定义业务处理函数 _with_context_prefix
        role = USER_ROLE_LABELS.get(user_role, user_role or "员工")  # 更新当前逻辑中的 role
        region = f"{province}{city}" if province and city else (province or city or self.tenant.region)  # 组合省市信息，作为外部问答服务的地域上下文
        return f"适用角色：{role}\n所在地区：{region}\n\n{answer}"  # 返回当前分支整理好的结果

    def _has_active_package(self) -> bool:  # 定义业务处理函数 _has_active_package
        return (  # 返回当前分支整理好的结果
            self.db.query(KnowledgePackage.id)  # 设置 return 的 字段
            .filter(KnowledgePackage.tenant_id == self.tenant.id, KnowledgePackage.status == "active")  # 设置 return 的 字段
            .first()  # 设置 return 的 字段
            is not None  # 设置 return 的 字段
        )  # 结束 return 的定义或组装

    def _inactive_package_answer(self, question: str) -> str:  # 定义业务处理函数 _inactive_package_answer
        risk = self._estimate_risk(question)  # 更新当前逻辑中的 risk
        return (  # 返回当前分支整理好的结果
            "当前租户的知识包已停用，系统不会调用知识库文件或外部知识包检索。\n"  # 设置 return 的 字段
            "请先在管理后台启用知识包，或由管理员确认当前资料可用后再进行智能问答。\n"  # 设置 return 的 字段
            f"本次问题仅做通用风险识别，初步风险等级为：{risk}。\n\n"  # 设置 return 的 字段
            f"风险提示：{DISCLAIMER}"  # 设置 return 的 字段
        )  # 结束 return 的定义或组装

    def _fallback_answer(self, question: str) -> str:  # 定义业务处理函数 _fallback_answer
        risk = self._estimate_risk(question)  # 更新当前逻辑中的 risk
        return (  # 返回当前分支整理好的结果
            "当前问题未命中已复核 FAQ，系统已按通用合规口径给出处理建议：\n"  # 设置 return 的 字段
            "1. 先确认适用地区、时间口径、员工身份、合同和企业制度版本。\n"  # 设置 return 的 字段
            "2. 涉及工资、社保、医保、假期、仲裁等事项时，应引用官方政策或经办规则，避免只凭经验答复。\n"  # 设置 return 的 字段
            "3. 对包含身份证号、手机号、银行卡号等个人信息的材料，应先脱敏再进入知识库或日志。\n"  # 设置 return 的 字段
            f"4. 本问题初步风险等级为：{risk}。建议由 HR 或法务复核后再对外确认。"  # 设置 return 的 字段
        )  # 结束 return 的定义或组装

    def _estimate_risk(self, question: str) -> str:  # 定义业务处理函数 _estimate_risk
        high_words = ["仲裁", "工伤", "解除", "赔偿", "最低工资", "未签", "违法", "身份证", "手机号"]  # 更新当前逻辑中的 high words
        medium_words = ["社保", "医保", "产假", "护理假", "加班", "离职", "补缴"]  # 更新当前逻辑中的 medium words
        if any(word in question for word in high_words):  # 根据当前条件决定是否进入对应业务分支
            return "high"  # 返回当前分支整理好的结果
        if any(word in question for word in medium_words):  # 根据当前条件决定是否进入对应业务分支
            return "medium"  # 返回当前分支整理好的结果
        return "low"  # 返回当前分支整理好的结果

    def _risk_from_answer(self, answer: str) -> Optional[str]:  # 定义业务处理函数 _risk_from_answer
        text = sanitize_text(answer) or ""  # 清洗并规范化 text 的输入值
        patterns = [  # 更新当前逻辑中的 patterns
            r"风险等级\s*[:：]\s*(?:\*\*)?\s*(高风险|中风险|低风险|高|中|低|high|medium|low)",  # 补充列表中的 r"风险等级\s*[ 项
            r"初步风险等级\s*为\s*[:：]?\s*(?:\*\*)?\s*(高风险|中风险|低风险|高|中|低|high|medium|low)",  # 补充列表中的 r"初步风险等级\s*为\s*[ 项
        ]  # 结束 patterns 的定义或组装
        for pattern in patterns:  # 遍历当前集合中的每一项并逐个处理
            match = re.search(pattern, text, flags=re.IGNORECASE)  # 更新当前逻辑中的 match
            if match:  # 根据当前条件决定是否进入对应业务分支
                return self._normalize_risk_level(match.group(1))  # 返回当前分支整理好的结果
        return None  # 返回当前分支整理好的结果

    def _normalize_risk_level(self, value: str) -> Optional[str]:  # 定义业务处理函数 _normalize_risk_level
        normalized = (sanitize_text(value) or "").strip().lower().strip("*：:，,。.;；")  # 初始化当前导出行的标准化结果字典
        mapping = {  # 更新当前逻辑中的 mapping
            "高": "high",  # 填充返回或配置中的 高 字段
            "高风险": "high",  # 填充返回或配置中的 高风险 字段
            "high": "high",  # 填充返回或配置中的 high 字段
            "中": "medium",  # 填充返回或配置中的 中 字段
            "中风险": "medium",  # 填充返回或配置中的 中风险 字段
            "中等": "medium",  # 填充返回或配置中的 中等 字段
            "中等风险": "medium",  # 填充返回或配置中的 中等风险 字段
            "medium": "medium",  # 填充返回或配置中的 medium 字段
            "低": "low",  # 填充返回或配置中的 低 字段
            "低风险": "low",  # 填充返回或配置中的 低风险 字段
            "low": "low",  # 填充返回或配置中的 low 字段
        }  # 结束 mapping 的定义或组装
        return mapping.get(normalized)  # 返回当前分支整理好的结果

    def _suggestions(self, question: str) -> list[str]:  # 定义业务处理函数 _suggestions
        if "产假" in question or "护理假" in question:  # 根据当前条件决定是否进入对应业务分支
            return ["陕西护理假多少天？", "生育津贴和产假工资如何衔接？", "企业制度低于地方假期规定怎么办？"]  # 返回当前分支整理好的结果
        if "仲裁" in question:  # 根据当前条件决定是否进入对应业务分支
            return ["劳动仲裁时效是多久？", "仲裁申请需要哪些材料？", "员工所在地和公司所在地哪个有管辖权？"]  # 返回当前分支整理好的结果
        if "社保" in question or "医保" in question:  # 根据当前条件决定是否进入对应业务分支
            return ["新员工入职后多久要办理社保？", "居民医保断缴后还能报销吗？", "社保补缴有什么风险？"]  # 返回当前分支整理好的结果
        return ["试用期工资可以低于最低工资吗？", "劳动合同最晚什么时候签？", "周末加班工资怎么算？"]  # 返回当前分支整理好的结果


def check_external_services() -> dict:  # 定义业务处理函数 check_external_services
    """探测本机 Dify 与 RAGFlow 服务状态。"""  # 函数文档字符串，说明 check_external_services 的职责
    services = {  # 更新当前逻辑中的 services
        "dify": {"name": "Dify", "url": settings.dify_base_url, "configured": bool(settings.dify_api_key)},  # 填充返回或配置中的 dify 字段
        "ragflow": {"name": "RAGFlow", "url": settings.ragflow_web_url, "configured": bool(settings.ragflow_api_key)},  # 填充返回或配置中的 ragflow 字段
    }  # 结束 services 的定义或组装
    for key, item in services.items():  # 遍历当前集合中的每一项并逐个处理
        probe_url = item["url"]  # 更新当前逻辑中的 probe url
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            response = requests.get(probe_url, timeout=3)  # 保存当前分支生成的响应对象
            item["online"] = response.status_code < 500  # 执行当前业务步骤并推进后续处理
            item["status_code"] = response.status_code  # 执行当前业务步骤并推进后续处理
        except requests.RequestException:  # 捕获异常并执行降级或错误处理逻辑
            item["online"] = False  # 执行当前业务步骤并推进后续处理
            item["status_code"] = None  # 执行当前业务步骤并推进后续处理
    return services  # 返回当前分支整理好的结果
