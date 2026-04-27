# 企业用工与社保合规智能平台 - 前端

## 一、项目概述

本项目是基于 Vue 3 + Vite 的前端应用，为企业用工与社保合规智能平台提供用户界面。首期 MVP 聚焦陕西地区用工与社保合规场景。

## 二、技术栈

- **Vue 3** - 渐进式前端框架
- **Vite** - 构建工具
- **Vue Router** - 路由管理
- **Pinia** - 状态管理
- **Axios** - HTTP 客户端

## 三、项目结构

```
frontend/
├── public/
├── src/
│   ├── api/                 # API 接口
│   │   └── index.js         # 所有 API 函数
│   ├── assets/              # 静态资源
│   │   └── main.css         # 全局样式
│   ├── components/          # 公共组件
│   ├── router/              # 路由配置
│   │   └── index.js         # 路由及权限守卫
│   ├── views/               # 页面组件
│   │   ├── Home.vue         # 用户首页（问答）
│   │   ├── History.vue      # 历史记录
│   │   └── admin/           # 管理端页面
│   │       ├── Login.vue    # 登录页
│   │       ├── Dashboard.vue # 概览页
│   │       ├── Logs.vue     # 问答日志
│   │       ├── Feedbacks.vue # 反馈管理
│   │       ├── Faqs.vue     # FAQ管理
│   │       ├── Sources.vue  # 来源管理
│   │       └── Packages.vue # 知识包管理
│   ├── App.vue              # 根组件
│   └── main.js              # 入口文件
├── index.html               # HTML 模板
├── vite.config.js           # Vite 配置
├── package.json             # 依赖配置
└── README.md                # 说明文档
```

## 四、快速开始

### 4.1 安装依赖

```bash
cd frontend
npm install
```

### 4.2 启动开发服务器

```bash
npm run dev
```

服务启动后，访问 `http://localhost:5173`

### 4.3 构建生产版本

```bash
npm run build
```

## 五、页面功能

### 5.1 用户端

#### 首页 (Home)
- 智能问答输入框
- 推荐问题快捷入口
- 回答展示区（包含来源、办事路径）
- 反馈功能（有帮助/无帮助）
- 回答满意度评价

#### 历史记录 (History)
- 分页展示历史问答记录
- 查看详情
- 清空历史功能

### 5.2 管理端

#### 登录页 (Login)
- 管理员账号登录
- JWT 令牌存储

#### 概览 (Dashboard)
- 统计卡片（总问题数、今日问题、总反馈、待处理、FAQ数、来源数）
- 快捷操作入口

#### 问答日志 (Logs)
- 分页列表展示
- 关键词搜索
- 日期范围筛选
- 查看详情弹窗

#### 反馈管理 (Feedbacks)
- 分页列表展示
- 状态筛选（待处理/已处理）
- 更新处理状态

#### FAQ管理 (Faqs)
- 分页列表展示
- 添加/编辑/删除 FAQ
- 分类和关键词管理

#### 来源管理 (Sources)
- 分页列表展示
- 添加/编辑/删除 来源
- 文档类型和地区筛选

#### 知识包管理 (Packages)
- 知识包列表展示
- 启用/禁用状态切换
- 查看详情

## 六、API 接口

前端通过 `/api` 路径调用后端接口，Vite 配置了代理将请求转发到后端服务。

### 6.1 用户端接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 问答 | POST | /api/chat | 提交问题获取回答 |
| 历史记录 | GET | /api/history | 获取用户历史记录 |
| 清空历史 | DELETE | /api/history | 清空用户历史记录 |
| 反馈 | POST | /api/feedback | 提交反馈 |
| 推荐问题 | GET | /api/recommended-questions | 获取推荐问题 |

### 6.2 管理端接口

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

## 七、路由配置

### 7.1 用户端路由

| 路径 | 组件 | 说明 |
|------|------|------|
| / | Home | 首页 |
| /history | History | 历史记录 |

### 7.2 管理端路由

| 路径 | 组件 | 说明 |
|------|------|------|
| /admin/login | Login | 登录页 |
| /admin | Dashboard | 概览页 |
| /admin/logs | Logs | 问答日志 |
| /admin/feedbacks | Feedbacks | 反馈管理 |
| /admin/faqs | Faqs | FAQ管理 |
| /admin/sources | Sources | 来源管理 |
| /admin/packages | Packages | 知识包管理 |

### 7.3 权限守卫

- 管理端路由需要登录后才能访问
- 未登录访问自动跳转到登录页
- 登录页访问后已登录自动跳转到概览页

## 八、状态管理

使用 Pinia 进行状态管理，主要存储：
- 用户登录信息
- 问答会话状态

## 九、样式说明

- 使用原生 CSS 变量定义主题色
- 响应式设计适配移动端
- 统一的卡片、按钮、表单组件样式

## 十、默认数据

### 10.1 推荐问题

系统预置以下推荐问题：
- 陕西产假多少天
- 西安劳动仲裁去哪里
- 居民医保断缴后怎么处理
- 试用期工资标准
- 加班费计算方式

### 10.2 默认管理员

- 用户名：admin
- 密码：admin123

---

**文档版本**：V1.0  
**创建日期**：2026年4月26日  
**项目名称**：企业用工与社保合规智能平台