"""核心 RAG Pipeline。

本模块严格按照《核心RAG链路流程.drawio》组织代码：
1 用户问题 -> 2 QAService -> 3 Pipeline 入口 -> 4 请求上下文 -> 5 查询路由
-> 6 检索准备 -> 8 FAQ 检索 -> 9 FAQ 高置信判断 -> 10 文档检索
-> 11 上下文筛选 -> 12 Prompt/答案生成 -> 15 写历史 -> finish/error。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

from typing import Any  # 导入当前模块运行所依赖的工具或类型

from app.rag.context import create_query_context  # 导入二期 RAG 检索与问答服务组件
from app.rag.generator import GenerationResult, build_rag_prompt, generate_with_model, template_answer  # 导入二期 RAG 检索与问答服务组件
from app.rag.history import add_turn  # 导入二期 RAG 检索与问答服务组件
from app.rag.pipeline_schema import RAGEvent, RAGPipelineResult, RetrievalHit  # 导入二期 RAG 检索与问答服务组件
from app.rag.retrieval import (  # 导入二期 RAG 检索与问答服务组件
    build_context,  # 执行当前业务步骤并推进后续处理
    faq_direct_answer,  # 执行当前业务步骤并推进后续处理
    prepare_retrieval,  # 执行当前业务步骤并推进后续处理
    resolve_active_kb_version,  # 执行当前业务步骤并推进后续处理
    retrieval_diagnostics,  # 执行当前业务步骤并推进后续处理
    search_doc,  # 执行当前业务步骤并推进后续处理
    search_faq,  # 执行当前业务步骤并推进后续处理
    select_context_docs,  # 执行当前业务步骤并推进后续处理
)  # 执行当前业务步骤并推进后续处理
from app.rag.routing import decide_route  # 导入二期 RAG 检索与问答服务组件


class RAGPipeline:  # 定义业务类 RAGPipeline
    # This class is the top-level coordinator of the phase-2 RAG MVP.
    # Reading this file from top to bottom is the easiest way to understand the full answer chain.
    """可测试、可追踪的二期 RAG 主链路。"""  # 类文档字符串，概述 RAGPipeline 的用途

    def stream_query(  # 定义业务处理函数 stream_query
        self,  # 声明参数 self，供当前逻辑使用
        *,  # 以下参数改为关键字传参，避免调用位置出错
        query: str,  # 声明参数 query，供当前逻辑使用
        scenario_id: str | None,  # 接收前端选择的问答场景标识
        session_id: str | None = None,  # 接收前端会话标识，便于串联上下文
        history: list[str] | None = None,  # 声明参数 history，供当前逻辑使用
        user_role: str = "employee",  # 接收提问人角色，用于控制回答口径
        province: str = "陕西省",  # 接收用户所在省份，用于补充地域政策上下文
        city: str = "西安市",  # 接收用户所在城市，用于补充地域政策上下文
    ) -> RAGPipelineResult:  # 结束 stream_query 的参数声明
        """流程图 3 Pipeline 入口：同步返回 MVP 答案。"""  # 类文档字符串，概述 RAGPipeline 的用途

        # MVP 当前仍是同步 HTTP 返回；函数名保留 stream_query，便于后续升级 SSE 流式事件。
        events: list[RAGEvent] = [self.start_event(query=query, scenario_id=scenario_id)]  # 更新当前逻辑中的 events
        # Main closed-loop flow:
        # 1) build context
        # 2) run router direct-answer checks
        # 3) run FAQ retrieval and FAQ direct-answer checks
        # 4) run document retrieval
        # 5) build prompt
        # 6) call LLM or fallback template
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            # 4 请求上下文：把 API 入参变成统一 RAGQueryContext。
            context = create_query_context(  # 更新当前逻辑中的 context
                query=query,  # 设置 create_query_context 的 query
                scenario_id=scenario_id,  # 设置 create_query_context 的 scenario id
                session_id=session_id,  # 设置 create_query_context 的 会话 ID
                history=history,  # 设置 create_query_context 的 历史上下文
                user_role=user_role,  # 设置 create_query_context 的 用户角色
                province=province,  # 设置 create_query_context 的 省份
                city=city,  # 设置 create_query_context 的 城市
            )  # 结束 create_query_context 的定义或组装
            # Convert loose request fields into one normalized context object.
            # All later stages share this object to avoid parameter drift across modules.
            events.append(RAGEvent("create_query_context", {"scenario_id": context.scenario.scenario_id}))  # 执行当前业务步骤并推进后续处理
            # 5 查询路由：先处理固定直出、拒答和场景边界。
            route = decide_route(context)  # 更新当前逻辑中的 route
            # Use cheap rule-based routing first so greetings, illegal requests, and scene-boundary problems
            # can exit early without touching vectors or the LLM.
            events.append(RAGEvent("decide_route", {"route": route.route, "inferred_scenario_id": route.inferred_scenario_id}))  # 执行当前业务步骤并推进后续处理
            if route.answer:  # 根据当前条件决定是否进入对应业务分支
                # A router answer means we intentionally short-circuit the expensive RAG pipeline.
                answer_source = self._answer_source_for_route(route.route)  # 更新当前逻辑中的 answer source
                result = self._finish_with_single_answer(  # 更新当前逻辑中的 result
                    context=context,  # 设置 _finish_with_single_answer 的 context
                    answer=route.answer,  # 设置 _finish_with_single_answer 的 回答内容
                    route=route.route,  # 设置 _finish_with_single_answer 的 route
                    provider=route.provider,  # 设置 _finish_with_single_answer 的 服务提供方
                    answer_source=answer_source,  # 设置 _finish_with_single_answer 的 answer source
                    risk_level=route.risk_level,  # 设置 _finish_with_single_answer 的 风险等级
                    events=events,  # 设置 _finish_with_single_answer 的 events
                )  # 结束 _finish_with_single_answer 的定义或组装
                return result  # 返回当前分支整理好的结果
            # 18 Active 版本：解析当前知识库版本。
            kb_version = resolve_active_kb_version()  # 更新当前逻辑中的 kb version
            # Record which knowledge-base version is currently active for traceability and troubleshooting.
            events.append(RAGEvent("resolve_active_kb_version", {"kb_version": kb_version}))  # 执行当前业务步骤并推进后续处理
            # 6/7 检索准备：生成改写、变体、意图、计划和画像。
            preparation = prepare_retrieval(context)  # 更新当前逻辑中的 preparation
            # Build the retrieval preparation package.
            # This is where query rewrite, variants, intent inference, and dynamic plan selection happen.
            events.append(  # 执行当前业务步骤并推进后续处理
                RAGEvent(  # 执行当前业务步骤并推进后续处理
                    "prepare_retrieval",  # 执行当前业务步骤并推进后续处理
                    {  # 执行当前业务步骤并推进后续处理
                        "intent": preparation.intent,  # 执行当前业务步骤并推进后续处理
                        "variants": preparation.query_variants,  # 执行当前业务步骤并推进后续处理
                        "profile": preparation.profile,  # 执行当前业务步骤并推进后续处理
                    },  # 执行当前业务步骤并推进后续处理
                )  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
            # 8 FAQ 检索：先查高频问答向量库。
            faq_hits, faq_elapsed_ms = search_faq(context, preparation)  # 执行当前业务步骤并推进后续处理
            # FAQ vectors are searched before document vectors because high-frequency standard questions
            # can often be answered directly and cheaply.
            events.append(RAGEvent("search_faq", {"hits": len(faq_hits), "elapsed_ms": round(faq_elapsed_ms, 2)}))  # 执行当前业务步骤并推进后续处理
            # 9 FAQ 高置信：命中标准答案时不再查文档、不调用 LLM。
            faq_answer = faq_direct_answer(context.query, faq_hits, preparation.plan.faq_direct_threshold)  # 更新当前逻辑中的 faq answer
            if faq_answer:  # 根据当前条件决定是否进入对应业务分支
                # FAQ direct-answer is intentionally conservative.
                # It only returns when the vector match is both strong and stable.
                retrieval = retrieval_diagnostics(  # 更新当前逻辑中的 retrieval
                    context=context,  # 设置 retrieval_diagnostics 的 context
                    preparation=preparation,  # 设置 retrieval_diagnostics 的 preparation
                    kb_version=kb_version,  # 设置 retrieval_diagnostics 的 kb version
                    faq_hits=faq_hits,  # 设置 retrieval_diagnostics 的 faq hits
                    doc_hits=[],  # 设置 retrieval_diagnostics 的 doc hits
                    faq_elapsed_ms=faq_elapsed_ms,  # 设置 retrieval_diagnostics 的 faq elapsed ms
                    doc_elapsed_ms=0.0,  # 设置 retrieval_diagnostics 的 doc elapsed ms
                )  # 结束 retrieval_diagnostics 的定义或组装
                return self._finish_with_single_answer(  # 返回当前分支整理好的结果
                    context=context,  # 设置 self._finish_with_single_answer 的 context
                    answer=self._with_context(faq_answer, context.scenario.label, context.user_role, context.data_scope.province, context.data_scope.city),  # 设置 self._finish_with_single_answer 的 回答内容
                    route="faq_direct",  # 设置 self._finish_with_single_answer 的 route
                    provider="phase2_faq_vector",  # 设置 self._finish_with_single_answer 的 服务提供方
                    answer_source="faq_direct",  # 设置 self._finish_with_single_answer 的 answer source
                    risk_level=self._estimate_risk(context.query),  # 设置 self._finish_with_single_answer 的 风险等级
                    events=events,  # 设置 self._finish_with_single_answer 的 events
                    context_hits=faq_hits[:3],  # 设置 self._finish_with_single_answer 的 context hits
                    retrieval=retrieval,  # 设置 self._finish_with_single_answer 的 retrieval
                )  # 结束 self._finish_with_single_answer 的定义或组装
            # 10 文档检索：FAQ 未高置信时进入 RAG 文档库。
            doc_hits, doc_elapsed_ms = search_doc(context, preparation)  # 执行当前业务步骤并推进后续处理
            # If FAQ is not confident enough, continue into document-level RAG retrieval.
            events.append(RAGEvent("search_doc", {"hits": len(doc_hits), "elapsed_ms": round(doc_elapsed_ms, 2)}))  # 执行当前业务步骤并推进后续处理
            # 11 上下文筛选：把 FAQ 和 Doc 命中合并、过滤、截断。
            context_hits = select_context_docs(faq_hits, doc_hits, preparation.plan)  # 更新当前逻辑中的 context hits
            # Merge FAQ evidence with document evidence and keep only the top usable context fragments.
            context_text = build_context(context_hits)  # 更新当前逻辑中的 context text
            events.append(RAGEvent("select_context_docs", {"context_docs": len(context_hits)}))  # 执行当前业务步骤并推进后续处理
            # This diagnostics object is returned to the frontend so answer provenance can be displayed clearly.
            retrieval = retrieval_diagnostics(  # 更新当前逻辑中的 retrieval
                context=context,  # 设置 retrieval_diagnostics 的 context
                preparation=preparation,  # 设置 retrieval_diagnostics 的 preparation
                kb_version=kb_version,  # 设置 retrieval_diagnostics 的 kb version
                faq_hits=faq_hits,  # 设置 retrieval_diagnostics 的 faq hits
                doc_hits=doc_hits,  # 设置 retrieval_diagnostics 的 doc hits
                faq_elapsed_ms=faq_elapsed_ms,  # 设置 retrieval_diagnostics 的 faq elapsed ms
                doc_elapsed_ms=doc_elapsed_ms,  # 设置 retrieval_diagnostics 的 doc elapsed ms
            )  # 结束 retrieval_diagnostics 的定义或组装
            # 12 Prompt 构造：把用户问题、场景、角色、地区和检索上下文拼成大模型输入。
            prompt = build_rag_prompt(context=context, context_text=context_text)  # 更新当前逻辑中的 prompt
            # Build the model prompt using retrieved evidence plus business context such as scene and region.
            events.append(RAGEvent("build_prompt", {"prompt_chars": len(prompt), "context_chars": len(context_text)}))  # 执行当前业务步骤并推进后续处理
            # 13 LLM 生成：有上下文时调用 Dify/OpenAI-compatible；无配置时返回可诊断跳过结果。
            generation = self.generate_answer(context=context, context_hits=context_hits, context_text=context_text, prompt=prompt)  # 更新当前逻辑中的 generation
            # Generation is the final stage.
            # When an LLM is configured, it rewrites retrieved evidence into a cleaner answer.
            events.append(  # 执行当前业务步骤并推进后续处理
                RAGEvent(  # 执行当前业务步骤并推进后续处理
                    "llm_generate",  # 执行当前业务步骤并推进后续处理
                    {  # 执行当前业务步骤并推进后续处理
                        "backend": generation.backend,  # 执行当前业务步骤并推进后续处理
                        "provider": generation.provider,  # 执行当前业务步骤并推进后续处理
                        "used_llm": generation.used_llm,  # 执行当前业务步骤并推进后续处理
                        "detail": generation.detail,  # 执行当前业务步骤并推进后续处理
                    },  # 执行当前业务步骤并推进后续处理
                )  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
            # 如果没有配置大模型或模型失败，使用模板兜底，保证 MVP 不会中断。
            answer_body = generation.answer or template_answer(question=context.query, scenario_label=context.scenario.label, hits=context_hits)  # 更新当前逻辑中的 answer body
            if not generation.answer:  # 根据当前条件决定是否进入对应业务分支
                # If model generation is unavailable, fall back to a template summary instead of failing the request.
                events.append(RAGEvent("template_fallback", {"reason": generation.detail.get("reason") or generation.detail.get("status")}))  # 执行当前业务步骤并推进后续处理
            # Frontend uses answer_source to show whether the answer came from direct output,
            # FAQ direct answer, hybrid retrieval plus LLM, or hybrid retrieval plus template.
            answer_source = "hybrid_retrieval_llm" if generation.used_llm else "hybrid_retrieval_template"  # 更新当前逻辑中的 answer source
            # 给答案追加场景、角色、地区和免责声明。
            answer = self._with_context(answer_body, context.scenario.label, context.user_role, context.data_scope.province, context.data_scope.city)  # 更新当前逻辑中的 回答内容
            # 把生成层诊断信息放进 retrieval，方便前端或验收查看是否真的调用模型。
            # Expose generation diagnostics in the response payload so acceptance testing can verify
            # whether the LLM layer actually ran.
            retrieval["answer_source"] = answer_source  # 执行当前业务步骤并推进后续处理
            retrieval["answer_source_label"] = answer_source_label(answer_source)  # 执行当前业务步骤并推进后续处理
            retrieval["generation"] = {  # 执行当前业务步骤并推进后续处理
                "backend": generation.backend,  # 执行当前业务步骤并推进后续处理
                "provider": generation.provider,  # 执行当前业务步骤并推进后续处理
                "used_llm": generation.used_llm,  # 执行当前业务步骤并推进后续处理
                "detail": generation.detail,  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
            # 15 写历史：Pipeline 产生日志事件，数据库写入仍由 API 层统一完成。
            # Add a history event so the whole request forms a readable execution trace.
            events.append(add_turn(context, answer, route="rag"))  # 执行当前业务步骤并推进后续处理
            events.append(RAGEvent("finish", {"route": "rag"}))  # 执行当前业务步骤并推进后续处理
            return RAGPipelineResult(  # 返回当前分支整理好的结果
                answer=answer,  # 设置 RAGPipelineResult 的 回答内容
                route="rag",  # 设置 RAGPipelineResult 的 route
                provider=generation.provider if generation.answer else "phase2_template_rag",  # 设置 RAGPipelineResult 的 服务提供方
                answer_source=answer_source,  # 设置 RAGPipelineResult 的 answer source
                risk_level=self._estimate_risk(context.query),  # 设置 RAGPipelineResult 的 风险等级
                context_hits=context_hits,  # 设置 RAGPipelineResult 的 context hits
                related_tasks=self._tasks(context.query),  # 设置 RAGPipelineResult 的 关联任务列表
                retrieval={**retrieval, "events": [event_payload(item) for item in events]},  # 设置 RAGPipelineResult 的 events
                events=events,  # 设置 RAGPipelineResult 的 events
            )  # 结束 RAGPipelineResult 的定义或组装
        except Exception as exc:  # pragma: no cover - defensive finish_error path.
            # 异常收口：保证调用方收到明确错误，而不是连接中断。
            events.append(RAGEvent("finish_error", {"error": str(exc)}))  # 执行当前业务步骤并推进后续处理
            return RAGPipelineResult(  # 返回当前分支整理好的结果
                answer="系统在执行 RAG 检索时遇到可恢复异常，请稍后重试或检查向量库、模型和知识库配置。",  # 设置 RAGPipelineResult 的 回答内容
                route="error",  # 设置 RAGPipelineResult 的 route
                provider="phase2_pipeline",  # 设置 RAGPipelineResult 的 服务提供方
                answer_source="error",  # 设置 RAGPipelineResult 的 answer source
                risk_level="medium",  # 设置 RAGPipelineResult 的 风险等级
                retrieval={"answer_source": "error", "answer_source_label": answer_source_label("error"), "events": [event_payload(item) for item in events], "error": str(exc)},  # 设置 RAGPipelineResult 的 answer source
                events=events,  # 设置 RAGPipelineResult 的 events
            )  # 结束 RAGPipelineResult 的定义或组装

    def start_event(self, *, query: str, scenario_id: str | None) -> RAGEvent:  # 定义业务处理函数 start_event
        """流程图 3 start_event()：记录请求进入 Pipeline。"""  # 函数文档字符串，说明 start_event 的职责

        return RAGEvent("start", {"query_preview": query[:80], "scenario_id": scenario_id})  # 返回当前分支整理好的结果

    def generate_answer(self, *, context, context_hits: list[RetrievalHit], context_text: str, prompt: str):  # 定义业务处理函数 generate_answer
        # The generator only runs when retrieval has produced enough evidence.
        # This keeps the system aligned with the core RAG rule: retrieve first, then generate.
        """流程图 13：调用大模型生成答案。"""  # 函数文档字符串，说明 generate_answer 的职责

        # 没有可靠上下文时不调用大模型，直接返回信息不足兜底，避免无依据生成。
        if not context_hits or not context_text:  # 根据当前条件决定是否进入对应业务分支
            return GenerationResult(  # 返回当前分支整理好的结果
                answer=template_answer(question=context.query, scenario_label=context.scenario.label, hits=[]),  # 设置 GenerationResult 的 回答内容
                provider="phase2_no_context",  # 设置 GenerationResult 的 服务提供方
                backend="none",  # 设置 GenerationResult 的 backend
                used_llm=False,  # 设置 GenerationResult 的 used llm
                detail={"status": "skipped", "reason": "no reliable context"},  # 设置 GenerationResult 的 状态
            )  # 结束 GenerationResult 的定义或组装
        # 有上下文时进入真正生成层：Dify/OpenAI-compatible/模板兜底。
        return generate_with_model(context=context, prompt=prompt)  # 返回当前分支整理好的结果

    def _finish_with_single_answer(  # 定义业务处理函数 _finish_with_single_answer
        self,  # 声明参数 self，供当前逻辑使用
        *,  # 以下参数改为关键字传参，避免调用位置出错
        context,  # 声明参数 context，供当前逻辑使用
        answer: str,  # 声明参数 answer，供当前逻辑使用
        route: str,  # 声明参数 route，供当前逻辑使用
        provider: str,  # 接收问答服务提供方筛选参数
        answer_source: str,  # 声明参数 answer_source，供当前逻辑使用
        risk_level: str,  # 声明参数 risk_level，供当前逻辑使用
        events: list[RAGEvent],  # 声明参数 events，供当前逻辑使用
        context_hits: list[RetrievalHit] | None = None,  # 声明参数 context_hits，供当前逻辑使用
        retrieval: dict[str, Any] | None = None,  # 声明参数 retrieval，供当前逻辑使用
    ) -> RAGPipelineResult:  # 结束 _finish_with_single_answer 的参数声明
        # Use one common closing helper for direct-answer style routes so all responses share
        # the same schema and trace payload.
        """流程图 A/B：直接收口或 FAQ 标准答案收口。"""  # 类文档字符串，概述 RAGPipeline 的用途

        # 直出路径也写历史事件，保证流程图闭环完整。
        events.append(add_turn(context, answer, route=route))  # 执行当前业务步骤并推进后续处理
        events.append(RAGEvent("finish", {"route": route}))  # 执行当前业务步骤并推进后续处理
        # retrieval 中追加 events，便于前端和验收看到完整链路。
        merged_retrieval = dict(retrieval or {})  # 更新当前逻辑中的 merged retrieval
        merged_retrieval["answer_source"] = answer_source  # 执行当前业务步骤并推进后续处理
        merged_retrieval["answer_source_label"] = answer_source_label(answer_source)  # 执行当前业务步骤并推进后续处理
        merged_retrieval["events"] = [event_payload(item) for item in events]  # 执行当前业务步骤并推进后续处理
        return RAGPipelineResult(  # 返回当前分支整理好的结果
            answer=answer,  # 设置 RAGPipelineResult 的 回答内容
            route=route,  # 设置 RAGPipelineResult 的 route
            provider=provider,  # 设置 RAGPipelineResult 的 服务提供方
            answer_source=answer_source,  # 设置 RAGPipelineResult 的 answer source
            risk_level=risk_level,  # 设置 RAGPipelineResult 的 风险等级
            context_hits=context_hits or [],  # 设置 RAGPipelineResult 的 context hits
            related_tasks=self._tasks(context.query),  # 设置 RAGPipelineResult 的 关联任务列表
            retrieval=merged_retrieval,  # 设置 RAGPipelineResult 的 retrieval
            events=events,  # 设置 RAGPipelineResult 的 events
        )  # 结束 RAGPipelineResult 的定义或组装

    def _answer_source_for_route(self, route: str) -> str:  # 定义业务处理函数 _answer_source_for_route
        """把前置路由结果转换成前端可展示的答案来源。"""  # 函数文档字符串，说明 _answer_source_for_route 的职责

        if route == "scene_boundary":  # 根据当前条件决定是否进入对应业务分支
            return "scene_boundary"  # 返回当前分支整理好的结果
        return "router_direct"  # 返回当前分支整理好的结果

    def _with_context(self, answer: str, scenario_label: str, user_role: str, province: str, city: str) -> str:  # 定义业务处理函数 _with_context
        """给答案追加场景、角色、地区和免责声明。"""  # 函数文档字符串，说明 _with_context 的职责

        return f"当前场景：{scenario_label}\n适用角色：{user_role}\n所在地区：{province}{city}\n\n{answer}\n\n风险提示：{DISCLAIMER}"  # 返回当前分支整理好的结果

    def _tasks(self, question: str) -> list[dict[str, Any]]:  # 定义业务处理函数 _tasks
        """返回办事类问题的步骤提示。"""  # 函数文档字符串，说明 _tasks 的职责

        # 办理、申请、仲裁、备案等词说明用户可能需要流程类任务。
        if not any(word in question for word in ("办理", "申请", "仲裁", "材料", "备案", "绑定")):  # 根据当前条件决定是否进入对应业务分支
            return []  # 返回当前分支整理好的结果
        return [  # 返回当前分支整理好的结果
            {  # 补充列表中的 { 项
                "title": "办理复核路径",  # 补充列表中的 标题 项
                "steps": [  # 补充列表中的 steps 项
                    "确认适用地区、员工身份、时间口径和事项类型。",  # 补充列表中的 确认适用地区、员工身份、时间口径和事项类型。 项
                    "准备合同、工资、考勤、社保医保记录或身份证明等材料。",  # 补充列表中的 准备合同、工资、考勤、社保医保记录或身份证明等材料。 项
                    "通过当地人社、医保、税务或仲裁机构官方渠道复核最新办理入口。",  # 补充列表中的 通过当地人社、医保、税务或仲裁机构官方渠道复核最新办理入口。 项
                    "高风险事项交由 HR 或法务形成书面复核结论。",  # 补充列表中的 高风险事项交由 HR 或法务形成书面复核结论。 项
                ],  # 结束 返回结果 的定义或组装
            }  # 补充列表中的 } 项
        ]  # 结束 返回结果 的定义或组装

    def _estimate_risk(self, question: str) -> str:  # 定义业务处理函数 _estimate_risk
        """根据关键词估计风险等级。"""  # 函数文档字符串，说明 _estimate_risk 的职责

        # 高风险词通常涉及解除、赔偿、工伤、仲裁和明显违法风险。
        high_words = ("仲裁", "解除", "赔偿", "工伤", "没签合同", "放弃社保", "违法", "扣款")  # 更新当前逻辑中的 high words
        # 中风险词通常涉及金额、待遇和社保缴费口径。
        medium_words = ("社保", "医保", "产假", "加班", "最低工资", "离职", "基数", "劳动合同", "试用期", "工资")  # 更新当前逻辑中的 medium words
        if any(word in question for word in high_words):  # 根据当前条件决定是否进入对应业务分支
            return "high"  # 返回当前分支整理好的结果
        if any(word in question for word in medium_words):  # 根据当前条件决定是否进入对应业务分支
            return "medium"  # 返回当前分支整理好的结果
        return "low"  # 返回当前分支整理好的结果


def event_payload(event: RAGEvent) -> dict[str, Any]:  # 定义业务处理函数 event_payload
    """把 RAGEvent 转成可 JSON 序列化字典。"""  # 函数文档字符串，说明 event_payload 的职责

    return {"name": event.name, "payload": event.payload}  # 返回当前分支整理好的结果


def answer_source_label(answer_source: str) -> str:  # 定义业务处理函数 answer_source_label
    """把机器来源字段转换成中文展示文案。"""  # 函数文档字符串，说明 answer_source_label 的职责

    labels = {  # 更新当前逻辑中的 labels
        "router_direct": "路由直出",  # 填充返回或配置中的 router direct 字段
        "scene_boundary": "场景边界直出",  # 填充返回或配置中的 scene boundary 字段
        "faq_direct": "FAQ 向量库直出",  # 填充返回或配置中的 faq direct 字段
        "hybrid_retrieval_llm": "混合检索 + 大模型生成",  # 填充返回或配置中的 hybrid retrieval llm 字段
        "hybrid_retrieval_template": "混合检索 + 模板兜底",  # 填充返回或配置中的 hybrid retrieval template 字段
        "error": "异常兜底",  # 填充返回或配置中的 error 字段
    }  # 结束 labels 的定义或组装
    return labels.get(answer_source, answer_source)  # 返回当前分支整理好的结果


DISCLAIMER = "本回答用于企业合规辅助，不替代正式法律意见；涉及金额、期限、待遇和争议处理时，请以当地人社、医保、税务等官方经办口径及企业制度最终复核为准。"  # 定义回答统一附带的合规免责声明
