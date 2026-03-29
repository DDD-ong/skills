# 架构设计参考知识

## 1. 技术栈约束

| 层级 | 技术 | 版本要求 |
|------|------|---------|
| 前端框架 | React (纯 SPA) | 18+ |
| 构建工具 | Vite | 5+ |
| 类型系统 | TypeScript | 5+ (strict mode) |
| UI 组件库 | Ant Design (antd) | 5+ |
| 路由 | React Router | v6+ |
| 状态管理 | Redux Toolkit / Zustand | latest |
| 后端框架 | Python FastAPI | 0.100+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| 数据库迁移 | Alembic | latest |
| 数据库 | MySQL | 8.0+ (阿里云 RDS) |
| 缓存 | Redis | 7+ (阿里云 Redis) |
| 认证 | JWT (python-jose) | - |
| 任务队列 | Celery + Redis | latest |
| 支付 | stripe-python | latest |
| AI | openai-python | latest |
| 财务 | xero-python | latest |
| 容器化 | Docker | latest |
| 编排 | Kubernetes (阿里云 ACK) | 1.28+ |
| CI/CD | GitHub Actions | - |
| 监控 | Prometheus + Grafana | - |

## 2. 系统外部依赖

- **Stripe**: 支付网关 - Subscriptions, Checkout, Webhooks, Invoices
- **Xero**: 财务系统 - Invoice 同步, 收入确认
- **OpenAI**: AI 模型 - 合同分析, 法律研究, 翻译
- **OCBC**: 银行 - Stripe Payout 入账
- **阿里云 RDS**: 托管 MySQL 数据库
- **阿里云 Redis**: 托管 Redis 缓存 + Celery Broker
- **阿里云 ACK**: Kubernetes 容器编排
- **阿里云 ACR**: Docker 镜像仓库
- **阿里云 CDN**: 前端静态资源加速
- **Email Service**: 开户邮件, Invoice 发送, 验证码（阿里云邮件推送 / SendGrid）

## 3. 架构关键挑战

### 前后端分离架构
- React SPA 作为纯静态资源部署在 Nginx 容器 + CDN
- FastAPI 后端提供 RESTful API，自动生成 OpenAPI 文档
- 跨域 (CORS) 配置：FastAPI CORSMiddleware
- API 版本管理：`/api/v1/` 路径前缀

### Credits 实时同步
- 个人池和组织池完全隔离，独立计量
- 余额需在多端实时一致
- 扣减操作需事务安全（MySQL SELECT FOR UPDATE）
- 建议方案: WebSocket (FastAPI WebSocket) 推送余额变更 / 前端轮询

### 多租户隔离
- 不使用数据库级 RLS，改用应用层中间件实现
- FastAPI Dependencies 注入当前用户和组织上下文
- 所有查询自动附加 `organization_id` 过滤条件
- 权限校验中间件：基于角色的访问控制 (RBAC)

### 支付流集成
- Stripe Checkout → 支付成功 Webhook → 创建 Subscription → 分配 Credits
- 自动续费: Stripe Invoice → 支付成功 → 续期 Credits
- 对账: Stripe Payout → OCBC 入账 → Xero Invoice 同步

### 统一认证
- 邮箱为唯一标识
- JWT Token (Access Token + Refresh Token)
- Access Token 短期有效（15-30min），Refresh Token 长期有效（7-30天）
- Token 存储在 HttpOnly Cookie 或 localStorage
- FastAPI OAuth2PasswordBearer + JWT 解码中间件

### 容器化部署
- 前端: Nginx 容器（多阶段构建：node build → nginx serve）
- 后端: Python 容器（uvicorn + gunicorn）
- K8s 资源：Deployment + Service + Ingress + HPA + ConfigMap + Secret
- 蓝绿部署或滚动更新策略
