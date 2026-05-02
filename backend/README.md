# 后端服务

FastAPI 后端负责认证、多租户隔离、问答日志、FAQ/来源管理、反馈闭环、Dify 调用与本地 FAQ 兜底。

## 技术栈优势

- `FastAPI`：基于类型标注自动生成 OpenAPI 文档，接口参数校验清晰，适合快速交付后台管理、问答和反馈等 REST API。
- `Pydantic`：请求体、响应模型和配置读取统一校验，能在接口入口提前拦截错误数据。
- `SQLAlchemy`：业务模型集中在 `app/models/`，查询逻辑可复用，并通过启动时的兼容补列逻辑支持演示库平滑升级。
- `PyMySQL + MySQL`：与本机 Docker MySQL 配合简单，适合保存租户、账号、问答日志、FAQ、来源目录和知识包等结构化数据。
- `JWT + bcrypt`：满足前后端分离登录态和密码哈希存储要求，配合角色权限实现平台超管、租户管理员、运营人员和只读人员的能力边界。
- `Dify/RAGFlow 可配置接入`：后端通过服务层封装外部 AI 与知识库能力，未配置 API Key 或外部服务异常时可以回落到本地 FAQ。

## 启动

以下命令默认从项目根目录执行。

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 配置

本地开发配置在 `.env` 中，默认连接本机 Docker MySQL：

- database：`employment`
- user：`root`
- password：`infini_rag_flow`

`.env` 已被 git 忽略。生产部署前必须修改 `JWT_SECRET_KEY`、初始密码和 Dify/RAGFlow API Key。

## 初始化

启动时会自动建表并幂等导入演示数据。当前演示数据包含 1 个演示租户、2 个管理员账号、21 条来源目录、30 条 FAQ、1 个知识包和 4 条测试问题。也可以手动执行：

```bash
python -c "from app.database import init_db; init_db()"
```

## 初始账号

- 平台超管：`admin / Admin@123456`
- 演示租户管理员：`tenant_admin / Tenant@123456 / demo-sx`

更多说明见项目根目录的 `docs/OPERATION.md`、`docs/SECURITY_AND_TENANCY.md`。
