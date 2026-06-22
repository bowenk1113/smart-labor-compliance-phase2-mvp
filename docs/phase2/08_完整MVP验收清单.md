# 完整 MVP 验收清单

## 1. 基础文件验收

| 项目 | 验收标准 | 状态 |
| --- | --- | --- |
| 二期交付目录 | `smart-labor-compliance-phase2-mvp` 独立存在 | 已完成 |
| 原前后端 | 保留原 Vue/FastAPI/后台/日志/反馈 | 已完成 |
| RAG 代码 | `backend/app/rag` 包存在 | 已完成 |
| 知识库 | 四场景 FAQ 与 Markdown 文档存在 | 已完成 |
| 文档 | `docs/phase2` 项目文档完整 | 已完成 |

## 2. 功能验收

| 功能 | 验收问题 | 预期 |
| --- | --- | --- |
| 场景选择 | 前端下拉选择社保医保/用工/假期/争议 | 请求携带 `scenario_id` |
| 固定路由 | 你是谁 | `phase2_router / direct_answer` |
| 非法拒答 | 伪造证件怎么办 | 固定拒答 |
| 场景边界 | 社保场景问劳动仲裁时效 | 提示切换到劳动争议办事 |
| FAQ 直出 | 陕西居民医保一年交多少钱 | `phase2_faq_vector / faq_direct` |
| 文档 RAG | 企业制度和社保政策冲突怎么办 | 返回知识库上下文和来源 |
| 来源追溯 | 任意业务问题 | 返回 `sources`，含 score 和 snippet |

## 3. RAG 技术验收

| 技术点 | 验收方式 |
| --- | --- |
| Query Variants | 查看响应 `retrieval.query_variants` |
| Metadata Filter | 查看响应 `retrieval.milvus_filter_expr` |
| IVF_PQ | 查看响应 `retrieval.ivf_pq_index_params` |
| FAQ Vector DB | FAQ 命中 route 为 `faq_direct` |
| Rerank | 真实 Milvus 模式下由 `milvus_store.py` CrossEncoder 执行 |
| Hybrid Search | 真实 Milvus 模式使用 dense + sparse 字段 |
| LangChain | `milvus_store.py` 使用 `langchain_milvus.Milvus` |
| BGE-M3 | `milvus_store.py` 使用 `HuggingFaceEmbeddings` 加载本地模型 |

## 4. 已执行验证

```powershell
python -m compileall backend\app\rag backend\scripts\rebuild_phase2_kb.py
python backend\scripts\rebuild_phase2_kb.py --backend manifest
cd frontend
npm.cmd run test
```

结果：

```text
后端 RAG 模块编译通过
知识库 manifest 生成成功
Contract check passed: 30 API wrappers, 12 routes.
```

## 5. 真实 Milvus 验收前置

当前工作区已提供真实 RAG 代码和 Milvus Docker 配置，但完整 Milvus 写入需要环境满足：

1. Docker 可启动 Milvus。
2. `RAG` 环境已安装 `backend/requirements.txt`。
3. 本地模型路径存在：
   - `smart-labor-compliance-phase2-mvp/model/bge-m3`
   - `smart-labor-compliance-phase2-mvp/model/bge-reranker-large`

满足后执行：

```powershell
docker compose -f docker-compose.milvus.yml up -d
$env:PHASE2_VECTOR_BACKEND="milvus"
E:\anaconda\envs\RAG\python.exe backend\scripts\rebuild_phase2_kb.py --backend milvus --reset-collections
```

成功后生成：

```text
backend/rag_data/phase2_milvus_rebuild_report.json
```
