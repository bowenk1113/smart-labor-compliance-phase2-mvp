"""FAQ 向量库与文档检索实现。

本模块优先表达 Milvus/LangChain 的生产设计，同时提供轻量本地向量检索兜底，保证二期 MVP 在未启动 Docker 知识库时也能演示闭环。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import csv  # 导入 CSV 读写工具，供导入导出接口复用
import math  # 导入当前模块运行所依赖的工具或类型
import re  # 导入当前模块运行所依赖的工具或类型
import time  # 导入时间工具，统计耗时或生成时间戳
from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型
from functools import lru_cache  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录
from typing import Any  # 导入当前模块运行所依赖的工具或类型

from app.rag.scenarios import Scenario  # 导入二期 RAG 检索与问答服务组件


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class KnowledgeDocument:  # 定义业务类 KnowledgeDocument
    """检索文档对象。"""  # 类文档字符串，概述 KnowledgeDocument 的用途

    content: str  # 执行当前业务步骤并推进后续处理
    metadata: dict[str, Any]  # 执行当前业务步骤并推进后续处理


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class RetrievalHit:  # 定义业务类 RetrievalHit
    """单条检索命中。"""  # 类文档字符串，概述 RetrievalHit 的用途

    document: KnowledgeDocument  # 执行当前业务步骤并推进后续处理
    score: float  # 执行当前业务步骤并推进后续处理


def milvus_ivf_pq_index_params() -> dict[str, Any]:  # 定义业务处理函数 milvus_ivf_pq_index_params
    """返回 Milvus IVF_PQ 索引参数。"""  # 函数文档字符串，说明 milvus_ivf_pq_index_params 的职责

    return {  # 返回当前分支整理好的结果
        "index_type": "IVF_PQ",  # 填充返回或配置中的 index type 字段
        "metric_type": "COSINE",  # 填充返回或配置中的 metric type 字段
        "params": {"nlist": 128, "m": 16, "nbits": 8},  # 填充返回或配置中的 params 字段
    }  # 结束 返回结果 的定义或组装


def build_filter_expr(*, scenario_id: str, source_type: str, tenant_id: str = "default", kb_version: str = "phase2_mvp") -> str:  # 定义业务处理函数 build_filter_expr
    """构建 Milvus 标量过滤表达式。"""  # 函数文档字符串，说明 build_filter_expr 的职责

    return (  # 返回当前分支整理好的结果
        f'scenario_id == "{_escape_expr(scenario_id)}" '  # 设置 return 的 字段
        f'and source_type == "{_escape_expr(source_type)}" '  # 设置 return 的 字段
        f'and tenant_id == "{_escape_expr(tenant_id)}" '  # 设置 return 的 字段
        f'and kb_version == "{_escape_expr(kb_version)}"'  # 设置 return 的 字段
    )  # 结束 return 的定义或组装


def _escape_expr(value: str) -> str:  # 定义业务处理函数 _escape_expr
    """转义 Milvus 表达式字符串。"""  # 函数文档字符串，说明 _escape_expr 的职责

    return value.replace("\\", "\\\\").replace('"', '\\"')  # 返回当前分支整理好的结果


def load_faq_documents(scenario: Scenario) -> list[KnowledgeDocument]:  # 定义业务处理函数 load_faq_documents
    """加载场景 FAQ CSV。"""  # 函数文档字符串，说明 load_faq_documents 的职责

    # 一个场景可能同时有两类 FAQ：
    # 1. faq.csv：项目内置的种子 FAQ，便于交付时直接演示；
    # 2. faq_runtime.csv：后台管理端从数据库实时导出的运营 FAQ。
    documents: list[KnowledgeDocument] = []  # 更新当前逻辑中的 documents
    for csv_path in faq_csv_paths(scenario):  # 遍历当前集合中的每一项并逐个处理
        # 每个 CSV 都转换成统一 KnowledgeDocument，后续索引层不关心它来自哪里。
        documents.extend(load_faq_csv(csv_path, scenario, id_prefix=""))  # 执行当前业务步骤并推进后续处理
    return documents  # 返回当前分支整理好的结果


def faq_csv_paths(scenario: Scenario) -> list[Path]:  # 定义业务处理函数 faq_csv_paths
    """返回某个场景需要加载的静态 FAQ 和后台实时 FAQ 文件。"""  # 函数文档字符串，说明 faq_csv_paths 的职责

    # runtime_csv 是“实时更新”的关键文件；后台 FAQ 改动后会重写这个文件。
    runtime_csv = scenario.faq_csv.with_name("faq_runtime.csv")  # 更新当前逻辑中的 runtime csv
    # 只返回实际存在的文件，避免首次启动时因为 runtime 文件还没生成而报错。
    return [path for path in (scenario.faq_csv, runtime_csv) if path.exists()]  # 返回当前分支整理好的结果


def load_faq_csv(csv_path: Path, scenario: Scenario, *, id_prefix: str = "") -> list[KnowledgeDocument]:  # 定义业务处理函数 load_faq_csv
    """把单个 FAQ CSV 文件转换成检索文档。"""  # 函数文档字符串，说明 load_faq_csv 的职责

    documents: list[KnowledgeDocument] = []  # 更新当前逻辑中的 documents
    # utf-8-sig 可以兼容 Excel 导出的带 BOM CSV。
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:  # 执行当前业务步骤并推进后续处理
        reader = csv.DictReader(file)  # 更新当前逻辑中的 reader
        for index, row in enumerate(reader, start=1):  # 遍历当前集合中的每一项并逐个处理
            # FAQ 检索至少需要 question 和 answer；缺任意一个都跳过，避免脏数据进索引。
            question = (row.get("question") or "").strip()  # 清洗并保存用户提交的问题文本
            answer = (row.get("answer") or "").strip()  # 更新当前逻辑中的 回答内容
            if not question or not answer:  # 根据当前条件决定是否进入对应业务分支
                continue  # 跳过当前项，继续处理下一项数据
            # content 是真正参与向量化/相似度计算的文本。
            content = f"问题：{question}\n答案：{answer}"  # 生成最终返回或上传的字节内容
            # doc_id 用于多路召回去重；后台导出的 DBFAQxxx 也会放在这里。
            doc_id = row.get("id") or f"{scenario.scenario_id}_faq_{index}"  # 更新当前逻辑中的 doc id
            documents.append(  # 执行当前业务步骤并推进后续处理
                KnowledgeDocument(  # 执行当前业务步骤并推进后续处理
                    content=content,  # 生成最终返回或上传的字节内容
                    metadata={  # 更新当前逻辑中的 metadata
                        # metadata 会一路返回到 sources，帮助前端展示来源和分数。
                        "id": f"{id_prefix}{doc_id}",  # 执行当前业务步骤并推进后续处理
                        "title": question,  # 执行当前业务步骤并推进后续处理
                        "answer": answer,  # 执行当前业务步骤并推进后续处理
                        "category": row.get("category") or scenario.label,  # 执行当前业务步骤并推进后续处理
                        "url": row.get("url") or "",  # 执行当前业务步骤并推进后续处理
                        "scenario_id": scenario.scenario_id,  # 执行当前业务步骤并推进后续处理
                        "source_type": "faq",  # 执行当前业务步骤并推进后续处理
                        "source_label": scenario.source_label,  # 执行当前业务步骤并推进后续处理
                        "tenant_id": "default",  # 执行当前业务步骤并推进后续处理
                        "kb_version": "phase2_mvp",  # 执行当前业务步骤并推进后续处理
                    },  # 结束 metadata 的定义或组装
                )  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
    return documents  # 返回当前分支整理好的结果


def load_doc_documents(scenario: Scenario) -> list[KnowledgeDocument]:  # 定义业务处理函数 load_doc_documents
    """加载场景文档并切分为小块。"""  # 函数文档字符串，说明 load_doc_documents 的职责

    documents: list[KnowledgeDocument] = []  # 更新当前逻辑中的 documents
    for path in sorted(scenario.data_dir.glob("*.md")):  # 遍历当前集合中的每一项并逐个处理
        text = path.read_text(encoding="utf-8").strip()  # 把文件字节内容解码成可解析的文本
        for index, chunk in enumerate(chunk_text(text), start=1):  # 遍历当前集合中的每一项并逐个处理
            documents.append(  # 执行当前业务步骤并推进后续处理
                KnowledgeDocument(  # 执行当前业务步骤并推进后续处理
                    content=chunk,  # 生成最终返回或上传的字节内容
                    metadata={  # 更新当前逻辑中的 metadata
                        "id": f"{scenario.scenario_id}_{path.stem}_{index}",  # 填充返回或配置中的 主键 ID 字段
                        "title": path.stem,  # 填充返回或配置中的 标题 字段
                        "file_name": path.name,  # 填充返回或配置中的 file name 字段
                        "scenario_id": scenario.scenario_id,  # 填充返回或配置中的 scenario id 字段
                        "source_type": "doc",  # 填充返回或配置中的 source type 字段
                        "source_label": scenario.source_label,  # 填充返回或配置中的 source label 字段
                        "tenant_id": "default",  # 填充返回或配置中的 租户 ID 字段
                        "kb_version": "phase2_mvp",  # 填充返回或配置中的 kb version 字段
                    },  # 结束 metadata 的定义或组装
                )  # 执行当前业务步骤并推进后续处理
            )  # 执行当前业务步骤并推进后续处理
    return documents  # 返回当前分支整理好的结果


def chunk_text(text: str, chunk_size: int = 620, overlap: int = 100) -> list[str]:  # 定义业务处理函数 chunk_text
    """按固定窗口切分中文资料。"""  # 函数文档字符串，说明 chunk_text 的职责

    normalized = re.sub(r"\n{3,}", "\n\n", text)  # 初始化当前导出行的标准化结果字典
    if len(normalized) <= chunk_size:  # 根据当前条件决定是否进入对应业务分支
        return [normalized]  # 返回当前分支整理好的结果
    chunks: list[str] = []  # 更新当前逻辑中的 chunks
    start = 0  # 更新当前逻辑中的 start
    while start < len(normalized):  # 在条件满足时持续循环处理
        end = min(len(normalized), start + chunk_size)  # 更新当前逻辑中的 end
        chunks.append(normalized[start:end].strip())  # 执行当前业务步骤并推进后续处理
        if end == len(normalized):  # 根据当前条件决定是否进入对应业务分支
            break  # 满足退出条件后立即结束当前循环
        start = max(0, end - overlap)  # 更新当前逻辑中的 start
    return [chunk for chunk in chunks if chunk]  # 返回当前分支整理好的结果


class LocalVectorIndex:  # 定义业务类 LocalVectorIndex
    """轻量本地向量索引。"""  # 类文档字符串，概述 LocalVectorIndex 的用途

    def __init__(self, documents: list[KnowledgeDocument]) -> None:  # 定义业务处理函数 __init__
        self.documents = documents  # 更新当前逻辑中的 documents
        self.vectors = [text_vector(item.content) for item in documents]  # 更新当前逻辑中的 vectors

    def search(self, query_variants: list[str], *, top_k: int) -> list[RetrievalHit]:  # 定义业务处理函数 search
        """对多个查询变体执行召回、合并、重排。"""  # 函数文档字符串，说明 search 的职责

        merged: dict[str, RetrievalHit] = {}  # 更新当前逻辑中的 merged
        for query in query_variants:  # 遍历当前集合中的每一项并逐个处理
            query_vector = text_vector(query)  # 更新当前逻辑中的 query vector
            for document, vector in zip(self.documents, self.vectors):  # 遍历当前集合中的每一项并逐个处理
                base_score = cosine_similarity(query_vector, vector)  # 更新当前逻辑中的 base score
                keyword_score = keyword_overlap(query, document.content)  # 更新当前逻辑中的 keyword score
                score = round(base_score * 0.62 + keyword_score * 0.38, 6)  # 更新当前逻辑中的 score
                doc_id = str(document.metadata.get("id") or document.content[:80])  # 更新当前逻辑中的 doc id
                previous = merged.get(doc_id)  # 更新当前逻辑中的 previous
                if previous is None or score > previous.score:  # 根据当前条件决定是否进入对应业务分支
                    merged[doc_id] = RetrievalHit(document=document, score=score)  # 更新当前逻辑中的 merged[doc id]
        hits = sorted(merged.values(), key=lambda item: item.score, reverse=True)  # 更新当前逻辑中的 hits
        return rerank(query_variants[0] if query_variants else "", hits[: max(top_k * 3, top_k)])[:top_k]  # 返回当前分支整理好的结果


def text_vector(text: str) -> dict[str, float]:  # 定义业务处理函数 text_vector
    """用字符 ngram 构建教学版向量。"""  # 函数文档字符串，说明 text_vector 的职责

    tokens = tokenize(text)  # 更新当前逻辑中的 tokens
    counts: dict[str, float] = {}  # 更新当前逻辑中的 counts
    for token in tokens:  # 遍历当前集合中的每一项并逐个处理
        counts[token] = counts.get(token, 0.0) + 1.0  # 更新当前逻辑中的 counts[token]
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0  # 更新当前逻辑中的 norm
    return {key: value / norm for key, value in counts.items()}  # 返回当前分支整理好的结果


def tokenize(text: str) -> list[str]:  # 定义业务处理函数 tokenize
    """把中文文本转换为字符级和词级混合 token。"""  # 函数文档字符串，说明 tokenize 的职责

    cleaned = re.sub(r"\s+", "", text.lower())  # 更新当前逻辑中的 cleaned
    chars = [char for char in cleaned if "\u4e00" <= char <= "\u9fff" or char.isalnum()]  # 更新当前逻辑中的 chars
    bigrams = ["".join(chars[index : index + 2]) for index in range(max(len(chars) - 1, 0))]  # 更新当前逻辑中的 bigrams
    trigrams = ["".join(chars[index : index + 3]) for index in range(max(len(chars) - 2, 0))]  # 更新当前逻辑中的 trigrams
    return chars + bigrams + trigrams  # 返回当前分支整理好的结果


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:  # 定义业务处理函数 cosine_similarity
    """计算稀疏向量余弦相似度。"""  # 函数文档字符串，说明 cosine_similarity 的职责

    if not left or not right:  # 根据当前条件决定是否进入对应业务分支
        return 0.0  # 返回当前分支整理好的结果
    if len(left) > len(right):  # 根据当前条件决定是否进入对应业务分支
        left, right = right, left  # 执行当前业务步骤并推进后续处理
    return sum(value * right.get(key, 0.0) for key, value in left.items())  # 返回当前分支整理好的结果


def keyword_overlap(query: str, content: str) -> float:  # 定义业务处理函数 keyword_overlap
    """计算关键词重合分。"""  # 函数文档字符串，说明 keyword_overlap 的职责

    query_tokens = set(tokenize(query))  # 更新当前逻辑中的 query tokens
    content_tokens = set(tokenize(content))  # 更新当前逻辑中的 content tokens
    if not query_tokens:  # 根据当前条件决定是否进入对应业务分支
        return 0.0  # 返回当前分支整理好的结果
    return len(query_tokens & content_tokens) / len(query_tokens)  # 返回当前分支整理好的结果


def rerank(query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:  # 定义业务处理函数 rerank
    """执行二阶段精排。"""  # 函数文档字符串，说明 rerank 的职责

    query_terms = set(tokenize(query))  # 更新当前逻辑中的 query terms
    scored: list[RetrievalHit] = []  # 更新当前逻辑中的 scored
    for hit in hits:  # 遍历当前集合中的每一项并逐个处理
        content_terms = set(tokenize(hit.document.content))  # 更新当前逻辑中的 content terms
        exact_bonus = 0.08 if query and query in hit.document.content else 0.0  # 更新当前逻辑中的 exact bonus
        overlap_bonus = 0.12 * (len(query_terms & content_terms) / (len(query_terms) or 1))  # 更新当前逻辑中的 overlap bonus
        scored.append(RetrievalHit(document=hit.document, score=round(hit.score + exact_bonus + overlap_bonus, 6)))  # 执行当前业务步骤并推进后续处理
    return sorted(scored, key=lambda item: item.score, reverse=True)  # 返回当前分支整理好的结果


@lru_cache(maxsize=16)  # 为后续函数或类声明附加装饰器配置
def faq_index(scenario_id: str) -> LocalVectorIndex:  # 定义业务处理函数 faq_index
    """返回指定场景的 FAQ 向量索引。"""  # 函数文档字符串，说明 faq_index 的职责

    from app.rag.scenarios import get_scenario  # 导入二期 RAG 检索与问答服务组件

    return LocalVectorIndex(load_faq_documents(get_scenario(scenario_id)))  # 返回当前分支整理好的结果


@lru_cache(maxsize=16)  # 为后续函数或类声明附加装饰器配置
def doc_index(scenario_id: str) -> LocalVectorIndex:  # 定义业务处理函数 doc_index
    """返回指定场景的文档向量索引。"""  # 函数文档字符串，说明 doc_index 的职责

    from app.rag.scenarios import get_scenario  # 导入二期 RAG 检索与问答服务组件

    return LocalVectorIndex(load_doc_documents(get_scenario(scenario_id)))  # 返回当前分支整理好的结果


def search_faq(scenario: Scenario, query_variants: list[str], top_k: int = 5) -> tuple[list[RetrievalHit], float]:  # 定义业务处理函数 search_faq
    """检索 FAQ 向量库。"""  # 函数文档字符串，说明 search_faq 的职责

    started = time.perf_counter()  # 更新当前逻辑中的 started
    hits = faq_index(scenario.scenario_id).search(query_variants, top_k=top_k)  # 更新当前逻辑中的 hits
    return hits, (time.perf_counter() - started) * 1000  # 返回当前分支整理好的结果


def search_docs(scenario: Scenario, query_variants: list[str], top_k: int = 6) -> tuple[list[RetrievalHit], float]:  # 定义业务处理函数 search_docs
    """检索文档知识库。"""  # 函数文档字符串，说明 search_docs 的职责

    started = time.perf_counter()  # 更新当前逻辑中的 started
    hits = doc_index(scenario.scenario_id).search(query_variants, top_k=top_k)  # 更新当前逻辑中的 hits
    return hits, (time.perf_counter() - started) * 1000  # 返回当前分支整理好的结果


def clear_local_index_cache() -> dict[str, Any]:  # 定义业务处理函数 clear_local_index_cache
    """清空本地 FAQ/文档索引缓存，让下一次问答重新读取知识库文件。"""  # 函数文档字符串，说明 clear_local_index_cache 的职责

    # 先记录清理前状态，便于后台页面和接口响应展示缓存是否真的被清掉。
    before = local_index_cache_info()  # 更新当前逻辑中的 before
    # faq_index/doc_index 都是 lru_cache；cache_clear 后下一次检索会重新加载 CSV/MD 文件。
    faq_index.cache_clear()  # 执行当前业务步骤并推进后续处理
    doc_index.cache_clear()  # 执行当前业务步骤并推进后续处理
    return {"before": before, "after": local_index_cache_info()}  # 返回当前分支整理好的结果


def local_index_cache_info() -> dict[str, dict[str, int]]:  # 定义业务处理函数 local_index_cache_info
    """返回本地索引缓存命中信息，供后台状态接口展示。"""  # 函数文档字符串，说明 local_index_cache_info 的职责

    # cache_info 是 functools.lru_cache 自带的运行统计。
    faq_info = faq_index.cache_info()  # 更新当前逻辑中的 faq info
    doc_info = doc_index.cache_info()  # 更新当前逻辑中的 doc info
    return {  # 返回当前分支整理好的结果
        "faq_index": {  # 填充返回或配置中的 faq index 字段
            "hits": faq_info.hits,  # 填充返回或配置中的 hits 字段
            "misses": faq_info.misses,  # 填充返回或配置中的 misses 字段
            "maxsize": faq_info.maxsize or 0,  # 填充返回或配置中的 maxsize 字段
            "currsize": faq_info.currsize,  # 填充返回或配置中的 currsize 字段
        },  # 结束 返回结果 的定义或组装
        "doc_index": {  # 填充返回或配置中的 doc index 字段
            "hits": doc_info.hits,  # 填充返回或配置中的 hits 字段
            "misses": doc_info.misses,  # 填充返回或配置中的 misses 字段
            "maxsize": doc_info.maxsize or 0,  # 填充返回或配置中的 maxsize 字段
            "currsize": doc_info.currsize,  # 填充返回或配置中的 currsize 字段
        },  # 结束 返回结果 的定义或组装
    }  # 结束 返回结果 的定义或组装
