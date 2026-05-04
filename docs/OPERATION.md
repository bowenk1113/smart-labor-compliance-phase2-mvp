# 企业用工与社保合规智能平台操作文档

## 1. 运行地址

- 前端开发地址：`http://localhost:3000`
- 后端 API：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/docs`
- Dify Web：`http://127.0.0.1/`
- RAGFlow Web：`http://127.0.0.1:8880/`

## 2. 初始账号

| 类型 | 用户名 | 密码 | 租户编码 |
| --- | --- | --- | --- |
| 平台超级管理员 | `admin` | `Admin@123456` | 留空 |
| 演示租户管理员 | `tenant_admin` | `Tenant@123456` | `demo-sx` |

首次交付到生产环境前必须修改 `.env` 中的 `JWT_SECRET_KEY` 和初始密码。

## 3. 启动步骤

以下命令默认从项目根目录执行。

后端：

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 4. 数据库说明

项目使用本机 Docker MySQL：

- host：`127.0.0.1`
- port：`3306`
- database：`employment`
- user：`root`
- password：`infini_rag_flow`

新项目表统一使用 `slc_` 前缀。启动后会自动建表并导入演示数据，手工建表参考 `sql/init_schema.sql`。

## 5. 多租户隔离

- 租户主表：`slc_tenants`
- 所有业务表均包含 `tenant_id`
- 用户端通过 `X-Tenant-Code` 或请求体 `tenant_code` 指定租户
- 后台租户管理员只能访问本租户数据
- 超级管理员可查看所有租户并创建新租户

## 6. Dify 与 RAGFlow 接入

当前项目按“可配置接入 + 本地 FAQ 兜底”实现：

- 后台概览会探测 Dify 与 RAGFlow 在线状态
- 配置 `DIFY_API_KEY` 后，问答优先调用 Dify Chat API
- 本机 Dify + RAGFlow 检索链路可能超过 30 秒，建议在 `.env` 中设置 `DIFY_TIMEOUT_SECONDS=60`
- 未配置 Dify API Key 或调用失败时，系统使用本租户 FAQ 和来源目录生成兜底回答
- RAGFlow 当前作为知识库建设和资料整理辅助服务，后台记录 Web/API 地址与数据集映射字段
- 如果 Dify 以 Docker 容器运行并需要访问宿主机上的 RAGFlow，不要在 Dify 外部知识库 API 中使用本机临时局域网 IP。建议配置为 `http://host.docker.internal:8880/api/v1/dify`，否则容器内检索节点可能访问超时，后端会回退到本地 FAQ。

Dify 工作流建议输出结构：

```json
{
  "answer": "结论先行的自然语言回答",
  "risk_level": "low | medium | high",
  "sources": [{"title": "来源名称", "url": "官方链接", "snippet": "依据摘要"}],
  "actions": ["需要 HR 核验的事项", "员工办理路径"],
  "disclaimer": "政策时效与个案复核提示"
}
```

## 7. 安全控制

- JWT 登录认证，密码使用 bcrypt 哈希
- 角色权限：超级管理员、租户管理员、运营人员、只读人员
- 后端按 `tenant_id` 强制过滤业务数据
- 请求体大小限制与基础 IP 限流
- 安全响应头：`X-Content-Type-Options`、`X-Frame-Options` 等
- 聊天问题、反馈、备注写库前会脱敏身份证号、手机号、银行卡号和邮箱
- CORS 默认只允许本机前端开发地址

## 8. 演示数据

初始化会导入：

- 1 个演示租户：`demo-sx / 陕西演示企业`
- 2 个管理员账号
- 21 条来源目录
- 30 条 FAQ
- 1 个陕西用工与社保合规知识包
- 4 条验收测试问题

其中“陕西最低工资标准通知”等来源标记为演示/待复核口径，正式使用前需按官网最新政策核验。

## 9. 文档维护约定

- 根目录 `README.md` 维护项目总览、技术栈优势、快速启动和文档入口。
- `backend/README.md` 维护后端启动、配置、初始化和后端技术栈说明。
- `frontend/README.md` 维护前端启动、页面清单、构建和前端技术栈说明。
- `docs/DIFY_RAGFLOW_GUIDE.md` 维护 Dify/RAGFlow 分工、工作流输入输出和知识整理建议。
- `docs/SECURITY_AND_TENANCY.md` 维护租户隔离、安全控制和生产上线检查。
- 文档和种子数据中的本地资料路径统一使用相对路径；接口路径、前端路由和本地服务 URL 保持运行所需格式。
