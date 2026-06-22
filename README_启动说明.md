# 项目启动说明

本文档用于把本项目直接发给其他同事、老师或客户后，指导对方在自己的电脑上完成启动。

项目名称：

- `smart-labor-compliance-phase2-mvp`

本文档提供两种启动方式：

1. 本地演示版：不依赖 Milvus，最快启动，适合演示页面和完整业务流程。
2. Milvus 完整版：启用真实 RAG、真实向量库和混合检索，适合技术验收。

---

## 一、项目中包含的重要内容

请确保发送项目时，以下目录和文件一并发送：

- `backend/`
- `frontend/`
- `model/`
- `scripts/`
- `docker-compose.milvus.dedicated.yml`
- `start_project.bat`
- `start_production_backend.bat`

其中最重要的是本地模型目录：

- `model/bge-m3`
- `model/bge-reranker-large`

如果缺少这两个模型目录，真实 RAG / Milvus 模式无法正常运行。

---

## 二、对方电脑需要提前安装什么

### 1. 本地演示版需要

- Python
- Node.js

建议版本：

- Python 3.10 或 3.11
- Node.js 18 及以上

### 2. Milvus 完整版额外需要

- Docker Desktop

并确保 Docker Desktop 已启动。

---

## 三、解压后的目录要求

对方拿到项目后，先把项目放到一个本地目录，例如：

```text
C:\Projects\smart-labor-compliance-phase2-mvp
```

然后打开 PowerShell 或 CMD，进入项目根目录。

例如：

```powershell
cd C:\Projects\smart-labor-compliance-phase2-mvp
```

---

## 四、启动方式一：本地演示版

本方式不依赖 Docker，不依赖 Milvus，最适合首次打开项目。

### 步骤 1：进入项目根目录

```powershell
cd 项目根目录
```

### 步骤 2：如果需要，指定 Python

如果对方电脑有多个 Python，建议先指定项目要使用的 Python：

```powershell
$env:PYTHON_BIN="你的Python.exe完整路径"
```

例如：

```powershell
$env:PYTHON_BIN="C:\Users\用户名\AppData\Local\Programs\Python\Python311\python.exe"
```

如果只有一个 Python，可以跳过这一步。

### 步骤 3：安装依赖并启动项目

```powershell
.\start_project.bat -InstallDeps
```

说明：

- 这一步会自动安装后端和前端依赖
- 本地演示版默认使用 `local` 向量检索模式
- 不需要 Docker

### 步骤 4：打开页面

启动成功后，可访问：

- 前端页面：`http://localhost:3000`
- 后端接口文档：`http://127.0.0.1:8000/docs`

---

## 五、启动方式二：Milvus 完整版

本方式用于演示真实 RAG、真实向量库、Hybrid Search 混合检索和重排序。

### 步骤 1：启动 Docker Desktop

确认 Docker Desktop 已启动，并且可以正常执行：

```powershell
docker version
```

### 步骤 2：进入项目根目录

```powershell
cd 项目根目录
```

### 步骤 3：启动项目专用的 Milvus

```powershell
docker compose -f docker-compose.milvus.dedicated.yml up -d
```

查看状态：

```powershell
docker compose -f docker-compose.milvus.dedicated.yml ps
```

正常应看到以下容器为 `Up`：

- `slc_phase2_etcd_dedicated`
- `slc_phase2_minio_dedicated`
- `slc_phase2_milvus_dedicated`

### 步骤 4：如果需要，指定 Python

建议指定完整 Python 路径，避免项目自动选错环境：

```powershell
$env:PYTHON_BIN="你的Python.exe完整路径"
```

### 步骤 5：设置 Milvus 相关环境变量

```powershell
$env:PHASE2_VECTOR_BACKEND="milvus"
$env:MILVUS_URI="http://127.0.0.1:19531"
$env:PHASE2_FAQ_COLLECTION="slc_phase2_faq_vectors_dedicated"
$env:PHASE2_DOC_COLLECTION="slc_phase2_doc_vectors_dedicated"
```

### 步骤 6：把知识库写入 Milvus

```powershell
python backend\scripts\rebuild_phase2_kb.py --backend milvus --reset-collections
```

执行成功后，终端会输出：

- FAQ collection 名称
- 文档 collection 名称
- 各场景 FAQ 数量
- 各场景文档 chunk 数量

并生成报告文件：

- `backend/rag_data/phase2_milvus_rebuild_report.json`

### 步骤 7：安装依赖并启动项目

```powershell
.\start_project.bat -InstallDeps -VectorBackend milvus
```

### 步骤 8：打开页面

启动成功后，可访问：

- 前端页面：`http://localhost:3000`
- 后端接口文档：`http://127.0.0.1:8000/docs`

---

## 六、项目当前使用的 Milvus 配置

为了避免和其他项目冲突，本项目已经做了物理隔离和逻辑隔离。

### 物理隔离

- 独立 Compose 文件：`docker-compose.milvus.dedicated.yml`
- 独立 Milvus 端口：`19531`
- 独立 MinIO 端口：`9010`
- 独立 MinIO Console 端口：`9011`
- 独立 Etcd 端口：`2389`
- 独立存储目录：`storage/milvus_dedicated/`

### 逻辑隔离

- FAQ collection：`slc_phase2_faq_vectors_dedicated`
- 文档 collection：`slc_phase2_doc_vectors_dedicated`

---

## 七、FAQ 管理页和 Milvus 的关系

项目里的“FAQ 管理”页面显示的是后台数据库中的 FAQ，不是直接显示 Milvus 中的数据。

数据链路如下：

1. 前端 FAQ 页面新增 / 修改 / 删除 FAQ
2. 后端先更新数据库
3. 后端导出 `faq_runtime.csv`
4. `local` 模式下，本地 RAG 可直接读取更新后的 FAQ
5. `milvus` 模式下，需要再次执行一次 Milvus 重建，FAQ 才会真正进入向量库

也就是说：

- FAQ 页面数据源：数据库
- Milvus 数据源：FAQ / 文档重建后的向量化结果

---

## 八、如何查看 Milvus 中的数据

如果对方安装了 Attu，可以连接项目自己的 Milvus：

- Host：`127.0.0.1`
- Port：`19531`
- Database：`default`

连接后可查看两个 collection：

- `slc_phase2_faq_vectors_dedicated`
- `slc_phase2_doc_vectors_dedicated`

注意：

- 前端新增 FAQ，不会新增新的 collection
- 新 FAQ 会进入现有的 FAQ collection 中

---

## 九、常见问题

### 1. 为什么启动脚本没有使用当前激活的 conda 环境

项目启动脚本会按自己的优先级选择 Python，不一定直接使用当前终端激活的环境。

最稳妥的做法是手动指定：

```powershell
$env:PYTHON_BIN="你的Python.exe完整路径"
```

然后再启动：

```powershell
.\start_project.bat -InstallDeps
```

或：

```powershell
.\start_project.bat -InstallDeps -VectorBackend milvus
```

### 2. Docker 启动 Milvus 时端口冲突怎么办

不要使用旧的 `docker-compose.milvus.yml`，请使用：

```powershell
docker compose -f docker-compose.milvus.dedicated.yml up -d
```

因为当前项目已经切换到独立端口：

- `19531`
- `9010`
- `9011`
- `2389`

### 3. 为什么 FAQ 新增后 Attu 里 collection 数量没变

因为项目本来就只使用两个 collection：

- 一个 FAQ collection
- 一个文档 collection

新增 FAQ 只是往 FAQ collection 里新增记录，不会新增第三个 collection。

### 4. 为什么第一次 Milvus 重建看起来像卡住了

第一次重建通常需要：

- 加载本地 embedding 模型
- 加载 reranker 模型
- 读取 FAQ 和文档
- 生成向量
- 写入 Milvus 并构建索引

因此第一次执行时间会比较长，属于正常现象。

---

## 十、最简启动命令汇总

### 本地演示版

```powershell
cd 项目根目录
$env:PYTHON_BIN="你的Python.exe完整路径"
.\start_project.bat -InstallDeps
```

### Milvus 完整版

```powershell
cd 项目根目录
docker compose -f docker-compose.milvus.dedicated.yml up -d
$env:PYTHON_BIN="你的Python.exe完整路径"
$env:PHASE2_VECTOR_BACKEND="milvus"
$env:MILVUS_URI="http://127.0.0.1:19531"
$env:PHASE2_FAQ_COLLECTION="slc_phase2_faq_vectors_dedicated"
$env:PHASE2_DOC_COLLECTION="slc_phase2_doc_vectors_dedicated"
python backend\scripts\rebuild_phase2_kb.py --backend milvus --reset-collections
.\start_project.bat -InstallDeps -VectorBackend milvus
```

---

## 十一、补充说明

如果对方只是看业务流程和页面，不需要真实向量库，推荐直接使用“本地演示版”。

如果对方要验收 RAG 技术实现、Milvus、混合检索、Attu 查看 collection，推荐使用“Milvus 完整版”。
