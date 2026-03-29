# 部署自动化参考知识

## 1. GitHub Actions CI Pipeline 参考

```yaml
# .github/workflows/ci.yaml
name: CI
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  frontend-check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
          cache-dependency-path: frontend/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm typecheck
      - run: pnpm test -- --coverage
      - run: pnpm build

  backend-check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: testpass
          MYSQL_DATABASE: altalex_test
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping -h localhost"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: mypy app/
      - run: pytest --cov=app --cov-report=xml
        env:
          DATABASE_URL: mysql+aiomysql://root:testpass@localhost:3306/altalex_test
          REDIS_URL: redis://localhost:6379/0
```

## 2. GitHub Actions 部署 Pipeline 参考

```yaml
# .github/workflows/deploy-staging.yaml
name: Deploy Staging
on:
  push:
    branches: [develop]

env:
  ACR_REGISTRY: registry.cn-shanghai.aliyuncs.com
  ACR_NAMESPACE: altalex
  CLUSTER_ID: ${{ secrets.ACK_CLUSTER_ID }}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 登录阿里云 ACR
      - name: Login to Aliyun ACR
        run: |
          docker login -u ${{ secrets.ACR_USERNAME }} -p ${{ secrets.ACR_PASSWORD }} ${{ env.ACR_REGISTRY }}

      # 构建并推送前端镜像
      - name: Build & Push Frontend
        run: |
          docker build -t ${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/frontend:${{ github.sha }} \
            --build-arg VITE_API_BASE_URL=${{ vars.STAGING_API_URL }} \
            frontend/
          docker push ${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/frontend:${{ github.sha }}

      # 构建并推送后端镜像
      - name: Build & Push Backend
        run: |
          docker build -t ${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/backend:${{ github.sha }} \
            backend/
          docker push ${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/backend:${{ github.sha }}

      # 配置 kubectl
      - name: Setup kubectl
        uses: aliyun/ack-set-context@v1
        with:
          access-key-id: ${{ secrets.ALIYUN_ACCESS_KEY_ID }}
          access-key-secret: ${{ secrets.ALIYUN_ACCESS_KEY_SECRET }}
          cluster-id: ${{ env.CLUSTER_ID }}

      # 执行数据库迁移
      - name: Run Alembic Migration
        run: |
          kubectl run alembic-migrate-${{ github.sha }} \
            --image=${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/backend:${{ github.sha }} \
            --namespace=altalex-staging \
            --restart=Never \
            --rm -i \
            --command -- alembic upgrade head

      # 更新 K8s Deployment 镜像
      - name: Deploy to K8s
        run: |
          kubectl set image deployment/frontend \
            frontend=${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/frontend:${{ github.sha }} \
            -n altalex-staging
          kubectl set image deployment/backend \
            backend=${{ env.ACR_REGISTRY }}/${{ env.ACR_NAMESPACE }}/backend:${{ github.sha }} \
            -n altalex-staging
          kubectl rollout status deployment/frontend -n altalex-staging --timeout=300s
          kubectl rollout status deployment/backend -n altalex-staging --timeout=300s
```

## 3. Dockerfile 参考

### 前端 Dockerfile（React SPA + Nginx）
```dockerfile
# frontend/Dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

# Stage 2: Serve
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 前端 Nginx 配置
```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA 路由 fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理（开发/调试用，生产环境由 Ingress 处理）
    # location /api/ {
    #     proxy_pass http://backend-service:8000;
    # }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
}
```

### 后端 Dockerfile（FastAPI + uvicorn）
```dockerfile
# backend/Dockerfile
# Stage 1: Dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

# 非 root 用户运行
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 4. Kubernetes Manifests 参考

### Backend Deployment
```yaml
# k8s/base/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  labels:
    app: altalex-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: altalex-backend
  template:
    metadata:
      labels:
        app: altalex-backend
    spec:
      containers:
        - name: backend
          image: registry.cn-shanghai.aliyuncs.com/altalex/backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secrets
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

### Backend Service
```yaml
# k8s/base/backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: altalex-backend
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

### Frontend Deployment
```yaml
# k8s/base/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  labels:
    app: altalex-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: altalex-frontend
  template:
    metadata:
      labels:
        app: altalex-frontend
    spec:
      containers:
        - name: frontend
          image: registry.cn-shanghai.aliyuncs.com/altalex/frontend:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 3
            periodSeconds: 5
```

### Ingress（阿里云 ALB Ingress）
```yaml
# k8s/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: altalex-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-id: "<ACM_CERT_ID>"
spec:
  rules:
    - host: app.altalex.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
    - host: dashboard.altalex.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

### HPA（自动扩缩容）
```yaml
# k8s/base/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### ConfigMap（Staging 示例）
```yaml
# k8s/staging/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: altalex-staging
data:
  APP_ENV: staging
  LOG_LEVEL: DEBUG
  CORS_ORIGINS: "https://staging.altalex.com"
  REDIS_URL: "redis://r-xxx.redis.rds.aliyuncs.com:6379/0"
  DATABASE_HOST: "rm-xxx.mysql.rds.aliyuncs.com"
  DATABASE_PORT: "3306"
  DATABASE_NAME: "altalex_staging"
```

### Secret（Staging 示例）
```yaml
# k8s/staging/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: altalex-staging
type: Opaque
stringData:
  DATABASE_USER: altalex_app
  DATABASE_PASSWORD: "<from-aliyun-kms>"
  JWT_SECRET_KEY: "<from-aliyun-kms>"
  OPENAI_API_KEY: "<from-aliyun-kms>"
  STRIPE_SECRET_KEY: "<from-aliyun-kms>"
  STRIPE_WEBHOOK_SECRET: "<from-aliyun-kms>"
```

## 5. 环境变量清单

| 变量名 | 用途 | 存放位置 | 敏感 |
|--------|------|----------|------|
| APP_ENV | 运行环境标识 | ConfigMap | No |
| DATABASE_HOST | MySQL RDS 地址 | ConfigMap | No |
| DATABASE_PORT | MySQL 端口 | ConfigMap | No |
| DATABASE_NAME | 数据库名 | ConfigMap | No |
| DATABASE_USER | 数据库用户名 | Secret | Yes |
| DATABASE_PASSWORD | 数据库密码 | Secret | Yes |
| REDIS_URL | 阿里云 Redis 地址 | ConfigMap | No |
| JWT_SECRET_KEY | JWT 签名密钥 | Secret | Yes |
| JWT_ALGORITHM | JWT 算法 (HS256) | ConfigMap | No |
| CORS_ORIGINS | 允许的跨域来源 | ConfigMap | No |
| OPENAI_API_KEY | OpenAI API 密钥 | Secret | Yes |
| STRIPE_SECRET_KEY | Stripe 密钥 | Secret | Yes |
| STRIPE_WEBHOOK_SECRET | Stripe Webhook 签名密钥 | Secret | Yes |
| SENTRY_DSN | Sentry 错误追踪 | ConfigMap | No |
| LOG_LEVEL | 日志级别 | ConfigMap | No |
| VITE_API_BASE_URL | 前端 API 地址 (构建时注入) | GitHub Vars | No |

## 6. Alembic 迁移部署流程

```bash
# 本地开发
alembic revision --autogenerate -m "add_feature_table"  # 自动生成迁移
alembic upgrade head                                      # 应用迁移
alembic downgrade -1                                      # 回滚一步

# CI/CD 中部署（通过 K8s Job）
kubectl run alembic-migrate \
  --image=registry.cn-shanghai.aliyuncs.com/altalex/backend:${TAG} \
  --namespace=altalex-production \
  --restart=Never \
  --rm -i \
  --env="DATABASE_URL=${PROD_DATABASE_URL}" \
  --command -- alembic upgrade head

# 生产回滚
kubectl run alembic-rollback \
  --image=registry.cn-shanghai.aliyuncs.com/altalex/backend:${TAG} \
  --namespace=altalex-production \
  --restart=Never \
  --rm -i \
  --env="DATABASE_URL=${PROD_DATABASE_URL}" \
  --command -- alembic downgrade -1
```

## 7. 监控配置

### Sentry (Python FastAPI)
```python
# app/core/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry(dsn: str, environment: str):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,  # 10% 性能追踪采样
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
    )
```

### FastAPI 健康检查端点
```python
# app/api/health.py
from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import async_session

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "ok"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}, 503
```
