---
name: frontend-dev
version: 1.0.0
description: >
  Develop React SPA frontend components and pages for Alta Lex applications.
  Use when building UI components, implementing pages, or handling client-side state.
description_zh: >
  为 Alta Lex 应用开发 React SPA 前端组件和页面。
  当构建 UI 组件、实现页面、或处理客户端状态时使用。
---

# Frontend Development

## 触发条件

当出现以下场景时使用此技能：
- 开发新的 UI 组件或页面
- 实现客户端交互逻辑和状态管理
- 集成后端 API 的前端调用
- 处理表单验证和用户输入

## 执行流程

1. **需求理解**: 读取相关需求文档和架构文档
2. **路由确认**: 确认组件/页面在三大应用中的路由位置
3. **组件设计**: 确定组件拆分和复用策略
4. **UI 实现**: 使用 Ant Design + 自定义样式编写 UI
5. **状态管理**: 接入 Zustand（全局状态）或 React Query（服务端数据）
6. **表单验证**: 使用 React Hook Form + Zod 处理用户输入
7. **代码产出**: 输出到 `frontend/src/` 对应目录

## 输入要求

- 架构文档（`docs/architecture/*.md`）
- API 契约（`docs/api/openapi-spec.yaml`）
- UI 设计稿（如有）

## 输出规范

### 文件组织约定
```
frontend/src/
├── pages/
│   ├── marketing/              # 官网应用
│   │   ├── Home.tsx
│   │   ├── Pricing.tsx
│   │   └── index.ts
│   ├── workspace/              # AI 法律工作台
│   │   ├── Contracts.tsx
│   │   ├── Research.tsx
│   │   ├── Settings.tsx
│   │   └── index.ts
│   ├── dashboard/              # 企业 Dashboard
│   │   ├── Overview.tsx
│   │   ├── Accounts.tsx
│   │   ├── Usage.tsx
│   │   └── index.ts
│   └── admin/                  # 平台管理员
│       ├── Overview.tsx
│       ├── Organizations.tsx
│       ├── Accounts.tsx
│       ├── Sales.tsx
│       ├── AuditLog.tsx
│       └── index.ts
├── components/
│   ├── common/                 # 通用组件
│   └── shared/                 # 跨应用共享组件
├── services/
│   ├── api.ts                  # Axios 实例
│   ├── auth.ts                 # 认证 API
│   ├── credits.ts              # Credits API
│   └── organization.ts         # 组织 API
├── hooks/                      # 自定义 Hooks
├── stores/                     # Zustand stores
└── types/                      # TypeScript 类型定义
```

### 组件编写规范
- 使用函数组件 + Hooks 模式
- 所有 Props 使用 TypeScript interface 定义
- 组件文件使用 PascalCase 命名
- UI 框架统一使用 Ant Design

## 质量检查

- [ ] TypeScript 严格模式无类型错误
- [ ] 路由守卫正确处理认证和权限
- [ ] 响应式设计覆盖移动端和桌面端
- [ ] 表单验证完整（Ant Design Form 或 React Hook Form）
- [ ] Loading 和 Error 状态处理完整
- [ ] API 调用通过 service 层统一管理
