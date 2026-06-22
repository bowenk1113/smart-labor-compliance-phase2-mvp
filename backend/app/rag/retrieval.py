"""检索准备、FAQ 检索、文档检索和上下文筛选。

本模块对应流程图 6 到 11，并把真实 Milvus RAG 与本地兜底索引隐藏在同一接口后面。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import os  # 导入当前模块运行所依赖的工具或类型
import time  # 导入时间工具，统计耗时或生成时间戳
from typing import Literal  # 导入当前模块运行所依赖的工具或类型

from app.rag.pipeline_schema import RAGQueryContext, RetrievalBundle, RetrievalPlan, RetrievalPreparation  # 导入二期 RAG 检索与问答服务组件
from app.rag.query import prepare_query_with_optional_llm  # 导入二期 RAG 检索与问答服务组件
from app.rag.scenarios import infer_scenario_id  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import RetrievalHit, build_filter_expr, milvus_ivf_pq_index_params, search_docs as search_local_docs, search_faq as search_local_faq  # 导入二期 RAG 检索与问答服务组件


def resolve_active_kb_version() -> str:  # 定义业务处理函数 resolve_active_kb_version
    """流程图 18「Active 版本」：解析当前知识库版本指针。"""  # 函数文档字符串，说明 resolve_active_kb_version 的职责

    # 生产环境可以从 MySQL active 指针读取；MVP 先使用环境变量模拟。
    return os.getenv("PHASE2_KB_VERSION", "phase2_mvp")  # 返回当前分支整理好的结果


def build_retrieval_plan(  # 定义业务处理函数 build_retrieval_plan
    context: RAGQueryContext,  # 声明参数 context，供当前逻辑使用
    *,  # 以下参数改为关键字传参，避免调用位置出错
    rewritten_query: str,  # 声明参数 rewritten_query，供当前逻辑使用
    inferred_scenario_id: str | None,  # 声明参数 inferred_scenario_id，供当前逻辑使用
    intent_score: int,  # 声明参数 intent_score，供当前逻辑使用
    is_follow_up: bool,  # 声明参数 is_follow_up，供当前逻辑使用
    query_type_hint: str | None = None,  # 声明参数 query_type_hint，供当前逻辑使用
) -> RetrievalPlan:  # 结束 build_retrieval_plan 的参数声明
    # This function is the "dynamic retrieval planner" of the MVP.
    # It turns scene, query type, follow-up state, and intent confidence into concrete retrieval parameters.
    """根据上下文生成检索计划。"""  # 模块文档字符串，概述当前文件职责

    # 先把问题归类，这个类型会直接影响 top_k、阈值和上下文数量。
    # 如果 LLM 查询规划器给出了可靠 query_type，就优先采用；否则继续用关键词规则分类。
    query_type = query_type_hint or classify_query_type(rewritten_query, context.scenario.scenario_id, is_follow_up)  # 更新当前逻辑中的 query type
    # reasons 用来记录为什么选择当前计划，方便调试和验收。
    reasons: list[str] = [f"query_type={query_type}"]  # 更新当前逻辑中的 reasons
    # 记录 query_type 是否来自 LLM，方便在接口诊断里证明动态检索计划确实生效。
    if query_type_hint:  # 根据当前条件决定是否进入对应业务分支
        reasons.append("query_type_hint_from_llm")  # 执行当前业务步骤并推进后续处理
    # 默认计划：FAQ 优先，文档适中召回。
    plan_kwargs = {  # 更新当前逻辑中的 plan kwargs
        "plan_name": "faq_first",  # 填充返回或配置中的 plan name 字段
        "query_type": query_type,  # 填充返回或配置中的 query type 字段
        "faq_top_k": 5,  # 填充返回或配置中的 faq top k 字段
        "doc_top_k": 6,  # 填充返回或配置中的 doc top k 字段
        "faq_direct_threshold": 0.58,  # 填充返回或配置中的 faq direct threshold 字段
        "min_context_score": 0.18,  # 填充返回或配置中的 min context score 字段
        "max_context_docs": 5,  # 填充返回或配置中的 max context docs 字段
        "enable_rerank": True,  # 填充返回或配置中的 enable rerank 字段
    }  # 结束 plan_kwargs 的定义或组装
    # 追问问题通常文本短、上下文依赖强，降低 FAQ 直出阈值但增加文档上下文。
    if is_follow_up:  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs.update({"plan_name": "follow_up_expand", "doc_top_k": 8, "faq_direct_threshold": 0.62, "max_context_docs": 6})  # 执行当前业务步骤并推进后续处理
        reasons.append("follow_up_query_requires_more_context")  # 执行当前业务步骤并推进后续处理
    # 办理类问题需要材料、流程、地点等更多上下文。
    if query_type == "procedure":  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs.update({"plan_name": "procedure_deep_context", "doc_top_k": 9, "max_context_docs": 6, "min_context_score": 0.15})  # 执行当前业务步骤并推进后续处理
        reasons.append("procedure_query_needs_steps_and_materials")  # 执行当前业务步骤并推进后续处理
    # 政策类问题需要更广召回，避免只命中 FAQ 中的一个口径。
    if query_type == "policy":  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs.update({"plan_name": "broad_policy", "faq_top_k": 6, "doc_top_k": 8, "max_context_docs": 6})  # 执行当前业务步骤并推进后续处理
        reasons.append("policy_query_needs_broader_recall")  # 执行当前业务步骤并推进后续处理
    # 争议/解除/赔偿等高风险问题需要更多证据，且不宜过早 FAQ 直出。
    if query_type == "dispute":  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs.update({"plan_name": "high_risk_dispute", "faq_direct_threshold": 0.72, "doc_top_k": 10, "max_context_docs": 7, "min_context_score": 0.14})  # 执行当前业务步骤并推进后续处理
        reasons.append("high_risk_query_requires_more_evidence")  # 执行当前业务步骤并推进后续处理
    # FAQ-like 问题适合更积极地走 FAQ 直出。
    if query_type == "faq_like":  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs.update({"plan_name": "faq_fast_path", "faq_top_k": 6, "faq_direct_threshold": 0.55, "doc_top_k": 5, "max_context_docs": 4})  # 执行当前业务步骤并推进后续处理
        reasons.append("faq_like_query_can_use_standard_answer")  # 执行当前业务步骤并推进后续处理
    # 高风险争议类场景需要更多上下文，因此略微提高文档召回数量。
    if context.scenario.scenario_id == "dispute_service":  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs.update({"plan_name": "dispute_scene_deep_context", "doc_top_k": max(plan_kwargs["doc_top_k"], 10), "max_context_docs": max(plan_kwargs["max_context_docs"], 7)})  # 执行当前业务步骤并推进后续处理
        reasons.append("selected_scene_is_dispute_service")  # 执行当前业务步骤并推进后续处理
    # 如果模型推断场景和前端选择场景一致且分数高，说明问题场景明确，可以提高 FAQ 直出效率。
    if inferred_scenario_id == context.scenario.scenario_id and intent_score >= 6 and query_type not in {"dispute", "procedure"}:  # 根据当前条件决定是否进入对应业务分支
        plan_kwargs["faq_direct_threshold"] = min(plan_kwargs["faq_direct_threshold"], 0.56)  # 执行当前业务步骤并推进后续处理
        reasons.append("strong_scene_intent_allows_lower_faq_threshold")  # 执行当前业务步骤并推进后续处理
    # 把 reasons 存进不可变 tuple，便于响应 JSON 序列化。
    return RetrievalPlan(**plan_kwargs, reasons=tuple(reasons))  # 返回当前分支整理好的结果


def classify_query_type(question: str, scenario_id: str, is_follow_up: bool) -> str:  # 定义业务处理函数 classify_query_type
    """把问题粗分为动态检索计划可用的类型。"""  # 函数文档字符串，说明 classify_query_type 的职责

    # 追问优先标记为 follow_up。
    if is_follow_up:  # 根据当前条件决定是否进入对应业务分支
        return "follow_up"  # 返回当前分支整理好的结果
    # 办理类关键词代表用户需要流程、材料、地点等上下文。
    if any(word in question for word in ("办理", "申请", "材料", "流程", "地点", "电话", "地址", "怎么绑定", "去哪")):  # 根据当前条件决定是否进入对应业务分支
        return "procedure"  # 返回当前分支整理好的结果
    # 争议和高风险处置类问题要更谨慎。
    if any(word in question for word in ("仲裁", "解除", "赔偿", "工伤", "违法", "扣款", "没签合同", "争议")) or scenario_id == "dispute_service":  # 根据当前条件决定是否进入对应业务分支
        return "dispute"  # 返回当前分支整理好的结果
    # 政策类问题通常包含“标准、多少、期限、基数、比例、规定”等词。
    if any(word in question for word in ("政策", "规定", "标准", "多少", "期限", "基数", "比例", "天", "金额")):  # 根据当前条件决定是否进入对应业务分支
        return "policy"  # 返回当前分支整理好的结果
    # 是不是、可以吗、怎么办这类高频句式通常很像 FAQ。
    if any(word in question for word in ("可以吗", "能不能", "是否", "怎么办", "怎么处理")):  # 根据当前条件决定是否进入对应业务分支
        return "faq_like"  # 返回当前分支整理好的结果
    # 默认归为 general。
    return "general"  # 返回当前分支整理好的结果


def prepare_retrieval(context: RAGQueryContext) -> RetrievalPreparation:  # 定义业务处理函数 prepare_retrieval
    # This is the unified retrieval-preparation entry.
    # It assembles rewritten query, variants, inferred intent, and the final retrieval plan into one package.
    """流程图 6/7：生成 intent、plan、variants 和 profile 参数包。"""  # 函数文档字符串，说明 prepare_retrieval 的职责

    # 查询准备会先尝试 LLM 动态规划；未配置 Key 或失败时自动回落到规则改写和规则变体。
    query_preparation = prepare_query_with_optional_llm(context.query, context.history)  # 更新当前逻辑中的 query preparation
    # 是否追问会影响检索计划，例如追问需要更大的上下文窗口。
    is_follow_up = query_preparation.is_follow_up  # 更新当前逻辑中的 is follow up
    # rewritten_query 是追问改写后的主查询。
    rewritten_query = query_preparation.rewritten_query  # 更新当前逻辑中的 rewritten query
    # query_variants 是 FAQ 和文档混合检索的多路召回输入。
    query_variants = query_preparation.query_variants  # 更新当前逻辑中的 query variants
    # 意图识别在 MVP 中使用场景关键词推断，后续可替换为 BERT/LLM 分类器。
    inferred_id, score = infer_scenario_id(rewritten_query)  # 执行当前业务步骤并推进后续处理
    # 检索计划集中保存 top_k、阈值、上下文数量等参数，并根据问题类型动态生成。
    plan = build_retrieval_plan(  # 更新当前逻辑中的 plan
        context,  # 设置 build_retrieval_plan 的 字段
        rewritten_query=rewritten_query,  # 设置 build_retrieval_plan 的 rewritten query
        inferred_scenario_id=inferred_id,  # 设置 build_retrieval_plan 的 inferred scenario id
        intent_score=score,  # 设置 build_retrieval_plan 的 intent score
        is_follow_up=is_follow_up,  # 设置 build_retrieval_plan 的 is follow up
        query_type_hint=query_preparation.query_type_hint,  # 设置 build_retrieval_plan 的 query type hint
    )  # 结束 build_retrieval_plan 的定义或组装
    # profile 记录检索画像，方便调试和验收。
    profile = {  # 更新当前逻辑中的 profile
        "scenario_id": context.scenario.scenario_id,  # 填充返回或配置中的 scenario id 字段
        "inferred_scenario_id": inferred_id,  # 填充返回或配置中的 inferred scenario id 字段
        "intent_score": score,  # 填充返回或配置中的 intent score 字段
        "tenant_id": context.data_scope.tenant_id,  # 填充返回或配置中的 租户 ID 字段
        "roles": list(context.data_scope.roles),  # 填充返回或配置中的 roles 字段
        "province": context.data_scope.province,  # 填充返回或配置中的 省份 字段
        "city": context.data_scope.city,  # 填充返回或配置中的 城市 字段
        "vector_backend": vector_backend(),  # 填充返回或配置中的 vector backend 字段
        "is_follow_up": is_follow_up,  # 填充返回或配置中的 is follow up 字段
        "query_variant_count": len(query_variants),  # 填充返回或配置中的 query variant count 字段
        "query_type_hint": query_preparation.query_type_hint,  # 填充返回或配置中的 query type hint 字段
        "retrieval_plan": plan.plan_name,  # 填充返回或配置中的 retrieval plan 字段
        "retrieval_plan_reasons": list(plan.reasons),  # 填充返回或配置中的 retrieval plan reasons 字段
    }  # 结束 profile 的定义或组装
    # 把查询 LLM 的诊断信息合并进 profile，前端和验收文档都可以看到是否调用了大模型生成变体。
    profile.update(query_preparation.diagnostics)  # 执行当前业务步骤并推进后续处理
    # RetrievalPreparation 与流程图中的参数包节点一一对应。
    return RetrievalPreparation(  # 返回当前分支整理好的结果
        rewritten_query=rewritten_query,  # 设置 RetrievalPreparation 的 rewritten query
        query_variants=query_variants,  # 设置 RetrievalPreparation 的 query variants
        intent=inferred_id or context.scenario.scenario_id,  # 设置 RetrievalPreparation 的 intent
        plan=plan,  # 设置 RetrievalPreparation 的 plan
        profile=profile,  # 设置 RetrievalPreparation 的 profile
    )  # 结束 RetrievalPreparation 的定义或组装


def vector_backend() -> str:  # 定义业务处理函数 vector_backend
    """读取当前向量检索后端。"""  # 函数文档字符串，说明 vector_backend 的职责

    return os.getenv("PHASE2_VECTOR_BACKEND", "local").lower()  # 返回当前分支整理好的结果


def search_faq(context: RAGQueryContext, preparation: RetrievalPreparation) -> tuple[list[RetrievalHit], float]:  # 定义业务处理函数 search_faq
    # FAQ retrieval uses the same query variants as document retrieval,
    # but searches the FAQ vector collection first for low-cost direct answers.
    """流程图 8：检索 FAQ 向量库。"""  # 函数文档字符串，说明 search_faq 的职责

    return _search(context, preparation.query_variants, source_type="faq", top_k=preparation.plan.faq_top_k)  # 返回当前分支整理好的结果


def search_doc(context: RAGQueryContext, preparation: RetrievalPreparation) -> tuple[list[RetrievalHit], float]:  # 定义业务处理函数 search_doc
    # Document retrieval is the second stage of the hybrid pipeline.
    # It is only used after FAQ cannot confidently answer the question.
    """流程图 10：检索文档知识库。"""  # 函数文档字符串，说明 search_doc 的职责

    return _search(context, preparation.query_variants, source_type="doc", top_k=preparation.plan.doc_top_k)  # 返回当前分支整理好的结果


def search_all(context: RAGQueryContext, preparation: RetrievalPreparation) -> RetrievalBundle:  # 定义业务处理函数 search_all
    """先检索 FAQ，再在需要时检索文档。"""  # 函数文档字符串，说明 search_all 的职责

    # FAQ 检索永远先执行，因为高频问题可以直接返回标准答案。
    faq_hits, faq_elapsed_ms = search_faq(context, preparation)  # 执行当前业务步骤并推进后续处理
    # 文档检索由 Pipeline 在 FAQ 未高置信命中时调用；这里保留组合接口供测试使用。
    doc_hits, doc_elapsed_ms = search_doc(context, preparation)  # 执行当前业务步骤并推进后续处理
    return RetrievalBundle(  # 返回当前分支整理好的结果
        faq_hits=faq_hits,  # 设置 RetrievalBundle 的 faq hits
        doc_hits=doc_hits,  # 设置 RetrievalBundle 的 doc hits
        faq_elapsed_ms=faq_elapsed_ms,  # 设置 RetrievalBundle 的 faq elapsed ms
        doc_elapsed_ms=doc_elapsed_ms,  # 设置 RetrievalBundle 的 doc elapsed ms
    )  # 结束 RetrievalBundle 的定义或组装


def faq_direct_answer(query: str, hits: list[RetrievalHit], threshold: float) -> str | None:  # 定义业务处理函数 faq_direct_answer
    # This is the core "FAQ direct answer" guard.
    # It exists to reduce cost, but it must stay conservative enough to avoid answering the wrong question.
    """流程图 9/B：FAQ 高置信时返回标准答案。

    二期 MVP 里，FAQ 直出不能只看向量分数高不高，还要防止“相近但不是同一问法”的误直出。
    比如“试用期工资是多少”更像金额/标准类问题，不应该仅因为相似度高，就被
    “试用期工资可以低于最低工资吗”这种是/否判断题直接抢答。
    所以这里增加三层保护：
    1. top1 分数必须达到 FAQ 直出阈值；
    2. top1 和 top2 过于接近时，不直接判定为唯一标准问；
    3. 用户问法与 FAQ 标题的问句类型要基本一致，例如“多少/几天/标准”类问题，
       不能直接命中“可以吗/是否/能不能”类 FAQ。
    """

    # 没有 FAQ 命中时不能直出。
    if not hits:  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    # 同标题 FAQ 可能同时来自内置 faq.csv 和后台 faq_runtime.csv；先按标题去重，避免重复记录把 top1/top2 差距拉得过近。
    deduped_hits = _dedupe_hits_by_title(hits)  # 更新当前逻辑中的 deduped hits
    # top1 分数低于阈值时继续进入文档 RAG。
    if deduped_hits[0].score < threshold:  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    # top1 与 top2 过于接近时，说明 FAQ 命中并不稳定，继续走混合检索更稳妥。
    if len(deduped_hits) > 1 and abs(deduped_hits[0].score - deduped_hits[1].score) < 0.035:  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    # 用户问法与候选 FAQ 的问题类型明显不一致时，不做 FAQ 直出。
    top_question = str(deduped_hits[0].document.metadata.get("title") or "").strip()  # 更新当前逻辑中的 top question
    if top_question and not _same_question_shape(query, top_question):  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    # FAQ 标准答案保存在 metadata.answer 中。
    answer = deduped_hits[0].document.metadata.get("answer")  # 更新当前逻辑中的 回答内容
    return str(answer).strip() if answer else None  # 返回当前分支整理好的结果


def _same_question_shape(query: str, candidate_question: str) -> bool:  # 定义业务处理函数 _same_question_shape
    # Shape-matching is a cheap semantic safety check.
    # It helps prevent an "amount" question from being answered by a "yes/no" FAQ, and vice versa.
    """判断用户原问题和 FAQ 标题是否属于同类问法。"""  # 函数文档字符串，说明 _same_question_shape 的职责

    query_type = _question_shape(query)  # 更新当前逻辑中的 query type
    candidate_type = _question_shape(candidate_question)  # 更新当前逻辑中的 candidate type
    # 任一侧无法稳定识别时，交回给分数判断，不做强限制。
    if query_type == "other" or candidate_type == "other":  # 根据当前条件决定是否进入对应业务分支
        return True  # 返回当前分支整理好的结果
    return query_type == candidate_type  # 返回当前分支整理好的结果


def _question_shape(text: str) -> str:  # 定义业务处理函数 _question_shape
    # This lightweight classifier is rule-based on purpose.
    # It gives FAQ direct-answer logic a stable and explainable question-type signal.
    """把中文问题粗分为金额/标准类、是非判断类、流程类等。"""  # 函数文档字符串，说明 _question_shape 的职责

    normalized = (text or "").strip()  # 初始化当前导出行的标准化结果字典
    if any(word in normalized for word in ("多少", "几天", "几个月", "多少钱", "比例", "标准", "基数", "金额", "上限", "下限")):  # 根据当前条件决定是否进入对应业务分支
        return "amount_or_standard"  # 返回当前分支整理好的结果
    if any(word in normalized for word in ("可以吗", "能不能", "是否", "可否", "行不行", "算不算")):  # 根据当前条件决定是否进入对应业务分支
        return "yes_no"  # 返回当前分支整理好的结果
    if any(word in normalized for word in ("怎么办", "如何", "怎么", "流程", "材料", "去哪", "哪里办")):  # 根据当前条件决定是否进入对应业务分支
        return "procedure"  # 返回当前分支整理好的结果
    return "other"  # 返回当前分支整理好的结果


def select_context_docs(faq_hits: list[RetrievalHit], doc_hits: list[RetrievalHit], plan: RetrievalPlan) -> list[RetrievalHit]:  # 定义业务处理函数 select_context_docs
    # This function chooses which evidence fragments are allowed into the final prompt.
    # In other words, it is the "context window budget manager" of the MVP.
    """流程图 11：筛选进入 Prompt 的上下文。"""  # 函数文档字符串，说明 select_context_docs 的职责

    # FAQ top2 可以作为补充证据，文档命中作为主要上下文。
    candidates = [hit for hit in [*_dedupe_hits_by_title(faq_hits)[:2], *doc_hits] if hit.score >= plan.min_context_score]  # 更新当前逻辑中的 candidates
    # 统一按相关性分数降序排列。
    candidates.sort(key=lambda item: item.score, reverse=True)  # 执行当前业务步骤并推进后续处理
    # 只保留有限上下文，避免 Prompt 被低质量片段撑大。
    return candidates[: plan.max_context_docs]  # 返回当前分支整理好的结果


def _dedupe_hits_by_title(hits: list[RetrievalHit]) -> list[RetrievalHit]:  # 定义业务处理函数 _dedupe_hits_by_title
    """按 FAQ 标题去重，优先保留分数更高的命中。"""  # 函数文档字符串，说明 _dedupe_hits_by_title 的职责

    deduped: list[RetrievalHit] = []  # 更新当前逻辑中的 deduped
    seen_titles: set[str] = set()  # 更新当前逻辑中的 seen titles
    for hit in hits:  # 遍历当前集合中的每一项并逐个处理
        title = str(hit.document.metadata.get("title") or hit.document.metadata.get("file_name") or "").strip()  # 更新当前逻辑中的 title
        normalized_title = title.casefold() if title else ""  # 更新当前逻辑中的 normalized title
        if normalized_title and normalized_title in seen_titles:  # 根据当前条件决定是否进入对应业务分支
            continue  # 跳过当前项，继续处理下一项数据
        if normalized_title:  # 根据当前条件决定是否进入对应业务分支
            seen_titles.add(normalized_title)  # 更新当前逻辑中的 seen titles
        deduped.append(hit)  # 把当前去重后的命中追加到结果列表
    return deduped or hits  # 返回当前分支整理好的结果


def build_context(context_hits: list[RetrievalHit]) -> str:  # 定义业务处理函数 build_context
    # This serializes selected evidence into prompt-ready text.
    # Titles and scores are kept so downstream answers can remain inspectable and source-aware.
    """把命中文档拼成可供 LLM 使用的上下文文本。"""  # 函数文档字符串，说明 build_context 的职责

    # 每条上下文保留标题、分数和正文，便于回答时引用来源。
    parts: list[str] = []  # 更新当前逻辑中的 parts
    for index, hit in enumerate(context_hits, start=1):  # 遍历当前集合中的每一项并逐个处理
        metadata = hit.document.metadata  # 更新当前逻辑中的 metadata
        title = metadata.get("title") or metadata.get("file_name") or "知识库片段"  # 更新当前逻辑中的 标题
        parts.append(f"[{index}] {title} score={hit.score:.3f}\n{hit.document.content}")  # 执行当前业务步骤并推进后续处理
    # 空上下文返回空字符串，Pipeline 会走信息不足收口。
    return "\n\n".join(parts)  # 返回当前分支整理好的结果


def retrieval_diagnostics(  # 定义业务处理函数 retrieval_diagnostics
    *,  # 以下参数改为关键字传参，避免调用位置出错
    context: RAGQueryContext,  # 声明参数 context，供当前逻辑使用
    preparation: RetrievalPreparation,  # 声明参数 preparation，供当前逻辑使用
    kb_version: str,  # 声明参数 kb_version，供当前逻辑使用
    faq_hits: list[RetrievalHit],  # 声明参数 faq_hits，供当前逻辑使用
    doc_hits: list[RetrievalHit],  # 声明参数 doc_hits，供当前逻辑使用
    faq_elapsed_ms: float,  # 声明参数 faq_elapsed_ms，供当前逻辑使用
    doc_elapsed_ms: float,  # 声明参数 doc_elapsed_ms，供当前逻辑使用
) -> dict:  # 结束 retrieval_diagnostics 的参数声明
    # This payload is intentionally verbose because it is used for frontend inspection,
    # acceptance checks, and proving that the RAG chain actually executed.
    """汇总流程图需要展示的检索诊断信息。"""  # 模块文档字符串，概述当前文件职责

    # 诊断信息会返回给前端和验收文档，用来证明 RAG 链路实际执行。
    return {  # 返回当前分支整理好的结果
        "scenario_id": context.scenario.scenario_id,  # 填充返回或配置中的 scenario id 字段
        "kb_version": kb_version,  # 填充返回或配置中的 kb version 字段
        "data_scope": {  # 填充返回或配置中的 data scope 字段
            "tenant_id": context.data_scope.tenant_id,  # 填充返回或配置中的 租户 ID 字段
            "roles": list(context.data_scope.roles),  # 填充返回或配置中的 roles 字段
            "visibility": context.data_scope.visibility,  # 填充返回或配置中的 visibility 字段
            "province": context.data_scope.province,  # 填充返回或配置中的 省份 字段
            "city": context.data_scope.city,  # 填充返回或配置中的 城市 字段
        },  # 结束 返回结果 的定义或组装
        "rewritten_query": preparation.rewritten_query,  # 填充返回或配置中的 rewritten query 字段
        "query_variants": preparation.query_variants,  # 填充返回或配置中的 query variants 字段
        "intent": preparation.intent,  # 填充返回或配置中的 intent 字段
        "profile": preparation.profile,  # 填充返回或配置中的 profile 字段
        "plan": {  # 填充返回或配置中的 plan 字段
            "plan_name": preparation.plan.plan_name,  # 填充返回或配置中的 plan name 字段
            "query_type": preparation.plan.query_type,  # 填充返回或配置中的 query type 字段
            "faq_top_k": preparation.plan.faq_top_k,  # 填充返回或配置中的 faq top k 字段
            "doc_top_k": preparation.plan.doc_top_k,  # 填充返回或配置中的 doc top k 字段
            "faq_direct_threshold": preparation.plan.faq_direct_threshold,  # 填充返回或配置中的 faq direct threshold 字段
            "min_context_score": preparation.plan.min_context_score,  # 填充返回或配置中的 min context score 字段
            "max_context_docs": preparation.plan.max_context_docs,  # 填充返回或配置中的 max context docs 字段
            "enable_rerank": preparation.plan.enable_rerank,  # 填充返回或配置中的 enable rerank 字段
            "reasons": list(preparation.plan.reasons),  # 填充返回或配置中的 reasons 字段
        },  # 结束 返回结果 的定义或组装
        "faq_hits": len(faq_hits),  # 填充返回或配置中的 faq hits 字段
        "doc_hits": len(doc_hits),  # 填充返回或配置中的 doc hits 字段
        "faq_top_score": faq_hits[0].score if faq_hits else 0,  # 填充返回或配置中的 faq top score 字段
        "doc_top_score": doc_hits[0].score if doc_hits else 0,  # 填充返回或配置中的 doc top score 字段
        "faq_elapsed_ms": round(faq_elapsed_ms, 2),  # 填充返回或配置中的 faq elapsed ms 字段
        "doc_elapsed_ms": round(doc_elapsed_ms, 2),  # 填充返回或配置中的 doc elapsed ms 字段
        "faq_filter_expr": build_filter_expr(  # 填充返回或配置中的 faq filter expr 字段
            scenario_id=context.scenario.scenario_id,  # 填充返回或配置中的 scenario id 字段
            source_type="faq",  # 填充返回或配置中的 source type 字段
            tenant_id=context.data_scope.tenant_id,  # 填充返回或配置中的 租户 ID 字段
            kb_version=kb_version,  # 填充返回或配置中的 kb version 字段
        ),  # 填充返回或配置中的 字段 字段
        "doc_filter_expr": build_filter_expr(  # 填充返回或配置中的 doc filter expr 字段
            scenario_id=context.scenario.scenario_id,  # 填充返回或配置中的 scenario id 字段
            source_type="doc",  # 填充返回或配置中的 source type 字段
            tenant_id=context.data_scope.tenant_id,  # 填充返回或配置中的 租户 ID 字段
            kb_version=kb_version,  # 填充返回或配置中的 kb version 字段
        ),  # 填充返回或配置中的 字段 字段
        "ivf_pq_index_params": milvus_ivf_pq_index_params(),  # 填充返回或配置中的 ivf pq index params 字段
        "vector_backend": vector_backend(),  # 填充返回或配置中的 vector backend 字段
    }  # 结束 返回结果 的定义或组装


def _search(  # 定义业务处理函数 _search
    context: RAGQueryContext,  # 声明参数 context，供当前逻辑使用
    query_variants: list[str],  # 声明参数 query_variants，供当前逻辑使用
    *,  # 以下参数改为关键字传参，避免调用位置出错
    source_type: Literal["faq", "doc"],  # 声明参数 source_type，供当前逻辑使用
    top_k: int,  # 声明参数 top_k，供当前逻辑使用
) -> tuple[list[RetrievalHit], float]:  # 结束 _search 的参数声明
    """按配置选择真实 Milvus RAG 或本地兜底索引。"""  # 模块文档字符串，概述当前文件职责

    # 真实验收时使用 PHASE2_VECTOR_BACKEND=milvus。
    started = time.perf_counter()  # 更新当前逻辑中的 started
    if vector_backend() == "milvus":  # 根据当前条件决定是否进入对应业务分支
        try:  # 尝试优先走真实 Milvus 混合检索链路
            from app.rag.milvus_store import search_milvus  # 导入二期 RAG 检索与问答服务组件

            hits = search_milvus(context.scenario, query_variants, source_type=source_type, top_k=top_k)  # 更新当前逻辑中的 hits
            if hits:  # Milvus 只要成功召回出结果，就直接返回生产链路命中
                return hits, (time.perf_counter() - started) * 1000  # 返回当前分支整理好的结果
        except Exception:  # Milvus 检索异常时自动降级到本地索引，避免整条问答链路空回答
            pass  # 这里故意吞掉异常，统一在后面的本地检索里兜底
    # 本地 FAQ 向量索引用字符 ngram 模拟 dense + keyword 融合召回。
    if source_type == "faq":  # 根据当前条件决定是否进入对应业务分支
        hits, _elapsed_ms = search_local_faq(context.scenario, query_variants, top_k=top_k)  # 更新当前逻辑中的 hits, _elapsed_ms
        return hits, (time.perf_counter() - started) * 1000  # 返回当前分支整理好的结果
    # 本地文档向量索引用同一接口返回 RetrievalHit。
    hits, _elapsed_ms = search_local_docs(context.scenario, query_variants, top_k=top_k)  # 更新当前逻辑中的 hits, _elapsed_ms
    return hits, (time.perf_counter() - started) * 1000  # 返回当前分支整理好的结果
