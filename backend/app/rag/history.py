"""Pipeline 历史记录适配层。

流程图 15 写的是 history.add_turn()。原项目已经在 chat.py 中把问答写入数据库，
因此本文件只负责在 Pipeline 事件里记录“已完成写历史节点”，避免重复写库。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

from app.rag.pipeline_schema import RAGEvent, RAGQueryContext  # 导入二期 RAG 检索与问答服务组件


def add_turn(context: RAGQueryContext, answer: str, *, route: str) -> RAGEvent:  # 定义业务处理函数 add_turn
    """生成历史写入事件，真实数据库写入由 routers/chat.py 负责。"""  # 函数文档字符串，说明 add_turn 的职责

    # 这里不直接访问数据库，是为了让 RAG Pipeline 保持纯业务逻辑，方便单元测试。
    return RAGEvent(  # 返回当前分支整理好的结果
        name="history.add_turn",  # 设置 RAGEvent 的 名称
        payload={  # 设置 RAGEvent 的 payload
            "session_id": context.session_id,  # 向 Dify 请求体写入 会话 ID
            "route": route,  # 向 Dify 请求体写入 route
            "query_preview": context.query[:80],  # 向 Dify 请求体写入 query preview
            "answer_preview": answer[:80],  # 向 Dify 请求体写入 answer preview
        },  # 结束 payload 的定义或组装
    )  # 结束 RAGEvent 的定义或组装
