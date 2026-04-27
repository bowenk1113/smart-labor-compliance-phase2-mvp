# 企业用工与社保合规智能平台 - 后端

## 一、项目概述

本项目是基于 Python FastAPI + MySQL 的后端服务，为企业用工与社保合规智能平台提供 API 接口支持。首期 MVP 聚焦陕西地区用工与社保合规场景。

## 二、技术栈

- **Python 3.x**
- **FastAPI** - Web 框架
- **SQLAlchemy** - ORM
- **PyMySQL** - MySQL 驱动
- **python-jose** - JWT 令牌
- **passlib/bcrypt** - 密码加密
- **Uvicorn** - ASGI 服务器

## 三、项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # 应用入口
│   ├── database.py          # 数据库连接
│   ├── security.py          # 安全相关（JWT、密码）
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── chat_log.py
│   │   ├── feedback.py
│   │   ├── faq.py
│   │   ├── source.py
│   │   ├── knowledge_package.py
│   │   └── admin.py
│   ├── schemas/             # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── feedback.py
│   │   ├── faq.py
│   │   ├── source.py
│   │   └── admin.py
│   ├── routers/             # 路由
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── history.py
│   │   ├── feedback.py
│   │   └── admin.py
│   └── services/            # 业务逻辑
│       ├── __init__.py
│       └── dify_service.py
├── requirements.txt
└── README.md
```

## 四、快速开始

### 4.1 安装依赖

```bash
pip install -r requirements.txt
```

### 4.2 配置数据库

在 `app/database.py` 中修改数据库连接配置：

```python
DATABASE_URL = "mysql+pymysql://username:password@localhost:3306/database_name"
```

### 4.3 初始化数据库

```bash
python -c "from app.database import init_db; init_db()"
```

### 4.4 创建管理员账号

```bash
python -c "from app.security import create_admin; create_admin('admin', 'admin123')"
```

### 4.5 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，访问 `http://localhost:8000/docs` 查看 API 文档。

## 五、API 接口列表

### 5.1 用户端接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 问答 | POST | /api/chat | 提交问题获取回答 |
| 历史记录 | GET | /api/history | 获取用户历史记录 |
| 清空历史 | DELETE | /api/history | 清空用户历史记录 |
| 反馈 | POST | /api/feedback | 提交反馈 |
| 推荐问题 | GET | /api/recommended-questions | 获取推荐问题 |

### 5.2 管理端接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 登录 | POST | /api/admin/login | 管理员登录 |
| 验证令牌 | GET | /api/admin/verify-token | 验证 JWT 令牌 |
| 统计 | GET | /api/admin/statistics | 获取统计数据 |
| 问答日志 | GET | /api/admin/logs | 获取问答日志列表 |
| 日志详情 | GET | /api/admin/logs/{id} | 获取日志详情 |
| 反馈列表 | GET | /api/admin/feedbacks | 获取反馈列表 |
| 更新反馈 | PUT | /api/admin/feedbacks/{id} | 更新反馈状态 |
| FAQ列表 | GET | /api/admin/faqs | 获取 FAQ 列表 |
| 添加FAQ | POST | /api/admin/faqs | 添加 FAQ |
| 更新FAQ | PUT | /api/admin/faqs/{id} | 更新 FAQ |
| 删除FAQ | DELETE | /api/admin/faqs/{id} | 删除 FAQ |
| 来源列表 | GET | /api/admin/sources | 获取来源列表 |
| 添加来源 | POST | /api/admin/sources | 添加来源 |
| 更新来源 | PUT | /api/admin/sources/{id} | 更新来源 |
| 删除来源 | DELETE | /api/admin/sources/{id} | 删除来源 |
| 知识包列表 | GET | /api/admin/knowledge-packages | 获取知识包列表 |
| 更新状态 | PUT | /api/admin/knowledge-packages/{id}/status | 更新知识包状态 |

## 六、数据库表结构

### 6.1 问答记录表 (chat_logs)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键，自增 |
| user_id | VARCHAR(64) | 用户ID |
| session_id | VARCHAR(64) | 会话ID |
| question | TEXT | 用户问题 |
| answer | TEXT | 系统回答 |
| sources | JSON | 来源列表 |
| related_tasks | JSON | 办事路径 |
| response_time | INT | 响应时间（毫秒） |
| status | VARCHAR(20) | 状态（success/failed） |
| created_at | DATETIME | 创建时间 |

### 6.2 反馈记录表 (feedbacks)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键，自增 |
| question_id | INT | 问答记录ID |
| user_id | VARCHAR(64) | 用户ID |
| is_helpful | BOOLEAN | 是否有帮助 |
| remark | TEXT | 备注 |
| status | VARCHAR(20) | 处理状态 |
| created_at | DATETIME | 创建时间 |

### 6.3 FAQ 表 (faqs)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键，自增 |
| question | VARCHAR(500) | 问题 |
| answer | TEXT | 答案 |
| category | VARCHAR(50) | 分类 |
| keywords | JSON | 关键词 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 6.4 来源目录表 (sources)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键，自增 |
| title | VARCHAR(200) | 文档标题 |
| url | VARCHAR(500) | 文档链接 |
| doc_type | VARCHAR(20) | 文档类型 |
| region | VARCHAR(50) | 适用地区 |
| publish_date | DATE | 发布日期 |
| description | TEXT | 描述 |
| created_at | DATETIME | 创建时间 |

### 6.5 知识包表 (knowledge_packages)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键，自增 |
| name | VARCHAR(100) | 知识包名称 |
| region | VARCHAR(50) | 适用地区 |
| description | TEXT | 描述 |
| status | VARCHAR(20) | 状态 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 6.6 管理员表 (admins)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键，自增 |
| username | VARCHAR(50) | 用户名 |
| password_hash | VARCHAR(200) | 密码哈希 |
| role | VARCHAR(20) | 角色 |
| created_at | DATETIME | 创建时间 |

## 七、Dify 集成

### 7.1 配置

在 `app/services/dify_service.py` 中配置 Dify API：

```python
DIFY_API_KEY = "your-api-key"
DIFY_BASE_URL = "https://api.dify.ai/v1"
```

### 7.2 调用方式

服务通过调用 Dify Chatflow API 获取智能回答，支持：
- 知识检索
- 语义召回
- 问答生成

## 八、安全配置

### 8.1 JWT 配置

```python
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24小时
```

### 8.2 密码加密

使用 bcrypt 进行密码哈希存储。

## 九、默认数据

### 9.1 推荐问题

系统预置以下推荐问题：
- 陕西产假多少天
- 西安劳动仲裁去哪里
- 居民医保断缴后怎么处理
- 试用期工资标准
- 加班费计算方式

### 9.2 默认管理员

- 用户名：admin
- 密码：admin123

## 十、后续扩展

### 10.1 多租户支持

- 企业账号体系
- 企业独立知识库
- 数据隔离

### 10.2 Dify 扩展

- 支持多个知识包
- 支持自定义 Prompt
- 支持知识库更新同步

---

**文档版本**：V1.0  
**创建日期**：2026年4月26日  
**项目名称**：企业用工与社保合规智能平台