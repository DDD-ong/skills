# Alta Lex PRD 分析参考知识

## 1. 三大应用功能边界

### 官网 (Marketing Website)
- 产品展示页（首页、功能介绍、案例展示）
- 定价页（Individual $240起 / Enterprise 联系销售）
- 注册/登录（邮箱唯一标识、密码要求：8位+大小写+数字+特殊符号）
- 个人订阅下单（Stripe Checkout、GST 9% 新加坡自动计税）
- 信用卡账单（商户名 Alta Lex、Invoice 自动生成发送）

### AI 法律工作台 (Alta Lex AI)
- 合同起草 (Contract Drafting)
- 合同审核 (Contract Review)
- 法律研究 (Legal Research)
- 法律翻译 (Legal Translation)
- Settings 页（个人信息、订阅管理、Credits 用量）

### 企业 Dashboard
- Overview Tab: 组织 Credits 汇总、即将到期提醒、订单列表
- Accounts Tab: 账号列表、批量新建、Link Existing Account、权限管理
- Usage Tab: 账号用量列表、明细查看

### 平台管理员后台（内部专用）
- Overview: 全平台汇总（Credits、个人账号、组织）
- Organizations: 组织列表、新增、快速操作
- Accounts: 全平台账号视图、Set Inactive 等敏感操作
- Sales: 订单列表、新增订单、发票回填（目标2分钟）
- Audit Log: 操作追溯、按操作人筛选

## 2. 三种账户类型

| 类型 | 描述 | Credits 池 |
|------|------|-----------|
| 纯个人账号 | 官网自主注册+付款，未挂载任何组织 | 仅个人池 |
| 纯组织账号 | 平台管理员后台创建，直接挂载到组织 | 仅组织池 |
| 双池账号 | 已有个人账号被挂载进企业组织 | 个人池 + 组织池（隔离） |

## 3. 三种组织角色

| 角色 | 数量 | 关键权限 |
|------|------|---------|
| Owner | 唯一 | 管理成员、额度分配、设为Admin、Link to Order、创建账号 |
| Admin | 多个 | 新增账号、停用User账号(不可)、额度分配、Edit Password(仅User) |
| User | 默认 | 仅使用产品、查看个人用量 |

## 4. 账号状态流转

- **Active**: 正常使用，订单有效期内
- **Inactive**: 平台管理员冻结，禁止消耗但可查看历史（仅平台管理员可操作）
- **Expired**: 订单到期，终态覆盖（无条件打为 Expired）

核心规则：
- 账号永久保留，**不支持删除**（防止"无限裂变"风险）
- Owner 无删除权限，仅可调整 Credits 额度实现"软冻结"
- 员工离职换人通过平台管理员修改邮箱/姓名信息

## 5. Credits 系统核心概念

| 概念 | 说明 |
|------|------|
| Total Credits | 订单发放的总额度 |
| Allocated Credits | 分配给具体账号的额度 |
| Unallocated Credits | 组织池中未分配的额度 |
| Used Credits | 已消耗量 |
| Remaining Credits | 剩余可用量 |
| Expired Credits | 已过期失效量 |

额度分配规则：
- 系统预填建议额度，操作人可修改后提交
- Set Inactive 时冻结已分配额度，不释放回池
- Reactivate 后恢复正常使用
- Expired 账号续费后需重新分配额度（Credits = 0）

## 6. 试用转付费三种情形

| 情形 | 场景 | 操作路径 |
|------|------|---------|
| A | 未经过测试直接下单 | 创建组织 → 创建订单 → 批量新建账号 |
| B | 已有测试账号，不再保留 | 创建正式订单 → 批量新建账号 → 测试账号自动 Expired |
| C | 已有测试账号，需要保留 | 创建正式订单 → Link to Order 关联测试账号 → 补足新建账号 |

## 7. 个人定价方案

- 初始支付: $240（包含 1,500 Credits，30天试用期）
- 年度订阅: $2,800/年（自动续费，18,000 Credits）
- 加油包: $10/100 Credits
