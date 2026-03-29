# 前端开发参考知识

## 1. 技术栈详情

### React SPA 路由设计 (React Router v6)
```typescript
// src/router/index.tsx
import { createBrowserRouter } from 'react-router-dom'

const router = createBrowserRouter([
  // 官网（公开）
  { path: '/', element: <MarketingLayout />, children: [
    { index: true, element: <HomePage /> },
    { path: 'pricing', element: <PricingPage /> },
    { path: 'login', element: <LoginPage /> },
    { path: 'register', element: <RegisterPage /> },
  ]},
  // AI 工作台（需认证）
  { path: '/workspace', element: <AuthGuard><WorkspaceLayout /></AuthGuard>, children: [
    { path: 'contracts', element: <ContractsPage /> },
    { path: 'research', element: <ResearchPage /> },
    { path: 'translation', element: <TranslationPage /> },
    { path: 'settings', element: <SettingsPage /> },
  ]},
  // 企业 Dashboard（需认证 + Owner/Admin）
  { path: '/dashboard', element: <AuthGuard roles={['owner','admin']}><DashboardLayout /></AuthGuard>, children: [
    { path: 'overview', element: <OverviewPage /> },
    { path: 'accounts', element: <AccountsPage /> },
    { path: 'usage', element: <UsagePage /> },
  ]},
  // 平台管理（需平台管理员）
  { path: '/admin', element: <AuthGuard adminOnly><AdminLayout /></AuthGuard>, children: [
    { path: 'overview', element: <AdminOverviewPage /> },
    { path: 'organizations', element: <OrganizationsPage /> },
    { path: 'accounts', element: <AdminAccountsPage /> },
    { path: 'sales', element: <SalesPage /> },
    { path: 'audit-log', element: <AuditLogPage /> },
  ]},
])
```

### Ant Design 常用组件
- Layout: Layout, Sider, Content, Header, Footer
- Data: Table, List, Descriptions, Statistic, Card
- Form: Form, Input, Select, DatePicker, Upload
- Feedback: Modal, Drawer, message, notification, Alert
- Navigation: Menu, Breadcrumb, Tabs, Pagination

### 状态管理方案
```typescript
// stores/authStore.ts - Zustand 用户认证状态
import { create } from 'zustand'

interface AuthStore {
  user: User | null
  token: string | null
  currentOrg: Organization | null
  setUser: (user: User) => void
  setCurrentOrg: (org: Organization) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  currentOrg: null,
  setUser: (user) => set({ user }),
  setCurrentOrg: (org) => set({ currentOrg: org }),
  logout: () => set({ user: null, token: null, currentOrg: null }),
}))

// hooks/useCreditsBalance.ts - React Query 查询 Credits
import { useQuery } from '@tanstack/react-query'
import { creditsApi } from '@/services/credits'

export function useCreditsBalance() {
  return useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: creditsApi.getBalance,
    refetchInterval: 30000, // 30 秒轮询
  })
}
```

## 2. API 调用层封装

### Axios 实例配置
```typescript
// services/request.ts
import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
})

// 请求拦截器 - 自动附加 JWT Token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 统一错误处理
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期，尝试刷新或跳转登录
      handleTokenExpired()
    }
    return Promise.reject(error)
  }
)

export default request
```

### API 服务模块示例
```typescript
// services/credits.ts
import request from './request'

export const creditsApi = {
  getBalance: () => request.get('/credits/balance'),
  getTransactions: (params: PaginationParams) =>
    request.get('/credits/transactions', { params }),
  consume: (data: { amount: number; description: string }) =>
    request.post('/credits/consume', data),
}
```

## 3. 关键页面组件参考

### Credits 展示组件
- Ant Design Statistic + Card 组合展示余额
- 个人池余额卡片（Total / Used / Remaining）
- 组织池余额卡片（Total / Allocated / Unallocated / Used）
- 即将到期 Credits 警告横幅 (Alert 组件)
- Credits 用量趋势图（Ant Design Charts / ECharts）

### 企业 Dashboard 核心组件
- Overview: Statistic 卡片组 + Table 订单列表
- Accounts: ProTable 账号管理（支持搜索、过滤、批量操作）
- Usage: Table + Drawer 详情侧边栏

### 路由守卫
```typescript
// components/AuthGuard.tsx
function AuthGuard({ children, roles, adminOnly }) {
  const { user } = useAuthStore()
  const navigate = useNavigate()

  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (adminOnly && !user.is_platform_admin) {
    return <Navigate to="/" replace />
  }
  if (roles && !roles.includes(user.currentRole)) {
    return <Navigate to="/" replace />
  }
  return children
}
```

### 表单组件
- 批量创建账号表单（Ant Design Form.List 动态行增删）
- Credits 分配表单（Slider + InputNumber 联动）
- Stripe Checkout 触发按钮
