"""请求上下文创建。

本模块对应流程图 4「请求上下文」和 17「场景/数据域」。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

from app.rag.pipeline_schema import DataScope, RAGQueryContext  # 导入二期 RAG 检索与问答服务组件
from app.rag.scenarios import get_scenario  # 导入二期 RAG 检索与问答服务组件


def create_query_context(  # 定义创建 query context 的接口或辅助函数
    *,  # 以下参数改为关键字传参，避免调用位置出错
    query: str,  # 声明参数 query，供当前逻辑使用
    scenario_id: str | None,  # 接收前端选择的问答场景标识
    session_id: str | None,  # 接收前端会话标识，便于串联上下文
    history: list[str] | None,  # 声明参数 history，供当前逻辑使用
    user_role: str,  # 接收提问人角色，用于控制回答口径
    province: str,  # 接收用户所在省份，用于补充地域政策上下文
    city: str,  # 接收用户所在城市，用于补充地域政策上下文
) -> RAGQueryContext:  # 结束 create_query_context 的参数声明
    # This function converts raw web-layer inputs into one normalized context object.
    # The rest of the RAG pipeline reads from this object instead of juggling many loose parameters.
    """把 API 入参转换成 Pipeline 内部统一上下文。"""  # 模块文档字符串，概述当前文件职责

    # 根据前端传入的 scenario_id 找到当前业务场景。
    scenario = get_scenario(scenario_id)  # 更新当前逻辑中的 scenario
    # 角色为空时回退为 employee，避免后续 DataScope 出现空角色。
    normalized_role = user_role or "employee"  # 更新当前逻辑中的 normalized role
    # DataScope 集中表达租户、角色、可见性和地区边界。
    data_scope = DataScope(  # 更新当前逻辑中的 data scope
        tenant_id="default",  # 设置 DataScope 的 租户 ID
        roles=(normalized_role,),  # 设置 DataScope 的 roles
        visibility="public",  # 设置 DataScope 的 visibility
        province=province or "陕西省",  # 设置 DataScope 的 省份
        city=city or "西安市",  # 设置 DataScope 的 城市
    )  # 结束 DataScope 的定义或组装
    # source_filter 与流程图中的 source_filter 对齐，后续可扩展到文件、法规库或租户知识库过滤。
    source_filter = {  # 更新当前逻辑中的 source filter
        "scenario_id": scenario.scenario_id,  # 填充返回或配置中的 scenario id 字段
        "tenant_id": data_scope.tenant_id,  # 填充返回或配置中的 租户 ID 字段
        "visibility": data_scope.visibility,  # 填充返回或配置中的 visibility 字段
    }  # 结束 source_filter 的定义或组装
    # RAGQueryContext 是后续所有节点共享的只读上下文对象。
    return RAGQueryContext(  # 返回当前分支整理好的结果
        query=query,  # 设置 RAGQueryContext 的 query
        scenario=scenario,  # 设置 RAGQueryContext 的 scenario
        session_id=session_id,  # 设置 RAGQueryContext 的 会话 ID
        history=history or [],  # 设置 RAGQueryContext 的 历史上下文
        user_role=normalized_role,  # 设置 RAGQueryContext 的 用户角色
        data_scope=data_scope,  # 设置 RAGQueryContext 的 data scope
        source_filter=source_filter,  # 设置 RAGQueryContext 的 source filter
    )  # 结束 RAGQueryContext 的定义或组装
