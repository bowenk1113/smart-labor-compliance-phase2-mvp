"""RAG 知识库同步工具。

本模块负责把后台管理端 FAQ 变更同步到二期 RAG 检索层：
1. Local MVP 模式：把数据库 FAQ 导出到场景目录下的 faq_runtime.csv，并清空内存索引缓存。
2. Milvus 模式：提供后台触发的全量重建入口，避免每次编辑 FAQ 都阻塞用户请求。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import csv  # 导入 CSV 读写工具，供导入导出接口复用
import os  # 导入当前模块运行所依赖的工具或类型
from datetime import datetime  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from typing import Any  # 导入当前模块运行所依赖的工具或类型

from sqlalchemy.orm import Session  # 导入 SQLAlchemy 会话与 ORM 相关能力

from app.models import FAQ  # 导入当前业务会读写的 ORM 模型
from app.rag.scenarios import SCENARIOS, Scenario, infer_scenario_id  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import clear_local_index_cache, local_index_cache_info, milvus_ivf_pq_index_params  # 导入二期 RAG 检索与问答服务组件


RUNTIME_FAQ_FIELDS = ["id", "question", "answer", "category", "url"]  # 更新当前逻辑中的 RUNTIME FAQ FIELDS
# LAST_SYNC_STATUS 是进程内的轻量状态记录，用来让后台页面看到最近一次同步做了什么。
# MVP 暂不写数据库，因为同步状态只用于教学演示和运行排查。
LAST_SYNC_STATUS: dict[str, Any] = {  # 更新当前逻辑中的 LAST SYNC STATUS
    "last_sync_at": None,  # 执行当前业务步骤并推进后续处理
    "last_action": None,  # 执行当前业务步骤并推进后续处理
    "last_backend": None,  # 执行当前业务步骤并推进后续处理
    "last_result": None,  # 执行当前业务步骤并推进后续处理
    "last_error": None,  # 执行当前业务步骤并推进后续处理
}  # 执行当前业务步骤并推进后续处理


def vector_backend() -> str:  # 定义业务处理函数 vector_backend
    """读取当前向量库后端类型。"""  # 函数文档字符串，说明 vector_backend 的职责

    # PHASE2_VECTOR_BACKEND=local 时使用本地轻量索引；=milvus 时使用真实 Milvus 混合检索。
    return os.getenv("PHASE2_VECTOR_BACKEND", "local").lower()  # 返回当前分支整理好的结果


def sync_after_faq_change(db: Session, *, action: str, tenant_id: int | None = None) -> dict[str, Any]:  # 定义业务处理函数 sync_after_faq_change
    """后台 FAQ 改动后的轻量同步入口。"""  # 函数文档字符串，说明 sync_after_faq_change 的职责

    # 先记录当前后端，返回给前端用于判断是否还需要手动重建 Milvus。
    backend = vector_backend()  # 更新当前逻辑中的 backend
    # 把数据库 FAQ 导出到 faq_runtime.csv，让本地 RAG 不重启也能读取后台新知识。
    runtime_result = export_runtime_faq_csv(db, tenant_id=tenant_id)  # 更新当前逻辑中的 runtime result
    # 清空 lru_cache 缓存；下一次问答会重新读取 faq.csv 和 faq_runtime.csv。
    cache_result = clear_local_index_cache()  # 更新当前逻辑中的 cache result
    # 返回同步详情，后台 FAQ 保存接口会把它放进响应，方便验收实时更新是否发生。
    result = {  # 更新当前逻辑中的 result
        "action": action,  # 填充返回或配置中的 action 字段
        "backend": backend,  # 填充返回或配置中的 backend 字段
        "runtime_faq": runtime_result,  # 填充返回或配置中的 runtime faq 字段
        "local_cache": cache_result,  # 填充返回或配置中的 local cache 字段
        "milvus_notice": "milvus 模式请调用 /api/admin/rag/rebuild-milvus 执行向量库重建" if backend == "milvus" else None,  # 填充返回或配置中的 milvus notice 字段
    }  # 结束 result 的定义或组装
    # 把本次同步动作写入进程内状态，供 /api/admin/rag/sync-status 查询。
    _remember_status(action=action, backend=backend, result=result, error=None)  # 执行当前业务步骤并推进后续处理
    return result  # 返回当前分支整理好的结果


def export_runtime_faq_csv(db: Session, *, tenant_id: int | None = None) -> dict[str, Any]:  # 定义业务处理函数 export_runtime_faq_csv
    """把后台数据库 FAQ 导出成每个场景可检索的 runtime CSV。"""  # 函数文档字符串，说明 export_runtime_faq_csv 的职责

    # 默认导出全部 FAQ；租户后台操作时只导出当前租户 FAQ，保持租户边界清晰。
    query = db.query(FAQ)  # 构造当前业务的基础数据库查询对象
    if tenant_id is not None:  # 根据当前条件决定是否进入对应业务分支
        query = query.filter(FAQ.tenant_id == tenant_id)  # 保存当前逐步拼装的数据库查询对象
    faqs = query.order_by(FAQ.id.asc()).all()  # 更新当前逻辑中的 faqs
    # 先为每个场景准备一个空列表，避免没有 FAQ 的场景缺少 runtime 文件。
    grouped: dict[str, list[FAQ]] = {scenario_id: [] for scenario_id in SCENARIOS}  # 更新当前逻辑中的 grouped
    for faq in faqs:  # 遍历当前集合中的每一项并逐个处理
        # 后台 FAQ 没有强制选择二期场景，所以这里用规则推断它应该进入哪个场景。
        scenario_id = infer_runtime_scenario_id(faq)  # 更新当前逻辑中的 scenario id
        grouped[scenario_id].append(faq)  # 执行当前业务步骤并推进后续处理
    files: list[dict[str, Any]] = []  # 更新当前逻辑中的 files
    for scenario_id, items in grouped.items():  # 遍历当前集合中的每一项并逐个处理
        scenario = SCENARIOS[scenario_id]  # 更新当前逻辑中的 scenario
        path = runtime_faq_csv_path(scenario)  # 更新当前逻辑中的 path
        # 确保场景目录存在；首次运行或新环境解压项目时目录可能还没创建。
        path.parent.mkdir(parents=True, exist_ok=True)  # 执行当前业务步骤并推进后续处理
        # utf-8-sig 兼容 Excel 打开 CSV，newline="" 避免 Windows 下出现空行。
        with path.open("w", encoding="utf-8-sig", newline="") as file:  # 执行当前业务步骤并推进后续处理
            writer = csv.DictWriter(file, fieldnames=RUNTIME_FAQ_FIELDS)  # 创建 CSV 写出器，按字段顺序输出数据
            writer.writeheader()  # 先写出 CSV 表头，保证导出文件字段齐全
            for faq in items:  # 遍历当前集合中的每一项并逐个处理
                # DBFAQ 前缀把后台 FAQ 和内置 CSV FAQ 区分开，避免检索文档 ID 冲突。
                writer.writerow(  # 把当前整理好的记录写入一行 CSV 数据
                    {  # 执行当前业务步骤并推进后续处理
                        "id": f"DBFAQ{faq.id}",  # 执行当前业务步骤并推进后续处理
                        "question": faq.question,  # 执行当前业务步骤并推进后续处理
                        "answer": faq.answer,  # 执行当前业务步骤并推进后续处理
                        "category": faq.category or scenario.label,  # 执行当前业务步骤并推进后续处理
                        "url": "",  # 执行当前业务步骤并推进后续处理
                    }  # 执行当前业务步骤并推进后续处理
                )  # 执行当前业务步骤并推进后续处理
        files.append({"scenario_id": scenario_id, "path": str(path), "records": len(items)})  # 执行当前业务步骤并推进后续处理
    return {"total_records": len(faqs), "files": files}  # 返回当前分支整理好的结果


def infer_runtime_scenario_id(faq: FAQ) -> str:  # 定义业务处理函数 infer_runtime_scenario_id
    """根据 FAQ 分类、关键词和问题内容推断应该进入哪个 RAG 场景。"""  # 函数文档字符串，说明 infer_runtime_scenario_id 的职责

    # 分类、问题、答案、关键词、别名都可能暴露业务场景，因此一起参与场景推断。
    text_parts = [  # 更新当前逻辑中的 text parts
        faq.category or "",  # 补充列表中的 category or 项
        faq.question or "",  # 补充列表中的 question or 项
        faq.answer or "",  # 补充列表中的 answer or 项
        " ".join(faq.keywords or []),  # 补充列表中的 keywords or []) 项
        " ".join(faq.aliases or []),  # 补充列表中的 aliases or []) 项
    ]  # 结束 text_parts 的定义或组装
    # infer_scenario_id 是二期场景关键词分类器，返回最可能的场景 ID。
    inferred_id, _score = infer_scenario_id(" ".join(text_parts))  # 执行当前业务步骤并推进后续处理
    # 推断不到时默认放入社保医保场景，保证 FAQ 不会因为缺少分类而完全不可检索。
    return inferred_id or "social_security"  # 返回当前分支整理好的结果


def runtime_faq_csv_path(scenario: Scenario) -> Path:  # 定义业务处理函数 runtime_faq_csv_path
    """返回后台 FAQ 导出的 runtime CSV 路径。"""  # 函数文档字符串，说明 runtime_faq_csv_path 的职责

    # runtime 文件与内置 faq.csv 放在同一场景目录下，便于排查和备份。
    return scenario.faq_csv.with_name("faq_runtime.csv")  # 返回当前分支整理好的结果


def rebuild_milvus_knowledge_base(*, reset_collections: bool = False) -> dict[str, Any]:  # 定义业务处理函数 rebuild_milvus_knowledge_base
    """重建 Milvus FAQ/文档向量库。"""  # 函数文档字符串，说明 rebuild_milvus_knowledge_base 的职责

    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        # 延迟导入 Milvus 依赖，避免 Local MVP 模式因为没装 Milvus 包而启动失败。
        from app.rag.milvus_store import rebuild_milvus_collections  # 导入二期 RAG 检索与问答服务组件

        # reset_collections=True 会删除旧 collection 后重建，适合演示和验收环境。
        result = rebuild_milvus_collections(reset_collections=reset_collections)  # 更新当前逻辑中的 result
        _remember_status(action="rebuild_milvus", backend="milvus", result=result, error=None)  # 执行当前业务步骤并推进后续处理
        return result  # 返回当前分支整理好的结果
    except Exception as exc:  # 捕获异常并执行降级或错误处理逻辑
        # 记录失败原因后继续抛出，让 FastAPI 返回明确错误，避免静默失败。
        _remember_status(action="rebuild_milvus", backend="milvus", result=None, error=str(exc))  # 执行当前业务步骤并推进后续处理
        raise  # 执行当前业务步骤并推进后续处理


def rag_sync_status() -> dict[str, Any]:  # 定义业务处理函数 rag_sync_status
    """返回当前 RAG 知识库同步状态。"""  # 函数文档字符串，说明 rag_sync_status 的职责

    runtime_files = []  # 更新当前逻辑中的 runtime files
    for scenario in SCENARIOS.values():  # 遍历当前集合中的每一项并逐个处理
        path = runtime_faq_csv_path(scenario)  # 更新当前逻辑中的 path
        # 每个场景都返回 runtime 文件是否存在和更新时间，方便判断后台同步是否落盘。
        runtime_files.append(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "scenario_id": scenario.scenario_id,  # 执行当前业务步骤并推进后续处理
                "path": str(path),  # 执行当前业务步骤并推进后续处理
                "exists": path.exists(),  # 执行当前业务步骤并推进后续处理
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if path.exists() else None,  # 执行当前业务步骤并推进后续处理
            }  # 结束 返回结果 的定义或组装
        )  # 执行当前业务步骤并推进后续处理
    return {  # 返回当前分支整理好的结果
        # backend 告诉前端当前是 local 还是 milvus。
        "backend": vector_backend(),  # 执行当前业务步骤并推进后续处理
        # local_cache 暴露 lru_cache 的命中情况，用于判断缓存是否已清空。
        "local_cache": local_index_cache_info(),  # 执行当前业务步骤并推进后续处理
        "runtime_files": runtime_files,  # 执行当前业务步骤并推进后续处理
        "index_params": milvus_ivf_pq_index_params(),  # 执行当前业务步骤并推进后续处理
        **LAST_SYNC_STATUS,  # 执行当前业务步骤并推进后续处理
    }  # 结束 返回结果 的定义或组装


def _remember_status(*, action: str, backend: str, result: Any, error: str | None) -> None:  # 定义业务处理函数 _remember_status
    """记录最近一次同步动作，供状态接口查看。"""  # 函数文档字符串，说明 _remember_status 的职责

    # 这里只保存最后一次动作，保持 MVP 状态结构简单；生产可扩展为数据库审计日志。
    LAST_SYNC_STATUS.update(  # 执行当前业务步骤并推进后续处理
        {  # 执行当前业务步骤并推进后续处理
            "last_sync_at": datetime.now().isoformat(timespec="seconds"),  # 执行当前业务步骤并推进后续处理
            "last_action": action,  # 执行当前业务步骤并推进后续处理
            "last_backend": backend,  # 执行当前业务步骤并推进后续处理
            "last_result": result,  # 执行当前业务步骤并推进后续处理
            "last_error": error,  # 执行当前业务步骤并推进后续处理
        }  # 结束 返回结果 的定义或组装
    )  # 执行当前业务步骤并推进后续处理
