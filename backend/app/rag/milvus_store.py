"""真实 Milvus + LangChain RAG 存储实现。

本模块是二期 MVP 的真实向量库路径，和 `store.py` 中的本地兜底索引形成互补：
- 开发演示时，如果没有启动 Docker Milvus，可以使用本地兜底索引跑通闭环。
- 完整 MVP 验收时，启动 `docker-compose.milvus.yml` 后，使用本模块把 FAQ 和文档写入 Milvus。

核心 RAG 技术点：
- BGE-M3 Embedding：把 FAQ 和文档切片转成 dense 向量。
- Milvus BM25BuiltInFunction：在服务端生成 sparse BM25 向量。
- Hybrid Search：同一个 collection 同时使用 dense + sparse 字段召回。
- IVF_PQ：为 dense 向量配置压缩索引，适合较大知识库降存储和加速。
- Metadata Filter：用 scenario_id、source_type、tenant_id、kb_version 做数据隔离。
- CrossEncoder Rerank：对粗召回结果做二阶段精排。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import os  # 导入当前模块运行所依赖的工具或类型
from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型
from functools import lru_cache  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from typing import Any, Literal  # 导入当前模块运行所依赖的工具或类型

from app.rag.scenarios import SCENARIOS, Scenario, get_scenario  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import KnowledgeDocument, RetrievalHit, build_filter_expr, load_doc_documents, load_faq_documents, milvus_ivf_pq_index_params  # 导入二期 RAG 检索与问答服务组件


DEFAULT_FAQ_COLLECTION = "slc_phase2_faq_vectors"  # 更新当前逻辑中的 DEFAULT FAQ COLLECTION
DEFAULT_DOC_COLLECTION = "slc_phase2_doc_vectors"  # 更新当前逻辑中的 DEFAULT DOC COLLECTION
PROJECT_MODEL_DIRNAME = "model"  # 更新当前逻辑中的 PROJECT MODEL DIRNAME
EMBEDDING_MODEL_DIRNAME = "bge-m3"  # 更新当前逻辑中的 EMBEDDING MODEL DIRNAME
RERANKER_MODEL_DIRNAME = "bge-reranker-large"  # 更新当前逻辑中的 RERANKER MODEL DIRNAME


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class MilvusSettings:  # 定义业务类 MilvusSettings
    """Milvus RAG 运行配置。"""  # 类文档字符串，概述 MilvusSettings 的用途

    milvus_uri: str  # 执行当前业务步骤并推进后续处理
    embedding_model_path: Path  # 执行当前业务步骤并推进后续处理
    reranker_model_path: Path  # 执行当前业务步骤并推进后续处理
    tenant_id: str = "default"  # 更新当前逻辑中的 租户 ID
    kb_version: str = "phase2_mvp"  # 更新当前逻辑中的 kb version
    search_top_k: int = 8  # 更新当前逻辑中的 search top k


def get_milvus_settings() -> MilvusSettings:  # 定义获取 milvus settings 的接口或辅助函数
    """从环境变量读取 Milvus 与本地模型配置。"""  # 函数文档字符串，说明 get_milvus_settings 的职责

    backend_root = Path(__file__).resolve().parents[2]  # 更新当前逻辑中的 backend root
    project_root = backend_root.parent  # 更新当前逻辑中的 project root
    default_model_root = project_root / PROJECT_MODEL_DIRNAME  # 更新当前逻辑中的 default model root
    return MilvusSettings(  # 返回当前分支整理好的结果
        milvus_uri=os.getenv("MILVUS_URI", "http://127.0.0.1:19530"),  # 设置 MilvusSettings 的 milvus uri
        embedding_model_path=Path(os.getenv("EMBEDDING_MODEL_PATH", str(default_model_root / EMBEDDING_MODEL_DIRNAME))),  # 设置 MilvusSettings 的 embedding model path
        reranker_model_path=Path(os.getenv("RERANKER_MODEL_PATH", str(default_model_root / RERANKER_MODEL_DIRNAME))),  # 设置 MilvusSettings 的 reranker model path
    )  # 结束 MilvusSettings 的定义或组装


def assert_rag_dependencies() -> None:  # 定义业务处理函数 assert_rag_dependencies
    """检查真实 RAG 路径所需依赖是否存在。"""  # 函数文档字符串，说明 assert_rag_dependencies 的职责

    missing: list[str] = []  # 更新当前逻辑中的 missing
    for module_name in ("langchain_milvus", "langchain_huggingface", "sentence_transformers", "pymilvus"):  # 遍历当前集合中的每一项并逐个处理
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            __import__(module_name)  # 执行当前业务步骤并推进后续处理
        except ModuleNotFoundError:  # 捕获异常并执行降级或错误处理逻辑
            missing.append(module_name)  # 执行当前业务步骤并推进后续处理
    if missing:  # 根据当前条件决定是否进入对应业务分支
        raise RuntimeError(  # 执行当前控制流分支
            "真实 Milvus RAG 依赖未安装："  # 执行当前业务步骤并推进后续处理
            + ", ".join(missing)  # 执行当前业务步骤并推进后续处理
            + "。请在 RAG 环境执行：python -m pip install -r backend/requirements.txt"  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理


@lru_cache(maxsize=1)  # 为后续函数或类声明附加装饰器配置
def embeddings():  # 定义业务处理函数 embeddings
    """加载 BGE-M3 Embedding 模型。"""  # 函数文档字符串，说明 embeddings 的职责

    from langchain_huggingface import HuggingFaceEmbeddings  # 导入当前模块运行所依赖的工具或类型

    settings = get_milvus_settings()  # 缓存全局运行配置对象供各模块复用
    if not settings.embedding_model_path.exists():  # 根据当前条件决定是否进入对应业务分支
        raise RuntimeError(  # 执行当前控制流分支
            f"Embedding 模型不存在：{settings.embedding_model_path}。"  # 执行当前业务步骤并推进后续处理
            f"请确认项目内 {PROJECT_MODEL_DIRNAME}\\{EMBEDDING_MODEL_DIRNAME} 目录存在，"  # 执行当前业务步骤并推进后续处理
            "或通过 EMBEDDING_MODEL_PATH 指定有效路径。"  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
    return HuggingFaceEmbeddings(  # 返回当前分支整理好的结果
        model_name=str(settings.embedding_model_path),  # 设置 HuggingFaceEmbeddings 的 model name
        model_kwargs={"device": "cpu", "local_files_only": True},  # 设置 HuggingFaceEmbeddings 的 device
        encode_kwargs={"normalize_embeddings": True},  # 设置 HuggingFaceEmbeddings 的 normalize embeddings
    )  # 结束 HuggingFaceEmbeddings 的定义或组装


@lru_cache(maxsize=1)  # 为后续函数或类声明附加装饰器配置
def reranker():  # 定义业务处理函数 reranker
    """加载 BGE CrossEncoder Reranker。"""  # 函数文档字符串，说明 reranker 的职责

    from sentence_transformers import CrossEncoder  # 导入当前模块运行所依赖的工具或类型

    settings = get_milvus_settings()  # 缓存全局运行配置对象供各模块复用
    if not settings.reranker_model_path.exists():  # 根据当前条件决定是否进入对应业务分支
        raise RuntimeError(  # 执行当前控制流分支
            f"Reranker 模型不存在：{settings.reranker_model_path}。"  # 执行当前业务步骤并推进后续处理
            f"请确认项目内 {PROJECT_MODEL_DIRNAME}\\{RERANKER_MODEL_DIRNAME} 目录存在，"  # 执行当前业务步骤并推进后续处理
            "或通过 RERANKER_MODEL_PATH 指定有效路径。"  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
    return CrossEncoder(str(settings.reranker_model_path), device="cpu", local_files_only=True)  # 返回当前分支整理好的结果


def bm25_function():  # 定义业务处理函数 bm25_function
    """创建 Milvus 服务端 BM25 稀疏向量函数。"""  # 函数文档字符串，说明 bm25_function 的职责

    from langchain_milvus import BM25BuiltInFunction  # 导入当前模块运行所依赖的工具或类型

    return BM25BuiltInFunction(  # 返回当前分支整理好的结果
        input_field_names="text",  # 设置 BM25BuiltInFunction 的 input field names
        output_field_names="sparse",  # 设置 BM25BuiltInFunction 的 output field names
        analyzer_params={"type": "chinese"},  # 设置 BM25BuiltInFunction 的 type
        enable_match=True,  # 设置 BM25BuiltInFunction 的 enable match
    )  # 结束 BM25BuiltInFunction 的定义或组装


def collection_name(source_type: Literal["faq", "doc"]) -> str:  # 定义业务处理函数 collection_name
    """返回 FAQ 或文档 collection 名称。"""  # 函数文档字符串，说明 collection_name 的职责

    if source_type == "faq":  # 根据当前条件决定是否进入对应业务分支
        return os.getenv("PHASE2_FAQ_COLLECTION", DEFAULT_FAQ_COLLECTION)  # 返回当前分支整理好的结果
    return os.getenv("PHASE2_DOC_COLLECTION", DEFAULT_DOC_COLLECTION)  # 返回当前分支整理好的结果


def vector_store(source_type: Literal["faq", "doc"], *, drop_old: bool = False):  # 定义业务处理函数 vector_store
    """创建 LangChain Milvus VectorStore。"""  # 函数文档字符串，说明 vector_store 的职责

    from langchain_milvus import Milvus  # 导入当前模块运行所依赖的工具或类型

    settings = get_milvus_settings()  # 缓存全局运行配置对象供各模块复用
    # One vector store instance maps to one physical Milvus collection: FAQ or document chunks.
    # langchain_milvus 在“dense embedding + sparse builtin BM25”双向量字段模式下，
    # 要求 index_params 为与 vector_field 一一对应的列表：
    # 1. dense 字段使用 IVF_PQ，体现本项目的压缩索引设计。
    # 2. sparse 字段使用 Milvus 稀疏倒排索引，供 BM25 混合检索使用。
    index_params = [  # 更新当前逻辑中的 index params
        {"field_name": "dense", **milvus_ivf_pq_index_params()},  # 补充列表中的 field name 项
        {  # 补充列表中的 { 项
            "field_name": "sparse",  # 补充列表中的 field name 项
            "index_type": "SPARSE_INVERTED_INDEX",  # 补充列表中的 index type 项
            # BM25 内建稀疏函数的输出字段必须使用 BM25 度量类型。
            # 这里如果写成 IP，会在 create_index 阶段被 Milvus 直接拒绝。
            "metric_type": "BM25",  # 执行当前业务步骤并推进后续处理
            "params": {"drop_ratio_build": 0.2},  # 执行当前业务步骤并推进后续处理
        },  # 执行当前业务步骤并推进后续处理
    ]  # 结束 index_params 的定义或组装
    return Milvus(  # 返回当前分支整理好的结果
        embedding_function=embeddings(),  # 设置 Milvus 的 embedding function
        builtin_function=bm25_function(),  # 设置 Milvus 的 builtin function
        collection_name=collection_name(source_type),  # 设置 Milvus 的 collection name
        # langchain_milvus 会在内部为 MilvusClient 管理连接别名。
        # 这里如果再手动传 alias，会在部分 pymilvus 版本上触发
        # “Connections.connect() got multiple values for argument 'alias'”。
        connection_args={"uri": settings.milvus_uri},  # 更新当前逻辑中的 connection args
        vector_field=["dense", "sparse"],  # 更新当前逻辑中的 vector field
        text_field="text",  # 更新当前逻辑中的 text field
        primary_field="pk",  # 更新当前逻辑中的 primary field
        auto_id=False,  # 更新当前逻辑中的 auto id
        enable_dynamic_field=True,  # 更新当前逻辑中的 enable dynamic field
        consistency_level="Session",  # 更新当前逻辑中的 consistency level
        drop_old=drop_old,  # 更新当前逻辑中的 drop old
        index_params=index_params,  # 更新当前逻辑中的 index params
    )  # 结束 Milvus 的定义或组装


def to_langchain_documents(documents: list[KnowledgeDocument]) -> tuple[list[Any], list[str]]:  # 定义业务处理函数 to_langchain_documents
    """把项目内部文档对象转换成 LangChain Document 和主键。"""  # 函数文档字符串，说明 to_langchain_documents 的职责

    from langchain_core.documents import Document  # 导入当前模块运行所依赖的工具或类型

    # LangChain Milvus expects two parallel arrays: Document objects and their explicit ids.
    lc_docs = []  # 更新当前逻辑中的 lc docs
    ids = []  # 更新当前逻辑中的 ids
    for document in documents:  # 遍历当前集合中的每一项并逐个处理
        doc_id = str(document.metadata.get("id") or document.content[:80])  # 更新当前逻辑中的 doc id
        lc_docs.append(Document(page_content=document.content, metadata=dict(document.metadata)))  # 执行当前业务步骤并推进后续处理
        ids.append(doc_id)  # 执行当前业务步骤并推进后续处理
    return lc_docs, ids  # 返回当前分支整理好的结果


def rebuild_milvus_collections(*, reset_collections: bool = False) -> dict[str, Any]:  # 定义业务处理函数 rebuild_milvus_collections
    """把四个场景的 FAQ 和文档写入 Milvus。"""  # 函数文档字符串，说明 rebuild_milvus_collections 的职责

    assert_rag_dependencies()  # 执行当前业务步骤并推进后续处理
    # FAQ and document chunks are split into two collections so retrieval can filter them independently.
    faq_store = vector_store("faq", drop_old=reset_collections)  # 更新当前逻辑中的 faq store
    doc_store = vector_store("doc", drop_old=reset_collections)  # 更新当前逻辑中的 doc store
    summary: dict[str, Any] = {  # 更新当前逻辑中的 summary
        "backend": "milvus_langchain",  # 执行当前业务步骤并推进后续处理
        "faq_collection": collection_name("faq"),  # 执行当前业务步骤并推进后续处理
        "doc_collection": collection_name("doc"),  # 执行当前业务步骤并推进后续处理
        "index_params": milvus_ivf_pq_index_params(),  # 执行当前业务步骤并推进后续处理
        "scenarios": [],  # 执行当前业务步骤并推进后续处理
    }  # 执行当前业务步骤并推进后续处理
    for scenario in SCENARIOS.values():  # 遍历当前集合中的每一项并逐个处理
        faq_docs, faq_ids = to_langchain_documents(load_faq_documents(scenario))  # 执行当前业务步骤并推进后续处理
        doc_docs, doc_ids = to_langchain_documents(load_doc_documents(scenario))  # 执行当前业务步骤并推进后续处理
        if faq_docs:  # 根据当前条件决定是否进入对应业务分支
            faq_store.add_documents(faq_docs, ids=faq_ids)  # 执行当前业务步骤并推进后续处理
        if doc_docs:  # 根据当前条件决定是否进入对应业务分支
            doc_store.add_documents(doc_docs, ids=doc_ids)  # 执行当前业务步骤并推进后续处理
        summary["scenarios"].append(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "scenario_id": scenario.scenario_id,  # 执行当前业务步骤并推进后续处理
                "faq_records": len(faq_docs),  # 执行当前业务步骤并推进后续处理
                "doc_chunks": len(doc_docs),  # 执行当前业务步骤并推进后续处理
                "faq_filter_expr": build_filter_expr(scenario_id=scenario.scenario_id, source_type="faq"),  # 执行当前业务步骤并推进后续处理
                "doc_filter_expr": build_filter_expr(scenario_id=scenario.scenario_id, source_type="doc"),  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
    return summary  # 返回当前分支整理好的结果


def search_milvus(scenario: Scenario, query_variants: list[str], *, source_type: Literal["faq", "doc"], top_k: int = 8) -> list[RetrievalHit]:  # 定义业务处理函数 search_milvus
    """在 Milvus 中执行混合检索并返回精排结果。"""  # 函数文档字符串，说明 search_milvus 的职责

    assert_rag_dependencies()  # 执行当前业务步骤并推进后续处理
    # query_variants enables multi-query recall before merging the strongest hits.
    store = vector_store(source_type)  # 更新当前逻辑中的 store
    expr = build_filter_expr(scenario_id=scenario.scenario_id, source_type=source_type)  # 更新当前逻辑中的 expr
    merged: dict[str, RetrievalHit] = {}  # 更新当前逻辑中的 merged
    for query in query_variants:  # 遍历当前集合中的每一项并逐个处理
        docs_with_scores = store.similarity_search_with_score(query=query, k=top_k, expr=expr)  # 更新当前逻辑中的 docs with scores
        for document, score in docs_with_scores:  # 遍历当前集合中的每一项并逐个处理
            metadata = dict(document.metadata or {})  # 更新当前逻辑中的 metadata
            doc_id = str(metadata.get("id") or metadata.get("chunk_id") or document.page_content[:80])  # 更新当前逻辑中的 doc id
            hit = RetrievalHit(  # 更新当前逻辑中的 hit
                document=KnowledgeDocument(content=document.page_content, metadata=metadata),  # 设置 RetrievalHit 的 document
                score=float(score),  # 设置 RetrievalHit 的 score
            )  # 结束 RetrievalHit 的定义或组装
            previous = merged.get(doc_id)  # 更新当前逻辑中的 previous
            if previous is None or hit.score > previous.score:  # 根据当前条件决定是否进入对应业务分支
                merged[doc_id] = hit  # 更新当前逻辑中的 merged[doc id]
    hits = sorted(merged.values(), key=lambda item: item.score, reverse=True)  # 更新当前逻辑中的 hits
    return rerank_hits(query_variants[0] if query_variants else "", hits[: top_k * 3])[:top_k]  # 返回当前分支整理好的结果


def rerank_hits(query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:  # 定义业务处理函数 rerank_hits
    """使用 CrossEncoder 对 Milvus 粗召回结果精排。"""  # 函数文档字符串，说明 rerank_hits 的职责

    if not query or not hits:  # 根据当前条件决定是否进入对应业务分支
        return hits  # 返回当前分支整理好的结果
    # CrossEncoder reranking is a refinement step and should not be allowed to break the whole RAG chain.
    pairs = [(query, hit.document.content) for hit in hits]  # 更新当前逻辑中的 pairs
    # 二阶段重排是加分项，不应该成为整条 RAG 链路的单点故障。
    # 在部分本地模型目录不完整、tokenizer 文件缺失，或 transformers / sentence-transformers
    # 版本组合不兼容时，CrossEncoder 初始化可能失败。此时直接回退到 Milvus 混合召回排序，
    # 保证 FAQ / 文档混合检索仍然可以给出答案，而不是整条链路进入异常兜底。
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        scores = reranker().predict(pairs)  # 更新当前逻辑中的 scores
    except Exception:  # 捕获异常并执行降级或错误处理逻辑
        return hits  # 返回当前分支整理好的结果
    reranked = [  # 更新当前逻辑中的 reranked
        RetrievalHit(document=hit.document, score=float(score))  # 补充列表中的 document, score=float(score)) 项
        for hit, score in sorted(zip(hits, scores), key=lambda item: float(item[1]), reverse=True)  # 补充列表中的 for hit, score in sorted(zip(hits, scores), key=lambda item 项
    ]  # 结束 reranked 的定义或组装
    return reranked  # 返回当前分支整理好的结果


def search_milvus_or_raise(scenario_id: str, query_variants: list[str], *, source_type: Literal["faq", "doc"], top_k: int = 8) -> list[RetrievalHit]:  # 定义业务处理函数 search_milvus_or_raise
    """按场景 ID 执行真实 Milvus 检索。"""  # 函数文档字符串，说明 search_milvus_or_raise 的职责

    return search_milvus(get_scenario(scenario_id), query_variants, source_type=source_type, top_k=top_k)  # 返回当前分支整理好的结果
