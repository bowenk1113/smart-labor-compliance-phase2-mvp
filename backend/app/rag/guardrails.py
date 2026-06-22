"""多路由与安全边界检测。

本模块负责把无需检索的问题提前拦截掉，降低大模型费用，并防止明显越界、违法或不适合回答的内容进入 RAG 链路。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import re  # 导入当前模块运行所依赖的工具或类型
from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型

from app.rag.scenarios import SCENARIOS, get_scenario, infer_scenario_id  # 导入二期 RAG 检索与问答服务组件


IDENTITY_ANSWER = "我是企业用工与社保合规智能平台的二期 RAG 助手，可以基于已配置知识库回答社保医保、用工合规、假期福利和劳动争议办事问题。"  # 更新当前逻辑中的 IDENTITY ANSWER
REFUSAL_ANSWER = "抱歉，这类内容不属于企业用工与社保合规咨询范围，我不能提供相关回答。请改问社保、用工、假期或劳动争议办事相关问题。"  # 更新当前逻辑中的 REFUSAL ANSWER


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RouteDecision:  # 定义业务类 RouteDecision
    """路由判断结果。"""  # 类文档字符串，概述 RouteDecision 的用途

    route: str  # 执行当前业务步骤并推进后续处理
    answer: str | None = None  # 更新当前逻辑中的 回答内容
    inferred_scenario_id: str | None = None  # 更新当前逻辑中的 inferred scenario id


def classify_direct_route(question: str) -> RouteDecision | None:  # 定义业务处理函数 classify_direct_route
    """识别固定直出路由。"""  # 函数文档字符串，说明 classify_direct_route 的职责

    text = (question or "").strip()  # 把文件字节内容解码成可解析的文本
    lowered = text.lower()  # 更新当前逻辑中的 lowered
    if lowered in {"hi", "hello", "你好", "您好", "在吗"}:  # 根据当前条件决定是否进入对应业务分支
        return RouteDecision("direct_answer", "您好，我可以帮您查询企业用工、社保医保、假期福利和劳动争议办事相关问题。")  # 返回当前分支整理好的结果
    if any(item in text for item in ("你是谁", "你是什么", "介绍一下你", "你的身份")):  # 根据当前条件决定是否进入对应业务分支
        return RouteDecision("direct_answer", IDENTITY_ANSWER)  # 返回当前分支整理好的结果
    if any(item in text for item in ("谢谢", "感谢", "辛苦了")):  # 根据当前条件决定是否进入对应业务分支
        return RouteDecision("direct_answer", "不客气。您可以继续提问，我会优先基于当前场景知识库回答。")  # 返回当前分支整理好的结果
    if any(item in text for item in ("转人工", "人工客服", "人工处理")):  # 根据当前条件决定是否进入对应业务分支
        return RouteDecision("direct_answer", "可以，请联系 HR、法务或企业服务台进行人工复核；涉及争议、金额和期限的问题建议保留书面材料。")  # 返回当前分支整理好的结果
    if _contains_illegal_or_adult_content(text):  # 根据当前条件决定是否进入对应业务分支
        return RouteDecision("direct_answer", REFUSAL_ANSWER)  # 返回当前分支整理好的结果
    if text and not _looks_like_supported_domain(text):  # 根据当前条件决定是否进入对应业务分支
        return RouteDecision("direct_answer", "当前平台仅支持企业用工、社保医保、假期福利和劳动争议办事问题。请切换到匹配场景后重新提问。")  # 返回当前分支整理好的结果
    return None  # 返回当前分支整理好的结果


def detect_scene_boundary(question: str, selected_scenario_id: str | None) -> RouteDecision | None:  # 定义业务处理函数 detect_scene_boundary
    """检测问题是否明显属于另一个内部场景。"""  # 函数文档字符串，说明 detect_scene_boundary 的职责

    selected = get_scenario(selected_scenario_id)  # 更新当前逻辑中的 selected
    inferred_id, score = infer_scenario_id(question)  # 执行当前业务步骤并推进后续处理
    if not inferred_id or inferred_id == selected.scenario_id or score < 3:  # 根据当前条件决定是否进入对应业务分支
        return None  # 返回当前分支整理好的结果
    inferred = SCENARIOS[inferred_id]  # 更新当前逻辑中的 inferred
    return RouteDecision(  # 返回当前分支整理好的结果
        route="scene_boundary",  # 设置 RouteDecision 的 route
        inferred_scenario_id=inferred_id,  # 设置 RouteDecision 的 inferred scenario id
        answer=f"这个问题更像属于“{inferred.label}”场景。当前选择的是“{selected.label}”，为避免误检索，请先切换场景后再提问。",  # 设置 RouteDecision 的 回答内容
    )  # 结束 RouteDecision 的定义或组装


def _contains_illegal_or_adult_content(text: str) -> bool:  # 定义业务处理函数 _contains_illegal_or_adult_content
    """用保守关键词识别非法、色情、暴力等固定拒答内容。"""  # 函数文档字符串，说明 _contains_illegal_or_adult_content 的职责

    patterns = (  # 更新当前逻辑中的 patterns
        r"色情|裸聊|黄色|成人视频",  # 执行当前业务步骤并推进后续处理
        r"杀人|爆炸物|制毒|毒品|枪支|勒索|诈骗教程",  # 执行当前业务步骤并推进后续处理
        r"绕过监管|逃避执法|伪造证件|伪造公章",  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)  # 返回当前分支整理好的结果


def _looks_like_supported_domain(text: str) -> bool:  # 定义业务处理函数 _looks_like_supported_domain
    """判断问题是否至少与平台业务域有弱相关。"""  # 函数文档字符串，说明 _looks_like_supported_domain 的职责

    if len(text) <= 3:  # 根据当前条件决定是否进入对应业务分支
        return True  # 返回当前分支整理好的结果
    domain_words = set()  # 更新当前逻辑中的 domain words
    for scenario in SCENARIOS.values():  # 遍历当前集合中的每一项并逐个处理
        domain_words.update(scenario.keywords)  # 执行当前业务步骤并推进后续处理
    domain_words.update(("公司", "员工", "企业", "HR", "人事", "政策", "办理", "合规", "劳动", "陕西", "西安"))  # 执行当前业务步骤并推进后续处理
    return any(word in text for word in domain_words)  # 返回当前分支整理好的结果

