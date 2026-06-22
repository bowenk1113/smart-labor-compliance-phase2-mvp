"""查询路由决策。

本模块对应流程图 5「查询路由」。它把问候、身份、非法拒答、
业务越界和内部场景边界放在检索之前处理，从而节省向量库和大模型资源。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型

from app.rag.guardrails import RouteDecision, classify_direct_route, detect_scene_boundary  # 导入二期 RAG 检索与问答服务组件
from app.rag.pipeline_schema import RAGQueryContext  # 导入二期 RAG 检索与问答服务组件


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class QueryRoute:  # 定义业务类 QueryRoute
    """Pipeline 内部使用的路由结果。"""  # 类文档字符串，概述 QueryRoute 的用途

    # 路由名称。
    route: str  # 执行当前业务步骤并推进后续处理
    # 需要直出的固定答案；为空时继续进入检索。
    answer: str | None = None  # 更新当前逻辑中的 回答内容
    # 路由提供者，用于响应中的 provider 字段。
    provider: str = "phase2_router"  # 更新当前逻辑中的 服务提供方
    # 风险等级。
    risk_level: str = "medium"  # 更新当前逻辑中的 风险等级
    # 推断出的目标场景。
    inferred_scenario_id: str | None = None  # 更新当前逻辑中的 inferred scenario id


def decide_route(context: RAGQueryContext) -> QueryRoute:  # 定义业务处理函数 decide_route
    # This is the pre-retrieval router.
    # It decides whether the request should be answered directly, refused, blocked by scene boundary, or sent into RAG.
    """执行 direct_answer、source_boundary、faq/retrieval 的路由判断。"""  # 函数文档字符串，说明 decide_route 的职责

    # 第一层先识别问候、身份、感谢、转人工、非法和明显业务越界。
    direct = classify_direct_route(context.query)  # 更新当前逻辑中的 direct
    if direct:  # 根据当前条件决定是否进入对应业务分支
        return _from_guardrail(direct, provider="phase2_router", risk_level="low")  # 返回当前分支整理好的结果
    # 第二层检测用户问题是否明显属于另一个内部场景。
    boundary = detect_scene_boundary(context.query, context.scenario.scenario_id)  # 更新当前逻辑中的 boundary
    if boundary:  # 根据当前条件决定是否进入对应业务分支
        return _from_guardrail(boundary, provider="phase2_boundary", risk_level="medium")  # 返回当前分支整理好的结果
    # 未被拦截的问题进入 FAQ 和文档 RAG 检索链路。
    return QueryRoute(route="retrieval", provider="phase2_pipeline", risk_level="medium")  # 返回当前分支整理好的结果


def _from_guardrail(decision: RouteDecision, *, provider: str, risk_level: str) -> QueryRoute:  # 定义业务处理函数 _from_guardrail
    """把 guardrails.py 的 RouteDecision 转换为 Pipeline 路由对象。"""  # 函数文档字符串，说明 _from_guardrail 的职责

    return QueryRoute(  # 返回当前分支整理好的结果
        route=decision.route,  # 设置 QueryRoute 的 route
        answer=decision.answer,  # 设置 QueryRoute 的 回答内容
        provider=provider,  # 设置 QueryRoute 的 服务提供方
        risk_level=risk_level,  # 设置 QueryRoute 的 风险等级
        inferred_scenario_id=decision.inferred_scenario_id,  # 设置 QueryRoute 的 inferred scenario id
    )  # 结束 QueryRoute 的定义或组装
