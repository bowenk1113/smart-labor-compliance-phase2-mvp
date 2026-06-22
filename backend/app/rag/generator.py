"""RAG 生成层。

本模块负责完整 RAG 链路中的 G：Generation。
检索层只负责找证据，生成层负责把用户问题、业务场景和检索上下文组装成 Prompt，
再调用 Dify 或 OpenAI-compatible Chat API 生成最终答案。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import os  # 导入当前模块运行所依赖的工具或类型
from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型
from typing import Any  # 导入当前模块运行所依赖的工具或类型

import requests  # 导入 HTTP 客户端，调用外部 Dify 或 RAGFlow 服务

from app.database import settings  # 导入数据库依赖与全局运行配置
from app.rag.pipeline_schema import RAGQueryContext  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import RetrievalHit  # 导入二期 RAG 检索与问答服务组件


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class GenerationResult:  # 定义业务类 GenerationResult
    """大模型生成结果。"""  # 类文档字符串，概述 GenerationResult 的用途

    # answer 是模型返回的最终正文。
    answer: str  # 执行当前业务步骤并推进后续处理
    # provider 标记本次答案来自哪个生成后端。
    provider: str  # 执行当前业务步骤并推进后续处理
    # backend 是配置层面的生成后端，例如 dify/openai_compatible/template。
    backend: str  # 执行当前业务步骤并推进后续处理
    # used_llm 表示是否真的调用了大模型。
    used_llm: bool  # 执行当前业务步骤并推进后续处理
    # detail 保存调用状态、模型名或跳过原因，便于前端/验收排错。
    detail: dict[str, Any]  # 执行当前业务步骤并推进后续处理


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class LLMTextResult:  # 定义业务类 LLMTextResult
    """通用大模型文本调用结果。

    这个结果不只给最终答案使用，也给“查询改写、问题变体、检索计划辅助”等轻量 LLM 能力使用。
    """

    # text 是模型返回的原始文本，调用方可以继续解析 JSON 或直接使用。
    text: str  # 执行当前业务步骤并推进后续处理
    # provider 标记文本来自哪个模型后端。
    provider: str  # 执行当前业务步骤并推进后续处理
    # backend 标记底层协议，目前是 openai_compatible。
    backend: str  # 执行当前业务步骤并推进后续处理
    # used_llm 表示本次是否真的调用了大模型。
    used_llm: bool  # 执行当前业务步骤并推进后续处理
    # detail 保存状态、模型名、失败原因等诊断信息。
    detail: dict[str, Any]  # 执行当前业务步骤并推进后续处理


def generation_backend() -> str:  # 定义业务处理函数 generation_backend
    """读取生成后端配置。"""  # 函数文档字符串，说明 generation_backend 的职责

    # auto 表示自动选择：优先 Dify，其次 OpenAI-compatible，最后模板兜底。
    return os.getenv("PHASE2_GENERATION_BACKEND", "auto").strip().lower() or "auto"  # 返回当前分支整理好的结果


def openai_compatible_chat(  # 定义业务处理函数 openai_compatible_chat
    *,  # 以下参数改为关键字传参，避免调用位置出错
    system_prompt: str,  # 声明参数 system_prompt，供当前逻辑使用
    user_prompt: str,  # 声明参数 user_prompt，供当前逻辑使用
    purpose: str,  # 声明参数 purpose，供当前逻辑使用
    temperature: float | None = None,  # 声明参数 temperature，供当前逻辑使用
) -> LLMTextResult:  # 结束 openai_compatible_chat 的参数声明
    """调用 OpenAI-compatible Chat Completions，供答案整理和查询变体共用。

    这里不写死 OpenAI 官方服务，只要求目标服务兼容 `/v1/chat/completions` 协议。
    因此它既可以接 OpenAI，也可以接本地模型网关或企业内部大模型网关。
    """

    # 如果没有配置 API Key，直接返回 skipped，让调用方走规则或模板兜底。
    api_key = os.getenv("PHASE2_LLM_API_KEY", "")  # 更新当前逻辑中的 api key
    if not api_key:  # 根据当前条件决定是否进入对应业务分支
        return LLMTextResult(  # 返回当前分支整理好的结果
            text="",  # 设置 LLMTextResult 的 text
            provider="phase2_llm_unconfigured",  # 设置 LLMTextResult 的 服务提供方
            backend="openai_compatible",  # 设置 LLMTextResult 的 backend
            used_llm=False,  # 设置 LLMTextResult 的 used llm
            detail={"status": "skipped", "reason": "PHASE2_LLM_API_KEY is empty", "purpose": purpose},  # 设置 LLMTextResult 的 状态
        )  # 结束 LLMTextResult 的定义或组装
    # 兼容接口地址，例如 https://api.openai.com/v1 或 http://127.0.0.1:11434/v1。
    base_url = os.getenv("PHASE2_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")  # 更新当前逻辑中的 base url
    # 模型名由环境变量配置，便于替换成企业可用模型。
    model = os.getenv("PHASE2_LLM_MODEL", "gpt-4o-mini")  # 更新当前逻辑中的 model
    # 查询扩展可单独设置 temperature；不传时使用统一默认值。
    final_temperature = temperature if temperature is not None else float(os.getenv("PHASE2_LLM_TEMPERATURE", "0.2"))  # 更新当前逻辑中的 final temperature
    # Chat Completions 标准请求体。
    payload = {  # 组装发往外部问答服务的请求载荷
        "model": model,  # 向 Dify 请求体写入 model
        "messages": [  # 向 Dify 请求体写入 messages
            {"role": "system", "content": system_prompt},  # 向 Dify 请求体写入 role
            {"role": "user", "content": user_prompt},  # 向 Dify 请求体写入 role
        ],  # 向 Dify 请求体写入 字段
        "temperature": final_temperature,  # 向 Dify 请求体写入 temperature
    }  # 结束 payload 的定义或组装
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        # 发送 OpenAI-compatible 请求。
        response = requests.post(  # 保存当前分支生成的响应对象
            f"{base_url}/chat/completions",  # 设置 post 的 字段
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},  # 设置 post 的 Authorization
            json=payload,  # 设置 post 的 json
            timeout=int(os.getenv("PHASE2_LLM_TIMEOUT_SECONDS", "30")),  # 设置 post 的 timeout
        )  # 结束 post 的定义或组装
        # 非 2xx 说明模型网关调用失败，返回诊断信息并让上层兜底。
        if response.status_code >= 400:  # 根据状态参数决定是否追加筛选条件
            return LLMTextResult(  # 返回当前分支整理好的结果
                text="",  # 设置 LLMTextResult 的 text
                provider="phase2_llm_failed",  # 设置 LLMTextResult 的 服务提供方
                backend="openai_compatible",  # 设置 LLMTextResult 的 backend
                used_llm=False,  # 设置 LLMTextResult 的 used llm
                detail={"status": "failed", "status_code": response.status_code, "body": response.text[:500], "purpose": purpose},  # 设置 LLMTextResult 的 状态
            )  # 结束 LLMTextResult 的定义或组装
        # 解析标准 choices[0].message.content。
        data = response.json()  # 整理当前接口最终要返回的数据结构
        choices = data.get("choices") or []  # 更新当前逻辑中的 choices
        text = str(((choices[0] or {}).get("message") or {}).get("content") or "").strip() if choices else ""  # 把文件字节内容解码成可解析的文本
        return LLMTextResult(  # 返回当前分支整理好的结果
            text=text,  # 设置 LLMTextResult 的 text
            provider="phase2_openai_compatible",  # 设置 LLMTextResult 的 服务提供方
            backend="openai_compatible",  # 设置 LLMTextResult 的 backend
            used_llm=bool(text),  # 设置 LLMTextResult 的 used llm
            detail={"status": "ok" if text else "empty_answer", "model": model, "purpose": purpose},  # 设置 LLMTextResult 的 状态
        )  # 结束 LLMTextResult 的定义或组装
    except requests.RequestException as exc:  # 捕获异常并执行降级或错误处理逻辑
        # 网络异常、超时、连接失败都进入可诊断失败结果。
        return LLMTextResult(  # 返回当前分支整理好的结果
            text="",  # 设置 LLMTextResult 的 text
            provider="phase2_llm_failed",  # 设置 LLMTextResult 的 服务提供方
            backend="openai_compatible",  # 设置 LLMTextResult 的 backend
            used_llm=False,  # 设置 LLMTextResult 的 used llm
            detail={"status": "failed", "error": str(exc), "model": model, "purpose": purpose},  # 设置 LLMTextResult 的 状态
        )  # 结束 LLMTextResult 的定义或组装


def build_rag_prompt(*, context: RAGQueryContext, context_text: str) -> str:  # 定义业务处理函数 build_rag_prompt
    """构建完整 RAG Prompt。"""  # 函数文档字符串，说明 build_rag_prompt 的职责

    # Prompt 里明确要求模型只能基于检索上下文回答，避免脱离证据编造。
    return f"""你是企业用工与社保合规智能问答助手。  # 返回当前分支整理好的结果

请严格基于【检索上下文】回答【用户问题】。  # 执行当前业务步骤并推进后续处理
如果检索上下文没有足够依据，请明确说明信息不足，不要编造。  # 执行当前业务步骤并推进后续处理
回答要结论先行、分点说明、保留风险提示，并提醒以当地官方经办口径和企业制度复核。  # 执行当前业务步骤并推进后续处理

【当前场景】  # 执行当前业务步骤并推进后续处理
{context.scenario.label}  # 执行当前业务步骤并推进后续处理

【适用角色】  # 执行当前业务步骤并推进后续处理
{context.user_role}  # 执行当前业务步骤并推进后续处理

【地区】  # 执行当前业务步骤并推进后续处理
{context.data_scope.province}{context.data_scope.city}  # 执行当前业务步骤并推进后续处理

【用户问题】  # 执行当前业务步骤并推进后续处理
{context.query}  # 执行当前业务步骤并推进后续处理

【检索上下文】  # 执行当前业务步骤并推进后续处理
{context_text}  # 执行当前业务步骤并推进后续处理

【输出要求】  # 执行当前业务步骤并推进后续处理
1. 先给直接结论。  # 执行当前业务步骤并推进后续处理
2. 再说明依据和处理建议。  # 执行当前业务步骤并推进后续处理
3. 如涉及金额、期限、待遇、解除、仲裁、工伤或社保缴纳，标注风险点。  # 执行当前业务步骤并推进后续处理
4. 不要输出与上下文无关的政策口径。  # 执行当前业务步骤并推进后续处理
"""  # 模块文档字符串，概述当前文件职责


def generate_with_model(*, context: RAGQueryContext, prompt: str) -> GenerationResult:  # 定义业务处理函数 generate_with_model
    """按配置调用大模型生成答案。"""  # 函数文档字符串，说明 generate_with_model 的职责

    # 读取生成后端。
    backend = generation_backend()  # 更新当前逻辑中的 backend
    # auto 模式下，如果 Dify 配了 Key，优先走 Dify。
    if backend in {"auto", "dify"} and settings.dify_api_key:  # 根据当前条件决定是否进入对应业务分支
        return _generate_with_dify(context=context, prompt=prompt)  # 返回当前分支整理好的结果
    # auto 模式下，如果配置了 OpenAI-compatible Key，走兼容接口。
    if backend in {"auto", "openai", "openai_compatible"} and os.getenv("PHASE2_LLM_API_KEY"):  # 根据当前条件决定是否进入对应业务分支
        return _generate_with_openai_compatible(context=context, prompt=prompt)  # 返回当前分支整理好的结果
    # 显式要求 Dify 但没有 Key 时，不静默假装调用成功。
    if backend == "dify":  # 根据当前条件决定是否进入对应业务分支
        return GenerationResult(  # 返回当前分支整理好的结果
            answer="",  # 设置 GenerationResult 的 回答内容
            provider="phase2_dify_unconfigured",  # 设置 GenerationResult 的 服务提供方
            backend="dify",  # 设置 GenerationResult 的 backend
            used_llm=False,  # 设置 GenerationResult 的 used llm
            detail={"status": "skipped", "reason": "DIFY_API_KEY is empty"},  # 设置 GenerationResult 的 状态
        )  # 结束 GenerationResult 的定义或组装
    # 显式要求 OpenAI-compatible 但没有 Key 时，也返回可诊断原因。
    if backend in {"openai", "openai_compatible"}:  # 根据当前条件决定是否进入对应业务分支
        return GenerationResult(  # 返回当前分支整理好的结果
            answer="",  # 设置 GenerationResult 的 回答内容
            provider="phase2_llm_unconfigured",  # 设置 GenerationResult 的 服务提供方
            backend="openai_compatible",  # 设置 GenerationResult 的 backend
            used_llm=False,  # 设置 GenerationResult 的 used llm
            detail={"status": "skipped", "reason": "PHASE2_LLM_API_KEY is empty"},  # 设置 GenerationResult 的 状态
        )  # 结束 GenerationResult 的定义或组装
    # auto 且没有任何大模型配置时，告知 Pipeline 使用模板兜底。
    return GenerationResult(  # 返回当前分支整理好的结果
        answer="",  # 设置 GenerationResult 的 回答内容
        provider="phase2_template_fallback",  # 设置 GenerationResult 的 服务提供方
        backend="template",  # 设置 GenerationResult 的 backend
        used_llm=False,  # 设置 GenerationResult 的 used llm
        detail={"status": "skipped", "reason": "no generation backend configured"},  # 设置 GenerationResult 的 状态
    )  # 结束 GenerationResult 的定义或组装


def template_answer(*, question: str, scenario_label: str, hits: list[RetrievalHit]) -> str:  # 定义业务处理函数 template_answer
    """没有大模型配置时的模板兜底答案。"""  # 函数文档字符串，说明 template_answer 的职责

    # 无上下文时返回信息不足，不让系统编造答案。
    if not hits:  # 根据当前条件决定是否进入对应业务分支
        return f"当前“{scenario_label}”知识库没有检索到足够依据。建议补充地区、时间、员工身份或办理事项后再查询。"  # 返回当前分支整理好的结果
    # 从前 3 条命中中抽取片段，形成可解释的答案。
    bullets = []  # 更新当前逻辑中的 bullets
    # enumerate 用来生成 1、2、3 这样的序号。
    for index, hit in enumerate(hits[:3], start=1):  # 遍历当前集合中的每一项并逐个处理
        # 把换行压成空格，让答案展示更紧凑。
        snippet = hit.document.content.replace("\n", " ").strip()  # 更新当前逻辑中的 snippet
        # 只截取前 260 个字符，避免单条来源过长。
        bullets.append(f"{index}. {snippet[:260]}")  # 执行当前业务步骤并推进后续处理
    # 模板答案用于没有 Dify/LLM Key 时保持系统可用。
    return (  # 返回当前分支整理好的结果
        f"根据“{scenario_label}”知识库，建议按以下口径处理：\n"  # 设置 return 的 字段
        + "\n".join(bullets)  # 设置 return 的 字段
        + "\n\n如果这是个案处理，请补充发生时间、工作地点、员工类型和已有材料，系统可继续缩小检索范围。"  # 设置 return 的 字段
    )  # 结束 return 的定义或组装


def _generate_with_dify(*, context: RAGQueryContext, prompt: str) -> GenerationResult:  # 定义业务处理函数 _generate_with_dify
    """调用 Dify blocking chat-messages 生成 RAG 答案。"""  # 函数文档字符串，说明 _generate_with_dify 的职责

    # Dify 的 Chat Messages API 地址。
    url = f"{settings.dify_base_url.rstrip('/')}/chat-messages"  # 更新当前逻辑中的 链接地址
    # Dify 请求体；这里把检索后的完整 Prompt 作为 query 发送。
    payload = {  # 组装发往外部问答服务的请求载荷
        "query": prompt,  # 向 Dify 请求体写入 query
        "user": context.session_id or "phase2-rag-user",  # 向 Dify 请求体写入 user
        "response_mode": "blocking",  # 向 Dify 请求体写入 response mode
        "inputs": {  # 向 Dify 请求体写入 inputs
            "scenario_id": context.scenario.scenario_id,  # 向 Dify 请求体写入 scenario id
            "scenario_label": context.scenario.label,  # 向 Dify 请求体写入 scenario label
            "user_role": context.user_role,  # 向 Dify 请求体写入 user role
            "province": context.data_scope.province,  # 向 Dify 请求体写入 province
            "city": context.data_scope.city,  # 向 Dify 请求体写入 city
        },  # 结束 payload 的定义或组装
    }  # 结束 payload 的定义或组装
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        # 发送 Dify 请求。
        response = requests.post(  # 保存当前分支生成的响应对象
            url,  # 设置 post 的 字段
            headers={"Authorization": f"Bearer {settings.dify_api_key}", "Content-Type": "application/json"},  # 设置 post 的 Authorization
            json=payload,  # 设置 post 的 json
            timeout=settings.dify_timeout_seconds,  # 设置 post 的 timeout
        )  # 结束 post 的定义或组装
        # 非 2xx 视为调用失败，返回给 Pipeline 做模板兜底。
        if response.status_code >= 400:  # 根据状态参数决定是否追加筛选条件
            return GenerationResult(  # 返回当前分支整理好的结果
                answer="",  # 设置 GenerationResult 的 回答内容
                provider="phase2_dify_failed",  # 设置 GenerationResult 的 服务提供方
                backend="dify",  # 设置 GenerationResult 的 backend
                used_llm=False,  # 设置 GenerationResult 的 used llm
                detail={"status": "failed", "status_code": response.status_code, "body": response.text[:500]},  # 设置 GenerationResult 的 状态
            )  # 结束 GenerationResult 的定义或组装
        # 解析 Dify JSON 响应。
        data = response.json()  # 整理当前接口最终要返回的数据结构
        # blocking 模式下通常从 answer 字段读取答案。
        answer = str(data.get("answer") or "").strip()  # 更新当前逻辑中的 回答内容
        return GenerationResult(  # 返回当前分支整理好的结果
            answer=answer,  # 设置 GenerationResult 的 回答内容
            provider="phase2_dify_rag",  # 设置 GenerationResult 的 服务提供方
            backend="dify",  # 设置 GenerationResult 的 backend
            used_llm=bool(answer),  # 设置 GenerationResult 的 used llm
            detail={  # 设置 GenerationResult 的 detail
                "status": "ok" if answer else "empty_answer",  # 填充返回或配置中的 状态 字段
                "conversation_id": data.get("conversation_id"),  # 填充返回或配置中的 会话 ID 字段
                "message_id": data.get("message_id"),  # 填充返回或配置中的 message id 字段
            },  # 结束 detail 的定义或组装
        )  # 结束 GenerationResult 的定义或组装
    except requests.RequestException as exc:  # 捕获异常并执行降级或错误处理逻辑
        # 网络错误、超时、连接失败都进入可诊断失败结果。
        return GenerationResult(  # 返回当前分支整理好的结果
            answer="",  # 设置 GenerationResult 的 回答内容
            provider="phase2_dify_failed",  # 设置 GenerationResult 的 服务提供方
            backend="dify",  # 设置 GenerationResult 的 backend
            used_llm=False,  # 设置 GenerationResult 的 used llm
            detail={"status": "failed", "error": str(exc)},  # 设置 GenerationResult 的 状态
        )  # 结束 GenerationResult 的定义或组装


def _generate_with_openai_compatible(*, context: RAGQueryContext, prompt: str) -> GenerationResult:  # 定义业务处理函数 _generate_with_openai_compatible
    """调用 OpenAI-compatible Chat Completions 接口。"""  # 函数文档字符串，说明 _generate_with_openai_compatible 的职责

    # 最终答案整理也复用通用模型调用函数，避免查询变体和答案生成各写一套 HTTP 逻辑。
    result = openai_compatible_chat(  # 更新当前逻辑中的 result
        system_prompt="你是企业用工与社保合规 RAG 助手，只能基于检索上下文回答。",  # 设置 openai_compatible_chat 的 system prompt
        user_prompt=prompt,  # 设置 openai_compatible_chat 的 user prompt
        purpose="rag_answer_generation",  # 设置 openai_compatible_chat 的 purpose
    )  # 结束 openai_compatible_chat 的定义或组装
    return GenerationResult(  # 返回当前分支整理好的结果
        answer=result.text,  # 设置 GenerationResult 的 回答内容
        provider="phase2_openai_compatible_rag" if result.used_llm else result.provider,  # 设置 GenerationResult 的 服务提供方
        backend=result.backend,  # 设置 GenerationResult 的 backend
        used_llm=result.used_llm,  # 设置 GenerationResult 的 used llm
        detail=result.detail,  # 设置 GenerationResult 的 detail
    )  # 结束 GenerationResult 的定义或组装
