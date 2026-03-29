---
name: code-review
version: 1.0.0
description: >
  Review code changes for quality, security, and compliance with Alta Lex standards.
  Use when reviewing pull requests, checking code before commits,
  or auditing existing code for security issues.
description_zh: >
  审查代码变更的质量、安全性和 Alta Lex 规范合规性。
  当审查 PR、提交前检查代码、或审计现有代码安全问题时使用。
---

# Code Review

## 触发条件

当出现以下场景时使用此技能：
- 代码提交前的质量审查
- Pull Request 审查
- 安全审计
- 代码规范合规检查

## 执行流程

1. **变更识别**: 获取变更文件列表和 diff
2. **安全审查**: 检查安全漏洞（SQL 注入、XSS、权限绕过、竞态条件）
3. **性能审查**: 识别性能瓶颈（N+1 查询、不必要的重渲染、缺失索引）
4. **规范审查**: 检查命名约定、类型标注、组件结构
5. **业务逻辑审查**: 验证 Credits 扣减安全性、权限检查完整性
6. **产出报告**: 按严重级别输出 Review 报告

## 输入要求

- 变更文件列表或 Git diff
- 可选：关联的需求文档或 Issue

## 输出规范

### Review 报告格式

```markdown
# Code Review Report

## 概要
- 审查文件数: N
- 问题总数: N (Critical: X, Warning: Y, Info: Z)

## Critical Issues
### [C-001] [问题标题]
- **文件**: `path/to/file.py:42`
- **类别**: Security / Performance / Logic
- **描述**: 问题描述
- **建议**: 修复方案

## Warnings
### [W-001] [问题标题]
...

## Info / Suggestions
### [I-001] [改进建议]
...
```

### 审查维度和检查清单

**安全性 (Security)**:
- [ ] 无 SQL 注入风险（使用 SQLAlchemy ORM 参数化查询）
- [ ] 无 XSS 风险（React 自动转义 + 避免 dangerouslySetInnerHTML）
- [ ] 应用层权限检查未被绕过（FastAPI Dependencies）
- [ ] Credits 扣减有事务保护（SELECT FOR UPDATE）
- [ ] Stripe Webhook 签名验证
- [ ] 敏感数据未暴露到前端

**性能 (Performance)**:
- [ ] 无 N+1 查询（使用 SQLAlchemy joinedload/selectinload）
- [ ] 大列表使用分页
- [ ] React 组件避免不必要的重渲染
- [ ] MySQL 查询有索引支持

**可维护性 (Maintainability)**:
- [ ] 命名清晰一致
- [ ] Python 类型标注完整 / TypeScript 类型完整
- [ ] 函数职责单一
- [ ] 错误处理完整

**Alta Lex 特定检查**:
- [ ] Credits 操作记录到审计日志
- [ ] 权限检查覆盖所有敏感操作
- [ ] 账号状态检查（Active/Inactive/Expired）
- [ ] 双池隔离逻辑正确

## 质量检查

- [ ] 所有 Critical 问题已提供修复建议
- [ ] 安全相关问题无遗漏
- [ ] 审查结果可直接转化为 action items
