"""核心 RAG Pipeline 的数据结构。

本文件专门对应流程图中的数据对象节点，例如 RAGQueryContext、
RetrievalPreparation 和 RetrievalResult。把这些对象单独定义出来，
可以让初学者先理解数据如何流动，再阅读具体的检索和生成逻辑。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

from dataclasses import dataclass, field  # 导入当前模块运行所依赖的工具或类型
from typing import Any  # 导入当前模块运行所依赖的工具或类型

from app.rag.scenarios import Scenario  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import RetrievalHit  # 导入二期 RAG 检索与问答服务组件


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class DataScope:  # 定义业务类 DataScope
    """流程图 17「场景/数据域」的数据隔离范围。"""  # 类文档字符串，概述 DataScope 的用途

    # tenant_id 用于多租户隔离；MVP 默认只有 default 租户。
    tenant_id: str = "default"  # 更新当前逻辑中的 租户 ID
    # roles 表示调用者角色；后续可用于 HR、员工、管理员的可见范围控制。
    roles: tuple[str, ...] = ("employee",)  # 更新当前逻辑中的 ]
    # visibility 表示知识可见性；MVP 默认读取 public 知识。
    visibility: str = "public"  # 更新当前逻辑中的 visibility
    # province 记录地区口径；劳动社保问题通常强依赖地区。
    province: str = "陕西省"  # 更新当前逻辑中的 省份
    # city 记录城市口径；MVP 默认西安市。
    city: str = "西安市"  # 更新当前逻辑中的 城市


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RAGQueryContext:  # 定义业务类 RAGQueryContext
    """流程图 4「请求上下文」的统一上下文对象。"""  # 类文档字符串，概述 RAGQueryContext 的用途

    # 用户原始问题。
    query: str  # 执行当前业务步骤并推进后续处理
    # 前端选择的内部业务场景。
    scenario: Scenario  # 执行当前业务步骤并推进后续处理
    # 会话 ID，供历史追问和日志串联使用。
    session_id: str | None  # 执行当前业务步骤并推进后续处理
    # 最近历史，供追问改写使用。
    history: list[str]  # 执行当前业务步骤并推进后续处理
    # 用户角色。
    user_role: str  # 执行当前业务步骤并推进后续处理
    # 数据域隔离信息。
    data_scope: DataScope  # 执行当前业务步骤并推进后续处理
    # 请求来源过滤条件；MVP 暂时由场景和 source_type 共同表达。
    source_filter: dict[str, Any] = field(default_factory=dict)  # 更新当前逻辑中的 source filter


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RAGEvent:  # 定义业务类 RAGEvent
    """Pipeline 事件，方便前端或日志展示每个阶段发生了什么。"""  # 类文档字符串，概述 RAGEvent 的用途

    # 事件名，例如 start、route_decided、faq_searched。
    name: str  # 执行当前业务步骤并推进后续处理
    # 事件携带的轻量数据。
    payload: dict[str, Any] = field(default_factory=dict)  # 更新当前逻辑中的 payload


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RetrievalPlan:  # 定义业务类 RetrievalPlan
    """流程图 7「参数包」中的检索计划。"""  # 类文档字符串，概述 RetrievalPlan 的用途

    # 计划名称，用于诊断和验收，例如 faq_first、broad_policy、high_risk_dispute。
    plan_name: str = "faq_first"  # 更新当前逻辑中的 plan name
    # 问题类型，用于解释为什么采用该计划，例如 faq_like、policy、procedure、dispute、follow_up。
    query_type: str = "general"  # 更新当前逻辑中的 query type
    # FAQ 召回数量。
    faq_top_k: int = 5  # 更新当前逻辑中的 faq top k
    # 文档召回数量。
    doc_top_k: int = 6  # 更新当前逻辑中的 doc top k
    # FAQ 高置信直出阈值。
    faq_direct_threshold: float = 0.58  # 更新当前逻辑中的 faq direct threshold
    # 进入上下文的最低相关性分数。
    min_context_score: float = 0.18  # 更新当前逻辑中的 min context score
    # 最大上下文条数。
    max_context_docs: int = 5  # 更新当前逻辑中的 max context docs
    # 是否启用二阶段重排。
    enable_rerank: bool = True  # 更新当前逻辑中的 enable rerank
    # 计划生成原因，便于前端或验收看到动态计划的决策依据。
    reasons: tuple[str, ...] = ()  # 更新当前逻辑中的 ]


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RetrievalPreparation:  # 定义业务类 RetrievalPreparation
    """流程图 6/7「检索准备」产出的完整参数包。"""  # 类文档字符串，概述 RetrievalPreparation 的用途

    # 追问改写后的独立查询。
    rewritten_query: str  # 执行当前业务步骤并推进后续处理
    # 多路召回查询变体。
    query_variants: list[str]  # 执行当前业务步骤并推进后续处理
    # 意图标签，MVP 用场景和关键词粗粒度表达。
    intent: str  # 执行当前业务步骤并推进后续处理
    # 检索计划。
    plan: RetrievalPlan  # 执行当前业务步骤并推进后续处理
    # 检索画像，记录后端、地区和角色等信息。
    profile: dict[str, Any]  # 执行当前业务步骤并推进后续处理


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RetrievalBundle:  # 定义业务类 RetrievalBundle
    """FAQ 与文档检索结果的统一载体。"""  # 类文档字符串，概述 RetrievalBundle 的用途

    # FAQ 命中。
    faq_hits: list[RetrievalHit] = field(default_factory=list)  # 更新当前逻辑中的 faq hits
    # 文档命中。
    doc_hits: list[RetrievalHit] = field(default_factory=list)  # 更新当前逻辑中的 doc hits
    # FAQ 检索耗时。
    faq_elapsed_ms: float = 0.0  # 更新当前逻辑中的 faq elapsed ms
    # 文档检索耗时。
    doc_elapsed_ms: float = 0.0  # 更新当前逻辑中的 doc elapsed ms


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RAGPipelineResult:  # 定义业务类 RAGPipelineResult
    """Pipeline 最终结果，供 service.py 转成 ChatResponse。"""  # 类文档字符串，概述 RAGPipelineResult 的用途

    # 最终回答。
    answer: str  # 执行当前业务步骤并推进后续处理
    # 路由名称，例如 direct_answer、faq_direct、rag。
    route: str  # 执行当前业务步骤并推进后续处理
    # 回答提供者标签。
    provider: str  # 执行当前业务步骤并推进后续处理
    # 答案来源标签，用于告诉前端本次是直出、FAQ 直出、混合检索生成还是兜底。
    answer_source: str  # 执行当前业务步骤并推进后续处理
    # 风险等级。
    risk_level: str  # 执行当前业务步骤并推进后续处理
    # 用于前端展示的上下文来源。
    context_hits: list[RetrievalHit] = field(default_factory=list)  # 更新当前逻辑中的 context hits
    # 办事类问题的步骤提示。
    related_tasks: list[dict[str, Any]] = field(default_factory=list)  # 更新当前逻辑中的 关联任务列表
    # 检索和 Pipeline 诊断信息。
    retrieval: dict[str, Any] = field(default_factory=dict)  # 更新当前逻辑中的 retrieval
    # Pipeline 事件列表。
    events: list[RAGEvent] = field(default_factory=list)  # 更新当前逻辑中的 events
