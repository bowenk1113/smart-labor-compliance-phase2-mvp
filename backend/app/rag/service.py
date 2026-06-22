"""二期 RAG 问答服务。

本文件对应流程图中的 QAService。它只负责：
1. validate_source() 这类 API 入参校验；
2. 调用 rag.stream_query()；
3. 把 PipelineResult 转换为原项目前端兼容的 ChatResponse。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import time  # 导入时间工具，统计耗时或生成时间戳
from typing import Any  # 导入当前模块运行所依赖的工具或类型

from app.rag.pipeline import DISCLAIMER, RAGPipeline  # 导入二期 RAG 检索与问答服务组件
from app.rag.scenarios import get_scenario, scenario_payloads  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import RetrievalHit, search_faq  # 导入二期 RAG 检索与问答服务组件
from app.schemas.chat import ChatResponse, SourceInfo, TaskInfo  # 导入接口请求体与响应体模型


class Phase2RAGService:  # 定义二期 RAG 问答流程的服务层适配器
    # This class is the service-layer adapter between the original project API contract
    # and the new phase-2 RAG pipeline.
    """原 Dify 项目的二期 RAG 服务入口，对应流程图 QAService。"""  # 类文档字符串，概述 Phase2RAGService 的用途

    def __init__(self) -> None:  # 定义业务处理函数 __init__
        """初始化 Pipeline 实例。"""  # 函数文档字符串，说明 __init__ 的职责

        # RAGPipeline 负责真正的 RAG 链路编排。
        self.rag = RAGPipeline()  # 初始化底层 RAG 流程编排器

    def answer(  # 定义统一问答执行入口
        self,  # 声明参数 self，供当前逻辑使用
        *,  # 以下参数改为关键字传参，避免调用位置出错
        question: str,  # 接收用户本次提交的问题内容
        scenario_id: str | None,  # 接收前端选择的问答场景标识
        session_id: str | None = None,  # 接收前端会话标识，便于串联上下文
        history: list[str] | None = None,  # 声明参数 history，供当前逻辑使用
        user_role: str = "employee",  # 接收提问人角色，用于控制回答口径
        province: str = "陕西省",  # 接收用户所在省份，用于补充地域政策上下文
        city: str = "西安市",  # 接收用户所在城市，用于补充地域政策上下文
    ) -> ChatResponse:  # 结束 answer 的参数声明
        # This is the main service entry called by the chat router.
        # It keeps the old frontend response shape while delegating the actual decision flow to RAGPipeline.
        """生成一次 RAG 答案，对应 QAService.stream_query()。"""  # 类文档字符串，概述 Phase2RAGService 的用途

        # 记录开始时间，用于原前端展示 response_time。
        # Measure end-to-end latency for one answer request so the frontend can show response_time.
        started = time.perf_counter()  # 更新当前逻辑中的 started
        # validate_source() 在 MVP 中用于规范 scenario_id；未知场景回退默认场景。
        normalized_scenario_id = self.validate_source(scenario_id)  # 更新当前逻辑中的 normalized scenario id
        # Pipeline 入口名与流程图 rag.stream_query() 对齐。
        # Delegate the actual route / FAQ / RAG decision to the phase-2 pipeline.
        result = self.rag.stream_query(  # 更新当前逻辑中的 result
            query=question,  # 设置 stream_query 的 query
            scenario_id=normalized_scenario_id,  # 设置 stream_query 的 scenario id
            session_id=session_id,  # 设置 stream_query 的 会话 ID
            history=history,  # 设置 stream_query 的 历史上下文
            user_role=user_role,  # 设置 stream_query 的 用户角色
            province=province,  # 设置 stream_query 的 省份
            city=city,  # 设置 stream_query 的 城市
        )  # 结束 stream_query 的定义或组装
        # 将 PipelineResult 转换成原项目 ChatResponse，保证前端不用改调用协议。
        return self._response(  # 返回当前分支整理好的结果
            answer=result.answer,  # 设置 self._response 的 回答内容
            route=result.route,  # 设置 self._response 的 route
            provider=result.provider,  # 设置 self._response 的 服务提供方
            answer_source=result.answer_source,  # 设置 self._response 的 answer source
            started=started,  # 设置 self._response 的 started
            sources=self._source_infos(result.context_hits),  # 设置 self._response 的 来源列表
            related_tasks=self._task_infos(result.related_tasks),  # 设置 self._response 的 关联任务列表
            risk_level=result.risk_level,  # 设置 self._response 的 风险等级
            retrieval=result.retrieval,  # 设置 self._response 的 retrieval
        )  # 结束 self._response 的定义或组装

    def validate_source(self, scenario_id: str | None) -> str:  # 定义场景参数规范化函数
        # Normalize and validate the selected scene id so downstream modules always receive a legal value.
        """对应流程图 validate_source()：校验并规范前端传入的场景。"""  # 函数文档字符串，说明 validate_source 的职责

        # get_scenario 已经内置默认场景兜底，这里返回规范后的场景 ID。
        return get_scenario(scenario_id).scenario_id  # 返回当前分支整理好的结果

    def recommended_questions(self, scenario_id: str | None) -> list[dict[str, Any]]:  # 定义场景推荐问题查询函数
        # This helper powers the frontend's scene-level question suggestions using FAQ retrieval.
        """从 FAQ 向量库返回推荐问题。"""  # 函数文档字符串，说明 recommended_questions 的职责

        # Use the current scene label as a lightweight query to fetch scene-relevant FAQ suggestions.
        scenario = get_scenario(scenario_id)  # 更新当前逻辑中的 scenario
        hits, _ = search_faq(scenario, [scenario.label], top_k=8)  # 执行当前业务步骤并推进后续处理
        return [  # 返回当前分支整理好的结果
            {  # 补充列表中的 { 项
                "id": hit.document.metadata.get("id"),  # 补充列表中的 主键 ID 项
                "question": hit.document.metadata.get("title"),  # 补充列表中的 问题内容 项
                "category": hit.document.metadata.get("category") or scenario.label,  # 补充列表中的 分类 项
                "risk_level": "medium",  # 补充列表中的 风险等级 项
            }  # 补充列表中的 } 项
            for hit in hits  # 补充列表中的 for hit in hits 项
        ]  # 结束 返回结果 的定义或组装

    @staticmethod  # 为后续函数或类声明附加装饰器配置
    def scenarios() -> list[dict[str, str]]:  # 定义前端场景列表返回函数
        """返回前端场景列表。"""  # 函数文档字符串，说明 scenarios 的职责

        return scenario_payloads()  # 返回当前分支整理好的结果

    def _source_infos(self, hits: list[RetrievalHit]) -> list[SourceInfo]:  # 定义检索命中到来源卡片的转换函数
        """把检索命中转换为原项目来源结构。"""  # 函数文档字符串，说明 _source_infos 的职责

        # Convert retrieval hits into the frontend source card structure.
        sources: list[SourceInfo] = []  # 更新当前逻辑中的 来源列表
        for hit in hits[:5]:  # 遍历当前集合中的每一项并逐个处理
            metadata = hit.document.metadata  # 更新当前逻辑中的 metadata
            title = str(metadata.get("title") or metadata.get("file_name") or metadata.get("source_label") or "知识库来源")  # 更新当前逻辑中的 标题
            url = str(metadata.get("url") or "") or None  # 更新当前逻辑中的 链接地址
            # Keep only a short preview so the UI can show "why this source was used" without flooding the page.
            snippet = hit.document.content[:220]  # 更新当前逻辑中的 snippet
            sources.append(SourceInfo(title=title, url=url, snippet=f"score={hit.score:.3f}；{snippet}"))  # 把当前来源信息追加到结果来源列表
        return sources  # 返回当前分支整理好的结果

    def _task_infos(self, items: list[dict[str, Any]]) -> list[TaskInfo]:  # 定义任务信息转换函数
        """把 Pipeline 的任务字典转换为 TaskInfo。"""  # 函数文档字符串，说明 _task_infos 的职责

        return [TaskInfo(**item) for item in items]  # 返回当前分支整理好的结果

    def _response(  # 定义 ChatResponse 兼容结构组装函数
        self,  # 声明参数 self，供当前逻辑使用
        *,  # 以下参数改为关键字传参，避免调用位置出错
        answer: str,  # 声明参数 answer，供当前逻辑使用
        route: str,  # 声明参数 route，供当前逻辑使用
        provider: str,  # 接收问答服务提供方筛选参数
        answer_source: str,  # 声明参数 answer_source，供当前逻辑使用
        started: float,  # 声明参数 started，供当前逻辑使用
        sources: list[SourceInfo] | None = None,  # 声明参数 sources，供当前逻辑使用
        related_tasks: list[TaskInfo] | None = None,  # 声明参数 related_tasks，供当前逻辑使用
        risk_level: str = "medium",  # 声明参数 risk_level，供当前逻辑使用
        retrieval: dict[str, Any] | None = None,  # 声明参数 retrieval，供当前逻辑使用
    ) -> ChatResponse:  # 结束 _response 的参数声明
        # This method converts the new pipeline result back into the response structure
        # already expected by the existing Vue frontend.
        """构造兼容原前端的 ChatResponse。"""  # 类文档字符串，概述 Phase2RAGService 的用途

        # Normalize the pipeline result into the legacy ChatResponse contract expected by the Vue frontend.
        return ChatResponse(  # 返回当前分支整理好的结果
            answer=answer,  # 设置 ChatResponse 的 回答内容
            sources=sources or [],  # 设置 ChatResponse 的 来源列表
            related_tasks=related_tasks or [],  # 设置 ChatResponse 的 关联任务列表
            response_time=int((time.perf_counter() - started) * 1000),  # 设置 ChatResponse 的 响应耗时
            provider=provider,  # 设置 ChatResponse 的 服务提供方
            answer_source=answer_source,  # 设置 ChatResponse 的 answer source
            risk_level=risk_level,  # 设置 ChatResponse 的 风险等级
            suggestions=[],  # 设置 ChatResponse 的 建议列表
            disclaimer=DISCLAIMER,  # 设置 ChatResponse 的 免责声明
            route=route,  # 设置 ChatResponse 的 route
            retrieval=retrieval or {},  # 设置 ChatResponse 的 retrieval
        )  # 结束 ChatResponse 的定义或组装
