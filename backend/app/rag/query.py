"""查询改写、查询变体与 LLM 动态检索计划辅助。

本模块处在 RAG 链路的「检索准备」阶段，目标是把用户原始问题变成更适合向量库检索的查询包：
1. 追问改写：把「那怎么办」这类短问题补全成独立问题。
2. 查询变体：把社保、医保、劳动仲裁等词扩展成同义表达，用于混合检索多路召回。
3. LLM 增强：配置 API Key 后，可让大模型生成 rewritten_query、variants 和 query_type。

注意：LLM 增强默认关闭，未配置 Key 时自动回落到确定性规则，保证本地 MVP 不依赖外部服务也能运行。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import json  # 导入 JSON 编解码工具，处理结构化字段
import os  # 导入当前模块运行所依赖的工具或类型
import re  # 导入当前模块运行所依赖的工具或类型
from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型
from typing import Any  # 导入当前模块运行所依赖的工具或类型

from app.rag.generator import openai_compatible_chat  # 导入二期 RAG 检索与问答服务组件


# 这些词通常说明用户在追问上一轮问题，需要把历史上下文拼回当前查询。
FOLLOW_UP_HINTS = ("那", "这个", "它", "怎么处理", "怎么办", "材料", "流程", "电话", "地址")  # 更新当前逻辑中的 FOLLOW UP HINTS

# 检索计划目前支持的稳定 query_type；LLM 返回其他类型时会回落到 general。
VALID_QUERY_TYPES = {"policy", "procedure", "dispute", "faq_like", "general", "follow_up"}  # 更新当前逻辑中的 VALID QUERY TYPES


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class QueryPreparationResult:  # 定义业务类 QueryPreparationResult
    """查询准备结果，供 retrieval.py 继续生成检索计划。"""  # 类文档字符串，概述 QueryPreparationResult 的用途

    # rewritten_query 是用于检索的主查询，可能是规则改写，也可能是 LLM 改写。
    rewritten_query: str  # 执行当前业务步骤并推进后续处理
    # query_variants 是多路召回查询列表，第一条永远尽量保留主查询。
    query_variants: list[str]  # 执行当前业务步骤并推进后续处理
    # is_follow_up 记录当前问题是否被判断为追问。
    is_follow_up: bool  # 执行当前业务步骤并推进后续处理
    # query_type_hint 是 LLM 给出的动态检索计划提示，例如 policy/procedure/dispute。
    query_type_hint: str | None  # 执行当前业务步骤并推进后续处理
    # diagnostics 记录是否启用 LLM、是否实际调用成功、失败原因等，方便前端验收。
    diagnostics: dict[str, Any]  # 执行当前业务步骤并推进后续处理


def needs_rewrite(question: str, history: list[str] | None = None) -> bool:  # 定义业务处理函数 needs_rewrite
    # This is a lightweight follow-up detector.
    # It decides whether the current user question is too short or too referential to search directly.
    """判断用户问题是否像追问。"""  # 函数文档字符串，说明 needs_rewrite 的职责

    # 没有历史上下文时，不能把当前问题当作追问改写。
    if not history:  # 根据当前条件决定是否进入对应业务分支
        return False  # 返回当前分支整理好的结果
    # 去掉首尾空白，避免空格影响长度判断。
    text = question.strip()  # 把文件字节内容解码成可解析的文本
    # 短句或带有指代词的问题，通常需要结合上一轮问题理解。
    return len(text) <= 14 or any(hint in text for hint in FOLLOW_UP_HINTS)  # 返回当前分支整理好的结果


def rewrite_query_if_needed(question: str, history: list[str] | None = None) -> str:  # 定义业务处理函数 rewrite_query_if_needed
    # When the user is asking a follow-up question, rewrite it into a standalone query
    # so vector retrieval has enough context to work with.
    """把追问改写为独立问题。"""  # 函数文档字符串，说明 rewrite_query_if_needed 的职责

    # 非追问问题直接使用原问题。
    if not needs_rewrite(question, history):  # 根据当前条件决定是否进入对应业务分支
        return question  # 返回当前分支整理好的结果
    # MVP 取最近一轮历史作为补全依据。
    last_turn = history[-1] if history else ""  # 更新当前逻辑中的 last turn
    # 用「追问」分隔历史与当前问题，减少检索时语义混淆。
    return f"{last_turn}；追问：{question}"  # 返回当前分支整理好的结果


def generate_query_variants(question: str, max_variants: int = 4) -> list[str]:  # 定义业务处理函数 generate_query_variants
    # Query variants are the simplest form of multi-route retrieval.
    # They widen recall by expanding common labor and social-insurance synonyms.
    """生成用于多路检索的查询变体。"""  # 函数文档字符串，说明 generate_query_variants 的职责

    # 第一条必须是原始/改写后的主查询，保证召回不偏离用户本意。
    variants = [question.strip()]  # 更新当前逻辑中的 variants
    # 这些替换词覆盖劳动社保高频同义表达，属于无需调用大模型的确定性变体。
    replacements = [  # 更新当前逻辑中的 replacements
        ("社保", "社会保险"),  # 补充列表中的 ("社保", "社会保险") 项
        ("医保", "医疗保险"),  # 补充列表中的 ("医保", "医疗保险") 项
        ("劳动仲裁", "劳动争议仲裁"),  # 补充列表中的 ("劳动仲裁", "劳动争议仲裁") 项
        ("产假", "生育假"),  # 补充列表中的 ("产假", "生育假") 项
        ("陪产假", "护理假"),  # 补充列表中的 ("陪产假", "护理假") 项
        ("底薪", "最低工资"),  # 补充列表中的 ("底薪", "最低工资") 项
        ("交多少钱", "缴费标准"),  # 补充列表中的 ("交多少钱", "缴费标准") 项
        ("去哪", "办理地点"),  # 补充列表中的 ("去哪", "办理地点") 项
        ("怎么办", "办理流程"),  # 补充列表中的 ("怎么办", "办理流程") 项
        ("需要什么", "申请材料"),  # 补充列表中的 ("需要什么", "申请材料") 项
    ]  # 结束 replacements 的定义或组装
    # 逐个尝试同义词替换，直到达到 max_variants。
    for old, new in replacements:  # 遍历当前集合中的每一项并逐个处理
        if old in question and len(variants) < max_variants:  # 根据当前条件决定是否进入对应业务分支
            candidate = question.replace(old, new)  # 更新当前逻辑中的 candidate
            if candidate not in variants:  # 根据当前条件决定是否进入对应业务分支
                variants.append(candidate)  # 执行当前业务步骤并推进后续处理
    return variants[:max_variants]  # 返回当前分支整理好的结果


def prepare_query_with_optional_llm(question: str, history: list[str] | None = None) -> QueryPreparationResult:  # 定义业务处理函数 prepare_query_with_optional_llm
    # This function is the query-planning entry for the MVP.
    # With API keys configured, it can call an LLM to generate rewrites, variants, and query-type hints.
    # Without API keys, it falls back to deterministic local rules.
    """生成检索前的查询包：优先可选 LLM，失败时使用本地规则。

    环境变量控制方式：
    - PHASE2_QUERY_LLM_ENABLED=true 时才尝试调用大模型。
    - PHASE2_LLM_API_KEY 留空时不会产生外部调用，会自动走规则兜底。
    - PHASE2_QUERY_LLM_MAX_VARIANTS 控制最多生成几个查询变体。
    """

    # max_variants 既限制规则变体，也限制 LLM 变体，防止一次请求召回路数过多。
    max_variants = _env_int("PHASE2_QUERY_LLM_MAX_VARIANTS", 4)  # 更新当前逻辑中的 max variants
    # 先生成确定性结果，后面 LLM 失败时直接复用它。
    fallback = _prepare_query_by_rules(question, history, max_variants=max_variants)  # 更新当前逻辑中的 fallback
    # 开关默认关闭，保证本地演示无需任何大模型 Key。
    llm_enabled = os.getenv("PHASE2_QUERY_LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}  # 更新当前逻辑中的 llm enabled
    if not llm_enabled:  # 根据当前条件决定是否进入对应业务分支
        fallback.diagnostics["query_llm_enabled"] = False  # 执行当前业务步骤并推进后续处理
        fallback.diagnostics["query_llm_used"] = False  # 执行当前业务步骤并推进后续处理
        fallback.diagnostics["query_llm_reason"] = "PHASE2_QUERY_LLM_ENABLED is false"  # 执行当前业务步骤并推进后续处理
        return fallback  # 返回当前分支整理好的结果
    # 目前 MVP 只实现 OpenAI-compatible 协议，配置项预留给后续扩展本地 LangChain/企业网关。
    backend = os.getenv("PHASE2_QUERY_LLM_BACKEND", "openai_compatible").strip().lower() or "openai_compatible"  # 更新当前逻辑中的 backend
    if backend not in {"openai", "openai_compatible"}:  # 根据当前条件决定是否进入对应业务分支
        fallback.diagnostics.update(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "query_llm_enabled": True,  # 执行当前业务步骤并推进后续处理
                "query_llm_used": False,  # 执行当前业务步骤并推进后续处理
                "query_llm_backend": backend,  # 执行当前业务步骤并推进后续处理
                "query_llm_reason": "unsupported query llm backend",  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
        return fallback  # 返回当前分支整理好的结果
    # 构造要求严格 JSON 的提示词，便于后端稳定解析并进入动态检索计划。
    system_prompt = (  # 更新当前逻辑中的 system prompt
        "你是企业用工与社保合规 RAG 系统的查询规划器。"  # 执行当前业务步骤并推进后续处理
        "只输出 JSON，不要输出 Markdown。"  # 执行当前业务步骤并推进后续处理
        "任务是把用户问题改写为适合检索的独立查询，并生成少量不同表达的查询变体。"  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    user_prompt = _build_query_llm_prompt(question=question, history=history or [], max_variants=max_variants)  # 更新当前逻辑中的 user prompt
    # 单独 temperature 让查询规划更稳定；没有配置时默认 0.1。
    llm_result = openai_compatible_chat(  # 更新当前逻辑中的 llm result
        system_prompt=system_prompt,  # 设置 openai_compatible_chat 的 system prompt
        user_prompt=user_prompt,  # 设置 openai_compatible_chat 的 user prompt
        purpose="query_rewrite_and_variants",  # 设置 openai_compatible_chat 的 purpose
        temperature=_env_float("PHASE2_QUERY_LLM_TEMPERATURE", 0.1),  # 设置 openai_compatible_chat 的 temperature
    )  # 结束 openai_compatible_chat 的定义或组装
    # 如果没有配置 Key、调用失败或返回空文本，就使用规则结果并把原因写入 diagnostics。
    if not llm_result.used_llm or not llm_result.text:  # 根据当前条件决定是否进入对应业务分支
        fallback.diagnostics.update(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "query_llm_enabled": True,  # 执行当前业务步骤并推进后续处理
                "query_llm_used": False,  # 执行当前业务步骤并推进后续处理
                "query_llm_backend": backend,  # 执行当前业务步骤并推进后续处理
                "query_llm_provider": llm_result.provider,  # 执行当前业务步骤并推进后续处理
                "query_llm_detail": llm_result.detail,  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
        return fallback  # 返回当前分支整理好的结果
    # 解析大模型 JSON；解析失败时同样不影响主链路。
    parsed = _parse_llm_json(llm_result.text)  # 更新当前逻辑中的 parsed
    if not parsed:  # 根据当前条件决定是否进入对应业务分支
        fallback.diagnostics.update(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "query_llm_enabled": True,  # 执行当前业务步骤并推进后续处理
                "query_llm_used": False,  # 执行当前业务步骤并推进后续处理
                "query_llm_backend": backend,  # 执行当前业务步骤并推进后续处理
                "query_llm_provider": llm_result.provider,  # 执行当前业务步骤并推进后续处理
                "query_llm_detail": {**llm_result.detail, "parse_error": "LLM did not return valid JSON"},  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
        return fallback  # 返回当前分支整理好的结果
    # rewritten_query 缺失时回落到规则改写结果。
    rewritten_query = str(parsed.get("rewritten_query") or fallback.rewritten_query).strip()  # 更新当前逻辑中的 rewritten query
    # variants 只接受字符串列表，避免模型返回对象导致后续检索报错。
    raw_variants = parsed.get("variants") if isinstance(parsed.get("variants"), list) else []  # 更新当前逻辑中的 raw variants
    llm_variants = [str(item).strip() for item in raw_variants if str(item).strip()]  # 更新当前逻辑中的 llm variants
    # 合并 LLM 变体和规则变体，既利用模型泛化能力，也保留确定性同义词召回。
    query_variants = _dedupe_non_empty([rewritten_query, *llm_variants, *fallback.query_variants])[:max_variants]  # 更新当前逻辑中的 query variants
    # query_type 用于后续动态检索计划；非法值直接忽略。
    query_type = str(parsed.get("query_type") or "").strip()  # 更新当前逻辑中的 query type
    query_type_hint = query_type if query_type in VALID_QUERY_TYPES else fallback.query_type_hint  # 更新当前逻辑中的 query type hint
    # diagnostics 会出现在接口返回的 retrieval.profile 中，验收时能看到 LLM 是否参与了变体生成。
    diagnostics = {  # 更新当前逻辑中的 diagnostics
        **fallback.diagnostics,  # 填充返回或配置中的 字段 字段
        "query_llm_enabled": True,  # 填充返回或配置中的 query llm enabled 字段
        "query_llm_used": True,  # 填充返回或配置中的 query llm used 字段
        "query_llm_backend": backend,  # 填充返回或配置中的 query llm backend 字段
        "query_llm_provider": llm_result.provider,  # 填充返回或配置中的 query llm provider 字段
        "query_llm_detail": llm_result.detail,  # 填充返回或配置中的 query llm detail 字段
        "query_llm_type_hint": query_type_hint,  # 填充返回或配置中的 query llm type hint 字段
        "query_llm_reasons": parsed.get("reasons") if isinstance(parsed.get("reasons"), list) else [],  # 填充返回或配置中的 query llm reasons 字段
    }  # 结束 diagnostics 的定义或组装
    return QueryPreparationResult(  # 返回当前分支整理好的结果
        rewritten_query=rewritten_query,  # 设置 QueryPreparationResult 的 rewritten query
        query_variants=query_variants,  # 设置 QueryPreparationResult 的 query variants
        is_follow_up=fallback.is_follow_up,  # 设置 QueryPreparationResult 的 is follow up
        query_type_hint=query_type_hint,  # 设置 QueryPreparationResult 的 query type hint
        diagnostics=diagnostics,  # 设置 QueryPreparationResult 的 diagnostics
    )  # 结束 QueryPreparationResult 的定义或组装


def _prepare_query_by_rules(question: str, history: list[str] | None, *, max_variants: int) -> QueryPreparationResult:  # 定义业务处理函数 _prepare_query_by_rules
    # This is the deterministic local fallback path.
    # It keeps the MVP runnable even when there is no external LLM configured.
    """纯规则查询准备，作为无 Key、LLM 失败和离线演示时的稳定兜底。"""  # 函数文档字符串，说明 _prepare_query_by_rules 的职责

    # 先判断追问，再根据追问结果改写主查询。
    is_follow_up = needs_rewrite(question, history)  # 更新当前逻辑中的 is follow up
    # 追问改写可以让向量检索拿到更多上下文关键词。
    rewritten_query = rewrite_query_if_needed(question, history)  # 更新当前逻辑中的 rewritten query
    # 规则变体覆盖常见劳动社保同义词。
    variants = generate_query_variants(rewritten_query, max_variants=max_variants)  # 更新当前逻辑中的 variants
    # 规则模式不提供 query_type_hint，让 retrieval.py 使用关键词分类。
    return QueryPreparationResult(  # 返回当前分支整理好的结果
        rewritten_query=rewritten_query,  # 设置 QueryPreparationResult 的 rewritten query
        query_variants=variants,  # 设置 QueryPreparationResult 的 query variants
        is_follow_up=is_follow_up,  # 设置 QueryPreparationResult 的 is follow up
        query_type_hint=None,  # 设置 QueryPreparationResult 的 query type hint
        diagnostics={  # 设置 QueryPreparationResult 的 diagnostics
            "query_prepare_mode": "rule_fallback",  # 填充返回或配置中的 query prepare mode 字段
            "query_llm_enabled": False,  # 填充返回或配置中的 query llm enabled 字段
            "query_llm_used": False,  # 填充返回或配置中的 query llm used 字段
        },  # 结束 diagnostics 的定义或组装
    )  # 结束 QueryPreparationResult 的定义或组装


def _build_query_llm_prompt(*, question: str, history: list[str], max_variants: int) -> str:  # 定义业务处理函数 _build_query_llm_prompt
    # The prompt forces the model to act like a query planner instead of an answer generator.
    # It must return strict JSON so the backend can safely parse and use the result.
    """构造 LLM 查询规划 Prompt，要求输出可解析 JSON。"""  # 函数文档字符串，说明 _build_query_llm_prompt 的职责

    # 只取最近 3 条历史，避免把过长会话塞进轻量级查询规划请求。
    recent_history = history[-3:]  # 更新当前逻辑中的 recent history
    # JSON schema 写进提示词，降低模型输出散文的概率。
    return f"""请根据企业用工与社保合规问答场景，对用户问题做检索规划。  # 返回当前分支整理好的结果

输出必须是严格 JSON，字段如下：  # 执行当前业务步骤并推进后续处理
{{  # 执行当前业务步骤并推进后续处理
  "rewritten_query": "把追问补全后的独立检索问题",  # 执行当前业务步骤并推进后续处理
  "variants": ["查询变体1", "查询变体2"],  # 执行当前业务步骤并推进后续处理
  "query_type": "policy|procedure|dispute|faq_like|general|follow_up",  # 执行当前业务步骤并推进后续处理
  "reasons": ["为什么这样改写和分类"]  # 执行当前业务步骤并推进后续处理
}}  # 执行当前业务步骤并推进后续处理

要求：  # 执行当前业务步骤并推进后续处理
1. variants 最多 {max_variants} 条，必须围绕原问题，不要扩展到无关政策。  # 执行当前业务步骤并推进后续处理
2. query_type 中，policy 表示政策标准，procedure 表示办理流程/材料/地点，dispute 表示劳动争议/赔偿/解除/工伤风险，faq_like 表示高频问答，follow_up 表示追问。  # 执行当前业务步骤并推进后续处理
3. 不要编造答案，只做查询规划。  # 执行当前业务步骤并推进后续处理

最近历史：  # 执行当前业务步骤并推进后续处理
{json.dumps(recent_history, ensure_ascii=False)}  # 执行当前业务步骤并推进后续处理

用户问题：  # 执行当前业务步骤并推进后续处理
{question}  # 执行当前业务步骤并推进后续处理
"""  # 模块文档字符串，概述当前文件职责


def _parse_llm_json(text: str) -> dict[str, Any] | None:  # 定义业务处理函数 _parse_llm_json
    # Models sometimes wrap JSON in markdown fences or add extra explanation.
    # This parser tries to recover the first valid JSON object without breaking the main pipeline.
    """解析 LLM 返回的 JSON，兼容模型偶尔包一层 ```json 的情况。"""  # 函数文档字符串，说明 _parse_llm_json 的职责

    # 去掉 Markdown 代码块标记。
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()  # 更新当前逻辑中的 cleaned
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        data = json.loads(cleaned)  # 整理当前接口最终要返回的数据结构
    except json.JSONDecodeError:  # 捕获异常并执行降级或错误处理逻辑
        # 如果模型在 JSON 前后夹了少量说明，尝试截取第一个对象。
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)  # 更新当前逻辑中的 match
        if not match:  # 根据当前条件决定是否进入对应业务分支
            return None  # 返回当前分支整理好的结果
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            data = json.loads(match.group(0))  # 整理当前接口最终要返回的数据结构
        except json.JSONDecodeError:  # 捕获异常并执行降级或错误处理逻辑
            return None  # 返回当前分支整理好的结果
    # 只接受对象，列表或字符串都视为无效规划。
    return data if isinstance(data, dict) else None  # 返回当前分支整理好的结果


def _dedupe_non_empty(items: list[str]) -> list[str]:  # 定义业务处理函数 _dedupe_non_empty
    """去重并过滤空字符串，保持原有顺序。"""  # 函数文档字符串，说明 _dedupe_non_empty 的职责

    # seen 用于记录已经保留过的查询文本。
    seen: set[str] = set()  # 更新当前逻辑中的 seen
    # result 保存最终有序结果。
    result: list[str] = []  # 更新当前逻辑中的 result
    for item in items:  # 遍历当前集合中的每一项并逐个处理
        # 统一去掉首尾空白，减少重复变体。
        normalized = item.strip()  # 初始化当前导出行的标准化结果字典
        if normalized and normalized not in seen:  # 根据当前条件决定是否进入对应业务分支
            seen.add(normalized)  # 执行当前业务步骤并推进后续处理
            result.append(normalized)  # 执行当前业务步骤并推进后续处理
    return result  # 返回当前分支整理好的结果


def _env_int(name: str, default: int) -> int:  # 定义业务处理函数 _env_int
    """读取整数环境变量，配置错误时使用默认值。"""  # 函数文档字符串，说明 _env_int 的职责

    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        return max(1, int(os.getenv(name, str(default))))  # 返回当前分支整理好的结果
    except ValueError:  # 捕获异常并执行降级或错误处理逻辑
        return default  # 返回当前分支整理好的结果


def _env_float(name: str, default: float) -> float:  # 定义业务处理函数 _env_float
    """读取浮点环境变量，配置错误时使用默认值。"""  # 函数文档字符串，说明 _env_float 的职责

    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        return float(os.getenv(name, str(default)))  # 返回当前分支整理好的结果
    except ValueError:  # 捕获异常并执行降级或错误处理逻辑
        return default  # 返回当前分支整理好的结果
