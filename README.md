# 企业用工与社保合规智能平台二期 MVP

本目录是原 `smart-labor-compliance` 的二期 MVP 交付版，新增了场景选择、多路由边界检测、FAQ 向量直出和 RAG 检索增强。

二期文档入口：

- [二期 MVP 项目书](docs/phase2/01_二期MVP项目书.md)
- [业务框架图](docs/phase2/02_业务框架图.md)
- [代码架构图](docs/phase2/03_代码架构图.md)
- [实现步骤](docs/phase2/04_实现步骤.md)
- [人员分工与工期](docs/phase2/05_人员分工与工期.md)
- [交付与运行说明](docs/phase2/06_交付与运行说明.md)
- [RAG 技术实现说明](docs/phase2/07_RAG技术实现说明.md)
- [完整 MVP 验收清单](docs/phase2/08_完整MVP验收清单.md)
- [详细启动与排错手册](docs/phase2/09_详细启动与排错手册.md)
- [核心 RAG 链路流程图对齐说明](docs/phase2/10_核心RAG链路流程图对齐说明.md)
- [前端界面查看与导包排错](docs/phase2/11_前端界面查看与导包排错.md)
- [知识库实时更新说明](docs/phase2/12_知识库实时更新说明.md)

## 二期新增能力

- 前端新增四个内部场景选择：社保医保合规、用工合规、假期福利、劳动争议办事。
- 后端新增固定路由：问候、身份、感谢、转人工、非法内容和平台越界直接回答。
- 后端新增场景边界检测：用户选错内部场景时提示切换，避免错误检索。
- FAQ 改为按场景组织的向量知识库形式，高置信命中直接返回标准答案。
- 未命中 FAQ 时进入文档 RAG 检索，返回来源、相关性分数和风险提示。
- 提供 Milvus Docker Compose、IVF_PQ 参数、过滤表达式和知识库重建清单脚本。

基于 `Vue 3 + FastAPI + MySQL + Dify + RAGFlow` 的前后端分离项目。首期聚焦陕西地区企业用工、社保、医保、假期和劳动争议场景，支持多租户、数据隔离、后台知识运营、问答日志、反馈闭环和测试数据验收。

## 核心能力

- 前后端分离：`frontend/` 与 `backend/` 独立运行
- 本机 Docker MySQL：默认使用 `employment` 数据库
- 多租户：新增租户、租户管理员、本租户数据隔离
- 安全：JWT、bcrypt、敏感信息脱敏、限流、请求体限制、安全响应头
- 智能问答：Dify API Key 可配置，未配置时使用本地 FAQ 兜底
- RAGFlow 配合：用于资料整理、知识卡和知识库建设
- 国际化：前端支持中文与英文切换
- 演示数据：启动自动导入租户、账号、来源、FAQ、知识包和测试问题

## 技术栈与选型优势

| 层级 | 技术 | 选择优势 |
| --- | --- | --- |
| 前端 | Vue 3 + Vite | Vue 3 组合式 API 适合拆分复杂后台页面，Vite 启动和热更新速度快，便于快速迭代用户问答台与管理后台。 |
| 后端 | Python + FastAPI | FastAPI 原生支持类型标注、Pydantic 校验和 OpenAPI 文档，适合承载多租户 API、问答接口和后台管理接口。 |
| 数据库 | MySQL + SQLAlchemy | MySQL 易部署、运维成本低，适合保存租户、日志、FAQ、来源目录等结构化数据；SQLAlchemy 让模型、查询和兼容迁移更集中。 |
| 安全 | JWT + bcrypt + 脱敏中间件 | JWT 适合前后端分离认证，bcrypt 保护密码哈希，后端统一脱敏和限流可降低日志与接口侧的数据泄露风险。 |
| AI 编排 | Dify | Dify 负责 Chatflow、Prompt 约束和模型接入，让业务后端保持稳定，AI 能力可以独立调优和替换。 |
| 知识整理 | RAGFlow | RAGFlow 适合政策资料清洗、知识卡整理和人工复核，补齐原始法规、网页和企业制度进入问答前的治理环节。 |

整体架构采用“业务系统稳定落库 + AI 能力可配置接入 + 本地 FAQ 兜底”的方式：即使 Dify 或 RAGFlow 暂不可用，核心后台、日志、来源目录和高频 FAQ 仍可运行。

## 项目结构

```text
.
├── backend/                 # FastAPI 后端、模型、路由、服务与演示数据
├── frontend/                # Vue 3 + Vite 前端
├── docs/                    # 运维、安全、多租户、Dify/RAGFlow 配合文档
├── sql/                     # MySQL 初始化参考脚本
├── 后端需求文档.md
├── 前端需求文档.md
└── 企业用工与社保合规智能平台项目书_商业化正式版.md
```

## 快速启动

以下命令默认从项目根目录执行。

先做环境预检：

```powershell
.\check_project.bat
```

Windows PowerShell / CMD 推荐使用：

```powershell
.\start_project.bat -InstallDeps
```

默认 local 模式安装轻量运行依赖；真实 Milvus RAG 模式才安装完整 RAG 依赖。

Windows 一键脚本和后端默认配置都使用 SQLite 本地库，数据库文件位于 `backend/storage/slc_phase2.db`，不会再因为本机 MySQL 密码不一致导致 MVP 打不开。

如果页面打不开，先看预检结果。当前最常见原因是：

- RAG Python 环境缺少后端运行包。
- `frontend/node_modules` 不存在，需要执行 `npm install`。

一键修复命令仍是：

```powershell
.\start_project.bat -InstallDeps
```

停止：

```powershell
.\stop_project.bat
```

## 生产部署启动

当前电脑没有安装 Nginx，因此生产部署采用“FastAPI 单服务托管前端”的方式：

```text
浏览器 -> FastAPI 8000 -> frontend/dist 静态文件
                       -> /api 后端接口
FastAPI -> MySQL + Milvus + Dify/Qwen/DeepSeek
```

这种方式不需要 Nginx。前端页面和后端 API 共用一个端口，生产访问地址是：

```text
http://服务器IP:8000
```

例如：

```text
http://192.168.11.71:8000
```

### 1. 构建前端静态文件

推荐使用项目脚本：

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp
.\build_production.bat -InstallDeps
```

也可以手工执行：

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp\frontend
npm install
npm run build
```

构建产物位于：

```text
C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp\frontend\dist
```

生产环境由 FastAPI 直接托管 `frontend/dist`。不要再使用测试环境的：

```text
http://服务器IP:3000
```

### 2. 配置后端生产环境变量

编辑：

```text
C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp\backend\.env
```

MySQL + Milvus + OpenAI-compatible 大模型示例：

```env
DB_BACKEND=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=employment

SERVE_FRONTEND=true
FRONTEND_DIST_PATH=../frontend/dist

PHASE2_VECTOR_BACKEND=milvus
PHASE2_KB_VERSION=phase2_mvp
MILVUS_URI=http://127.0.0.1:19530

PHASE2_GENERATION_BACKEND=auto
PHASE2_LLM_BASE_URL=https://api.deepseek.com
PHASE2_LLM_API_KEY=你的DeepSeek或Qwen API Key
PHASE2_LLM_MODEL=deepseek-chat
PHASE2_LLM_TEMPERATURE=0.2
PHASE2_LLM_TIMEOUT_SECONDS=30

PHASE2_QUERY_LLM_ENABLED=true
PHASE2_QUERY_LLM_BACKEND=openai_compatible
PHASE2_QUERY_LLM_MAX_VARIANTS=4
PHASE2_QUERY_LLM_TEMPERATURE=0.1
```

如果使用 Qwen，把大模型部分改为：

```env
PHASE2_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PHASE2_LLM_MODEL=qwen-plus
```

如果暂时没有 MySQL，可以先保留 SQLite：

```env
DB_BACKEND=sqlite
SQLITE_PATH=storage/slc_phase2.db
SERVE_FRONTEND=true
FRONTEND_DIST_PATH=../frontend/dist
```

但正式上线建议使用 MySQL。

### 3. 启动 Milvus 向量库

如果本机已经有 `knowforge-milvus` 容器在运行，并且暴露了 `127.0.0.1:19530`，可以跳过本步骤，直接复用现有 Milvus。

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp
docker compose -f docker-compose.milvus.yml up -d
```

检查容器：

```powershell
docker compose -f docker-compose.milvus.yml ps
```

如果启动时出现 `failed to resolve reference docker.io/...`，表示 Docker 正在拉取镜像但访问 Docker Hub 失败。优先检查本机是否已有可用容器：

```powershell
docker ps
```

看到 `knowforge-milvus` 且端口包含 `0.0.0.0:19530->19530/tcp` 时，说明 Milvus 已可用，不需要重复拉取镜像。

### 4. 安装后端完整依赖

生产 RAG 模式需要完整依赖，包括 LangChain、Milvus、Embedding 和 Reranker：

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp
E:\anaconda\envs\RAG\python.exe -m pip install -r backend\requirements.txt
```

如果之前环境中已经装过部分包，但重建 Milvus 时提示 `No module named 'filelock'` 或 `Could not import sentence_transformers`，再次执行上面的完整安装命令即可补齐依赖。

如果 `pip install -r backend\requirements.txt` 提示 `pydantic-settings` 与 `langchain-community` 冲突，请确保当前代码中的 requirements 已更新为 `pydantic-settings==2.10.1`，然后重新执行安装。

如果提示 `langchain-core` 与 `langchain-milvus` 冲突，请确保当前代码中的 requirements 已把 `langchain-milvus` 调整为与 `langchain 0.3.x` 兼容的版本，然后重新执行安装。

### 5. 重建 Milvus 知识库

首次生产部署或知识库批量更新后，执行：

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp
E:\anaconda\envs\RAG\python.exe backend\scripts\rebuild_phase2_kb.py --backend milvus --reset-collections
```

后台 FAQ 修改后的 MVP 实时更新说明见：

```text
docs/phase2/12_知识库实时更新说明.md
```

### 6. 启动后端生产服务

推荐使用项目脚本启动生产后端：

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp
.\start_production_backend.bat -InstallDeps -BackendPort 8000 -Workers 2
```

默认情况下，生产启动脚本会自动设置：

```text
SERVE_FRONTEND=true
AUTO_SEED=true
```

也就是说，后端启动后会直接托管 `frontend/dist`，不需要 Nginx。

停止生产后端：

```powershell
.\stop_production_backend.bat
```

这个脚本会自动读取 `backend/.env`，并把其中的 MySQL、Milvus、DeepSeek/Qwen API Key 等配置注入后端进程。

也可以手工启动。生产启动不要加 `--reload`，可以使用多 worker：

```powershell
cd C:\Users\k1502\Desktop\Project\smart-labor-compliance-phase2-mvp\backend
E:\anaconda\envs\RAG\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

验证后端：

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

验证前端页面：

```text
http://127.0.0.1:8000
http://192.168.11.71:8000
```

Windows 生产服务器建议进一步把该命令注册为 NSSM、Windows Service、计划任务或 Supervisor 托管进程，避免命令行窗口关闭后服务停止。

如果局域网其他电脑访问不了，需要检查 Windows 防火墙是否放行 `8000` 端口。

### 7. 生产部署检查清单

```text
1. npm run build 已生成 frontend/dist。
2. backend/.env 已填写 MySQL、Milvus、大模型 API Key。
3. Docker Milvus 已启动。
4. Milvus 知识库已 rebuild。
5. FastAPI 后端通过 start_production_backend.bat 或 --host 0.0.0.0 --workers 2 启动，且没有 --reload。
6. SERVE_FRONTEND=true，FastAPI 已托管 frontend/dist。
7. 浏览器访问 http://服务器IP:8000，而不是 http://服务器IP:3000。
8. Windows 防火墙放行 8000 端口。
```

## 源码注释说明

二期核心代码的注释已经直接写在原源码中，重点覆盖 RAG Pipeline、检索准备、FAQ 向量直出、混合检索、回答来源、知识库实时更新和前端场景选择等链路。

真实 Milvus RAG 模式：

```powershell
docker compose -f docker-compose.milvus.yml up -d
.\start_project.bat -InstallDeps -VectorBackend milvus
```

`scripts/start_project.sh` 是 Bash 脚本，只适合 Git Bash、WSL 或 Linux/macOS 终端。

如果使用 Bash，可运行：

```bash
./scripts/start_project.sh
```

访问 `http://localhost:3000`。停止项目：

```bash
./scripts/stop_project.sh
```

如需手工排障，也可以分别启动：

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## 初始账号

- 平台超管：`admin / Admin@123456`
- 演示租户管理员：`tenant_admin / Tenant@123456 / demo-sx`

## 文档

- [操作文档](docs/OPERATION.md)
- [Dify 与 RAGFlow 配合开发指南](docs/DIFY_RAGFLOW_GUIDE.md)
- [安全与多租户设计说明](docs/SECURITY_AND_TENANCY.md)
- [MySQL 初始化参考](sql/init_schema.sql)
- [后端需求文档](后端需求文档.md)
- [前端需求文档](前端需求文档.md)
- [商业化项目书](企业用工与社保合规智能平台项目书_商业化正式版.md)

## 重要说明

演示数据中含部分“待复核/演示口径”的政策来源，正式上线前必须按陕西省人社厅、医保局、西安市人社局等官方渠道核验最新口径。
