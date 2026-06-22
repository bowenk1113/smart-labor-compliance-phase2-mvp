"""重建二期 MVP 知识库。

脚本用于教学和交付演示：
1. 扫描四个场景的 FAQ 和 Markdown 文档。
2. 输出知识库清单，便于核对每个场景入库数量。
3. 使用 `--backend milvus` 时，把 FAQ 和文档真实写入 Milvus。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

import argparse  # 导入当前模块运行所依赖的工具或类型
import json  # 导入 JSON 编解码工具，处理结构化字段
import sys  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 执行当前业务步骤并推进后续处理

from app.rag.scenarios import SCENARIOS  # 导入二期 RAG 检索与问答服务组件
from app.rag.store import build_filter_expr, load_doc_documents, load_faq_documents, milvus_ivf_pq_index_params  # 导入二期 RAG 检索与问答服务组件


def build_manifest() -> dict:  # 定义业务处理函数 build_manifest
    """生成二期知识库清单。"""  # 函数文档字符串，说明 build_manifest 的职责
    manifest = {  # 更新当前逻辑中的 manifest
        "project": "smart-labor-compliance-phase2-mvp",  # 填充返回或配置中的 project 字段
        "vector_db": "Milvus",  # 填充返回或配置中的 vector db 字段
        "index_type": "IVF_PQ",  # 填充返回或配置中的 index type 字段
        "index_params": milvus_ivf_pq_index_params(),  # 填充返回或配置中的 index params 字段
        "scenarios": [],  # 填充返回或配置中的 scenarios 字段
    }  # 结束 manifest 的定义或组装
    for scenario in SCENARIOS.values():  # 遍历当前集合中的每一项并逐个处理
        faqs = load_faq_documents(scenario)  # 更新当前逻辑中的 faqs
        docs = load_doc_documents(scenario)  # 更新当前逻辑中的 docs
        manifest["scenarios"].append(  # 执行当前业务步骤并推进后续处理
            {  # 执行当前业务步骤并推进后续处理
                "scenario_id": scenario.scenario_id,  # 执行当前业务步骤并推进后续处理
                "label": scenario.label,  # 执行当前业务步骤并推进后续处理
                "faq_records": len(faqs),  # 执行当前业务步骤并推进后续处理
                "doc_chunks": len(docs),  # 执行当前业务步骤并推进后续处理
                "faq_filter_expr": build_filter_expr(scenario_id=scenario.scenario_id, source_type="faq"),  # 执行当前业务步骤并推进后续处理
                "doc_filter_expr": build_filter_expr(scenario_id=scenario.scenario_id, source_type="doc"),  # 执行当前业务步骤并推进后续处理
            }  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理
    return manifest  # 返回当前分支整理好的结果


def write_json(payload: dict, file_name: str) -> Path:  # 定义业务处理函数 write_json
    """把重建结果写入 rag_data 目录。"""  # 函数文档字符串，说明 write_json 的职责

    output = Path(__file__).resolve().parents[1] / "rag_data" / file_name  # 创建内存输出缓冲区
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")  # 执行当前业务步骤并推进后续处理
    return output  # 返回当前分支整理好的结果


def main() -> None:  # 定义业务处理函数 main
    """执行知识库重建。"""  # 函数文档字符串，说明 main 的职责

    parser = argparse.ArgumentParser(description="Rebuild phase2 FAQ/doc RAG knowledge base.")  # 更新当前逻辑中的 parser
    parser.add_argument("--backend", choices=["manifest", "milvus"], default="manifest", help="manifest 只生成清单；milvus 写入真实 Milvus。")  # 执行当前业务步骤并推进后续处理
    parser.add_argument("--reset-collections", action="store_true", help="仅 backend=milvus 时生效，删除旧 collection 后重建。")  # 执行当前业务步骤并推进后续处理
    args = parser.parse_args()  # 更新当前逻辑中的 args

    if args.backend == "milvus":  # 根据当前条件决定是否进入对应业务分支
        from app.rag.milvus_store import rebuild_milvus_collections  # 导入二期 RAG 检索与问答服务组件

        payload = rebuild_milvus_collections(reset_collections=args.reset_collections)  # 组装发往外部问答服务的请求载荷
        output = write_json(payload, "phase2_milvus_rebuild_report.json")  # 创建内存输出缓冲区
        print(json.dumps(payload, ensure_ascii=False, indent=2))  # 执行当前业务步骤并推进后续处理
        print(f"\nMilvus rebuild report saved: {output}")  # 执行当前业务步骤并推进后续处理
        return  # 结束当前函数并返回空结果

    manifest = build_manifest()  # 更新当前逻辑中的 manifest
    output = write_json(manifest, "phase2_kb_manifest.json")  # 创建内存输出缓冲区
    print(json.dumps(manifest, ensure_ascii=False, indent=2))  # 执行当前业务步骤并推进后续处理
    print(f"\nmanifest saved: {output}")  # 执行当前业务步骤并推进后续处理


if __name__ == "__main__":  # 根据当前条件决定是否进入对应业务分支
    main()  # 执行当前业务步骤并推进后续处理
