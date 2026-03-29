---
name: deploy-automation
version: 1.0.0
description: >
  Generate CI/CD pipelines and deployment configurations for Alta Lex.
  Use when setting up GitHub Actions workflows, configuring Aliyun ACK Kubernetes deployment,
  or managing environment configurations.
description_zh: >
  为 Alta Lex 生成 CI/CD 流水线和部署配置。
  当设置 GitHub Actions 工作流、配置阿里云 ACK Kubernetes 部署、或管理环境配置时使用。
---

# Deploy Automation

## 触发条件

当出现以下场景时使用此技能：
- 设置或修改 CI/CD 流水线
- 配置阿里云 ACK Kubernetes 部署
- 编写 Dockerfile 多阶段构建
- 管理环境变量和密钥（ConfigMap / Secret）
- 设计数据库迁移部署策略（Alembic）
- 配置监控和告警

## 执行流程

1. **架构理解**: 读取架构文档了解部署拓扑
2. **Pipeline 设计**: 设计 GitHub Actions 工作流
3. **容器化**: 编写 Dockerfile（前端 Nginx + 后端 FastAPI）
4. **K8s 配置**: 生成 Deployment、Service、Ingress、HPA 等 manifests
5. **环境管理**: 定义各环境的 ConfigMap 和 Secret 清单
6. **迁移策略**: 设计 Alembic 数据库迁移部署流程
7. **监控配置**: 配置 Sentry 和阿里云 ARMS 监控
8. **文档产出**: 输出配置文件和运维文档

## 输入要求

- 架构文档（`docs/architecture/*.md`）
- 技术栈信息

## 输出规范

### CI/CD Pipeline 文件
```
.github/workflows/
├── ci.yaml              # PR 检查: lint + typecheck + test + build
├── deploy-staging.yaml  # Staging 部署: merge to develop → 构建镜像 → 部署 K8s
├── deploy-prod.yaml     # 生产部署: merge to main → 构建镜像 → 部署 K8s
└── db-migration.yaml    # 数据库迁移 (Alembic)
```

### Dockerfile
```
frontend/Dockerfile      # 多阶段构建: Node build → Nginx 运行
backend/Dockerfile       # 多阶段构建: pip install → uvicorn 运行
```

### Kubernetes Manifests
```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
├── staging/
│   ├── kustomization.yaml
│   ├── configmap.yaml
│   └── secret.yaml
└── production/
    ├── kustomization.yaml
    ├── configmap.yaml
    └── secret.yaml
```

### Pipeline 阶段设计
```
PR 创建/更新:
  → Install dependencies (前端 pnpm / 后端 pip)
  → Lint (ESLint + Ruff)
  → Type Check (tsc --noEmit + mypy)
  → Unit Tests (Jest + pytest)
  → Build (React build + Docker build)

Merge to develop (Staging):
  → Full Test Suite
  → Docker Build & Push to Aliyun ACR
  → DB Migration (Alembic upgrade)
  → kubectl apply (Staging namespace)
  → Smoke Tests

Merge to main (Production):
  → Full Test Suite
  → Docker Build & Push to Aliyun ACR (production tag)
  → DB Migration (Alembic upgrade)
  → kubectl apply (Production namespace) - Rolling Update
  → Smoke Tests
  → Notify (Slack/DingTalk)
```

## 质量检查

- [ ] Pipeline 覆盖 lint、typecheck、test、build 全流程
- [ ] 密钥通过 GitHub Secrets + K8s Secret 管理，不硬编码
- [ ] 数据库迁移（Alembic）有回滚策略
- [ ] 生产部署有 smoke test 验证
- [ ] K8s manifests 包含 liveness/readiness 健康检查
- [ ] HPA 配置合理的自动扩缩容策略
- [ ] 环境变量模板 (.env.example) 完整
