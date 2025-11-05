# Git 工作流与提交规范

本文档定义 Bento 项目的 Git 工作流程、分支策略和提交规范。

## 📋 目录

- [分支策略](#分支策略)
- [提交规范](#提交规范)
- [Pull Request 规范](#pull-request-规范)
- [代码审查](#代码审查)
- [发布流程](#发布流程)

---

## 分支策略

### 主要分支

```
main (生产环境)
  ↑
  └── develop (开发主线)
       ↑
       ├── feature/xxx (功能分支)
       ├── bugfix/xxx (bug修复)
       ├── hotfix/xxx (紧急修复)
       └── release/vX.Y.Z (发布分支)
```

#### `main` 分支
- **用途**: 生产环境代码，始终保持可发布状态
- **保护**: 
  - ✅ 禁止直接推送
  - ✅ 必须通过 PR 合并
  - ✅ 必须通过所有 CI 检查
  - ✅ 需要至少 1 人代码审查
- **标签**: 每次发布打 tag（如 `v0.2.0`）

#### `develop` 分支
- **用途**: 开发主线，集成最新功能
- **保护**: 
  - ✅ 禁止直接推送
  - ✅ 必须通过 PR 合并
  - ✅ 必须通过 CI
- **来源**: 从 `main` 分支创建
- **合并到**: `main`（通过 release 分支）

### 临时分支

#### Feature 分支（功能开发）
```bash
# 命名格式
feature/<issue-number>-<short-description>
feature/42-add-order-aggregate
feature/123-implement-outbox-pattern

# 创建
git checkout develop
git pull origin develop
git checkout -b feature/42-add-order-aggregate

# 合并到 develop
git checkout develop
git merge --no-ff feature/42-add-order-aggregate
git push origin develop
git branch -d feature/42-add-order-aggregate
```

**约定**：
- ✅ 从 `develop` 分支创建
- ✅ 完成后合并回 `develop`
- ✅ 使用 `--no-ff` 保留分支历史
- ✅ 合并后删除分支

#### Bugfix 分支（常规修复）
```bash
# 命名格式
bugfix/<issue-number>-<short-description>
bugfix/88-fix-event-serialization

# 工作流程与 feature 相同
```

#### Hotfix 分支（紧急修复）
```bash
# 命名格式
hotfix/<version>-<description>
hotfix/v0.1.1-fix-critical-bug

# 创建（从 main）
git checkout main
git pull origin main
git checkout -b hotfix/v0.1.1-fix-critical-bug

# 修复并测试
git add .
git commit -m "fix: critical bug in order processing"

# 合并到 main 和 develop
git checkout main
git merge --no-ff hotfix/v0.1.1-fix-critical-bug
git tag -a v0.1.1 -m "Hotfix: critical bug fix"
git push origin main --tags

git checkout develop
git merge --no-ff hotfix/v0.1.1-fix-critical-bug
git push origin develop

git branch -d hotfix/v0.1.1-fix-critical-bug
```

**特点**：
- 🚨 用于生产环境紧急问题
- ✅ 从 `main` 分支创建
- ✅ 同时合并到 `main` 和 `develop`
- ✅ 合并到 `main` 后立即打 tag

#### Release 分支（发布准备）
```bash
# 命名格式
release/vX.Y.Z
release/v0.2.0

# 创建
git checkout develop
git checkout -b release/v0.2.0

# 准备发布（修复小 bug，更新版本号）
# pyproject.toml: version = "0.2.0"
git commit -m "chore: bump version to 0.2.0"

# 合并到 main
git checkout main
git merge --no-ff release/v0.2.0
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main --tags

# 合并回 develop
git checkout develop
git merge --no-ff release/v0.2.0
git push origin develop

git branch -d release/v0.2.0
```

---

## 提交规范

### Conventional Commits 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type（必需）
| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(domain): add Order aggregate` |
| `fix` | Bug 修复 | `fix(persistence): resolve N+1 query issue` |
| `docs` | 文档变更 | `docs(adr): add event sourcing decision` |
| `style` | 代码格式（不影响逻辑） | `style: format with ruff` |
| `refactor` | 重构（非功能非修复） | `refactor(application): simplify usecase` |
| `perf` | 性能优化 | `perf(repository): add query caching` |
| `test` | 测试相关 | `test(domain): add order validation tests` |
| `build` | 构建系统/依赖 | `build: upgrade fastapi to 0.115` |
| `ci` | CI 配置 | `ci: add mypy check to workflow` |
| `chore` | 其他杂项 | `chore: update .gitignore` |
| `revert` | 回退提交 | `revert: revert "feat: add feature X"` |

#### Scope（可选）
模块或层级：
- `core` - 核心层
- `domain` - 领域层
- `application` - 应用层
- `infrastructure` - 基础设施
- `persistence` - 持久化
- `messaging` - 消息
- `interfaces` - 接口层
- `observability` - 可观测性

#### Subject（必需）
- ✅ 使用祈使句（"add" 而非 "added"）
- ✅ 首字母小写
- ✅ 结尾不加句号
- ✅ 不超过 50 字符
- ✅ 清晰描述做了什么

#### Body（可选）
- 详细说明**为什么**改动
- 换行后 72 字符
- 用空行分隔 subject

#### Footer（可选）
- **Breaking Changes**: `BREAKING CHANGE: <description>`
- **关闭 Issue**: `Closes #123`, `Fixes #456`
- **关联 PR**: `Related to #789`

### 提交示例

#### ✅ 好的提交

```bash
# 1. 简单功能
git commit -m "feat(domain): add Order aggregate root"

# 2. 带 scope 和详细说明
git commit -m "feat(persistence): implement SQLAlchemy UnitOfWork

- Add transaction management
- Integrate with Outbox pattern
- Support event collection from aggregates

Closes #42"

# 3. Breaking Change
git commit -m "refactor(core): change Result API

BREAKING CHANGE: Result.value() renamed to Result.unwrap()
for consistency with Rust's Result type.

Migration:
- Replace all .value() calls with .unwrap()
- Update error handling to use unwrap_err()

Closes #88"

# 4. Bug 修复
git commit -m "fix(messaging): prevent duplicate event publishing

Events were published twice when UoW committed.
Now using set() to deduplicate before publishing.

Fixes #156"
```

#### ❌ 不好的提交

```bash
# 太模糊
git commit -m "update code"
git commit -m "fix bug"

# 不符合格式
git commit -m "Added new feature."  # 应该用祈使句
git commit -m "FIX: order issue"    # type 应该小写

# 混合多个改动
git commit -m "feat: add Order and Product and fix cache bug"
# 应该拆分成多个提交

# Subject 太长
git commit -m "feat: add the new order aggregate root with validation and event collection mechanism"
# 详细内容应该放在 body
```

### 提交最佳实践

#### 1. 原子性提交
每个提交只做一件事：
```bash
# ✅ 好的 - 分离关注点
git add src/domain/order.py
git commit -m "feat(domain): add Order aggregate"

git add src/persistence/order_repo.py
git commit -m "feat(persistence): add OrderRepository"

# ❌ 不好的 - 混合多个改动
git add src/domain/ src/persistence/
git commit -m "feat: add order stuff"
```

#### 2. 频繁提交
```bash
# 开发过程
feat(domain): add Order entity skeleton
feat(domain): add Order validation logic
test(domain): add Order validation tests
refactor(domain): extract OrderStatus value object
```

**原则**：提交要小而频繁，便于：
- ✅ 代码审查
- ✅ 问题追踪
- ✅ 回退操作

#### 3. 提交前检查
```bash
# 查看改动
git diff

# 检查代码质量
make lint

# 运行测试
make test

# 分阶段提交
git add -p  # 交互式选择

# 修正上次提交（未推送前）
git commit --amend
```

---

## Pull Request 规范

### PR 标题
遵循 Conventional Commits 格式：
```
feat(domain): add Order aggregate root
fix(persistence): resolve connection leak
docs(conventions): add git workflow guide
```

### PR 描述模板

```markdown
## 📝 变更说明
简要描述这个 PR 做了什么。

## 🎯 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] 测试 (test)
- [ ] 其他

## 🔗 关联 Issue
Closes #123

## 📋 变更详情
- 添加了 Order 聚合根
- 实现了订单验证逻辑
- 集成了领域事件

## 🧪 测试
- [x] 单元测试通过
- [x] 集成测试通过
- [ ] E2E 测试（不适用）

## 📸 截图（如适用）
（如有 UI 变更）

## 🚀 部署说明
- 无需数据库迁移
- 需要重启服务

## ✅ 检查清单
- [x] 代码遵循项目规范
- [x] 通过 `make lint`
- [x] 通过 `make test`
- [x] 更新了相关文档
- [x] 添加了必要的测试
- [x] 无 Breaking Changes
```

### PR 大小建议

| 大小 | 行数变更 | 建议 |
|------|---------|------|
| 🟢 小 | < 200 行 | 理想大小，易于审查 |
| 🟡 中 | 200-500 行 | 可接受，考虑拆分 |
| 🔴 大 | > 500 行 | 应该拆分成多个 PR |

**大 PR 的处理**：
```bash
# 使用 git log 查看提交
git log --oneline feature/large-feature

# 拆分成多个 PR
git checkout -b feature/part-1
git cherry-pick commit1 commit2
git push origin feature/part-1

git checkout -b feature/part-2
git cherry-pick commit3 commit4
git push origin feature/part-2
```

### PR 合并策略

#### 1. Squash and Merge（推荐用于 feature）
```bash
# 将所有提交压缩成一个
feature/42-add-order (5 commits)
  ↓ squash
develop (1 commit: feat(domain): add Order aggregate)
```

**优点**：
- ✅ 保持主分支历史清晰
- ✅ 每个功能一个提交
- ❌ 丢失详细开发历史

**使用场景**：功能分支合并到 develop

#### 2. Rebase and Merge
```bash
# 保留所有提交，但重写基础
feature/42-add-order (5 commits)
  ↓ rebase
develop (5 commits, 线性历史)
```

**优点**：
- ✅ 线性历史
- ✅ 保留详细提交
- ❌ 修改提交历史

#### 3. Merge Commit（推荐用于 release）
```bash
# 保留分支历史
release/v0.2.0
  ↓ merge --no-ff
main (包含完整分支图)
```

**优点**：
- ✅ 保留完整历史
- ✅ 清晰的分支点
- ❌ 复杂的提交图

**使用场景**：release/hotfix 合并到 main

---

## 代码审查

### 审查者职责

#### 必须检查
- [ ] ✅ 代码符合分层架构
- [ ] ✅ Domain 层无 I/O 操作
- [ ] ✅ 使用 Result 类型处理错误
- [ ] ✅ 类型注解完整
- [ ] ✅ 有对应的测试
- [ ] ✅ 通过 CI 检查

#### 关注点
```markdown
**架构层面**：
- 依赖方向是否正确？
- 是否违反了六边形架构原则？

**DDD 层面**：
- 聚合边界是否合理？
- 业务规则是否在 Domain 层？
- 领域事件是否恰当？

**代码质量**：
- 命名是否清晰？
- 逻辑是否易懂？
- 有没有重复代码？

**测试覆盖**：
- 关键路径是否有测试？
- 边界条件是否考虑？
```

### 审查评论规范

#### ✅ 好的评论
```markdown
**建议**: 这里可以使用 Specification 模式来封装业务规则。
参考：docs/conventions/README.md#specification

**问题**: Order 不应该直接依赖 OrderRepository。
建议在 Application 层通过 UseCase 协调。

**疑问**: 为什么这里不记录领域事件？
订单状态变化应该触发 OrderStatusChangedEvent。

**赞**: 👍 这个 Result 类型使用得很好，错误处理清晰！
```

#### ❌ 不好的评论
```markdown
# 太模糊
"这里有问题"  # 什么问题？如何修改？

# 太主观
"我不喜欢这个写法"  # 应该说明具体原因

# 不尊重
"这代码写得太烂了"  # 应该建设性地提建议
```

### 评论类型标签
```markdown
**[MUST]**: 必须修改（阻塞合并）
**[SHOULD]**: 建议修改
**[NIT]**: 小问题（代码风格等）
**[QUESTION]**: 疑问/讨论
**[PRAISE]**: 表扬好的实践
```

### PR 审查清单

```markdown
## 架构与设计
- [ ] 遵循六边形架构
- [ ] 依赖方向正确（内层不依赖外层）
- [ ] Domain 层纯粹（无 I/O）
- [ ] 使用 Protocol 定义端口

## DDD 实践
- [ ] 聚合边界清晰
- [ ] 使用统一语言（Ubiquitous Language）
- [ ] 领域事件恰当
- [ ] 值对象不可变

## 代码质量
- [ ] 命名清晰（使用业务语言）
- [ ] 类型注解完整
- [ ] 错误处理恰当（Result vs Exception）
- [ ] 无重复代码

## 测试
- [ ] 有单元测试
- [ ] 测试覆盖关键路径
- [ ] 测试名称清晰
- [ ] 无脆弱测试（不依赖顺序）

## 文档
- [ ] 复杂逻辑有注释
- [ ] 公共 API 有 docstring
- [ ] ADR 更新（如有架构决策）

## 性能与安全
- [ ] 无 N+1 查询
- [ ] 无 SQL 注入风险
- [ ] 敏感数据加密/脱敏
```

---

## 发布流程

### 版本号规范（SemVer）

```
vMAJOR.MINOR.PATCH

v0.2.1
  │ │ └─ Patch: 向后兼容的 bug 修复
  │ └─── Minor: 向后兼容的新功能
  └───── Major: 不兼容的 API 变更
```

**示例**：
- `v0.1.0` → `v0.1.1`: 修复 bug
- `v0.1.1` → `v0.2.0`: 添加新功能
- `v0.2.0` → `v1.0.0`: 重大重构，API 不兼容

### 发布步骤

```bash
# 1. 创建 release 分支
git checkout develop
git pull origin develop
git checkout -b release/v0.2.0

# 2. 更新版本号
# 编辑 pyproject.toml
version = "0.2.0"

# 3. 更新 CHANGELOG
# 编辑 CHANGELOG.md
## [0.2.0] - 2025-11-05
### Added
- Order aggregate with validation
- SQLAlchemy UnitOfWork
- Outbox pattern implementation

### Fixed
- Event serialization issue (#88)

### Changed
- Result API (BREAKING: .value() → .unwrap())

# 4. 提交版本变更
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.2.0"

# 5. 合并到 main
git checkout main
git merge --no-ff release/v0.2.0

# 6. 打标签
git tag -a v0.2.0 -m "Release v0.2.0

Features:
- Order aggregate
- UnitOfWork pattern
- Outbox implementation

See CHANGELOG.md for details."

# 7. 推送
git push origin main --tags

# 8. 合并回 develop
git checkout develop
git merge --no-ff release/v0.2.0
git push origin develop

# 9. 删除 release 分支
git branch -d release/v0.2.0

# 10. 创建 GitHub Release
# 在 GitHub 上基于 tag 创建 Release，附上 CHANGELOG
```

### CHANGELOG 格式

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- 正在开发的功能

## [0.2.0] - 2025-11-05
### Added
- Order aggregate with event collection
- SQLAlchemy UnitOfWork implementation
- Outbox pattern for event consistency

### Fixed
- Event serialization bug (#88)
- Repository connection leak (#92)

### Changed
- **BREAKING**: Result.value() renamed to Result.unwrap()

### Deprecated
- Old Repository interface (use new Protocol-based)

### Removed
- Legacy event bus implementation

### Security
- Fixed SQL injection vulnerability in OrderRepository

## [0.1.0] - 2025-10-15
### Added
- Initial release
- Core abstractions (Entity, ValueObject, Result)
- Basic repository pattern

[Unreleased]: https://github.com/org/bento/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/org/bento/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/org/bento/releases/tag/v0.1.0
```

---

## 快速参考

### 常用命令

```bash
# 创建功能分支
git checkout -b feature/42-add-order

# 提交代码
git add .
git commit -m "feat(domain): add Order aggregate"

# 推送到远程
git push origin feature/42-add-order

# 同步最新 develop
git checkout develop
git pull origin develop
git checkout feature/42-add-order
git rebase develop

# 查看提交历史
git log --oneline --graph --decorate

# 修正最后一次提交
git commit --amend

# 交互式 rebase（整理提交）
git rebase -i HEAD~3
```

### Commit Message 速查

```bash
# 新功能
git commit -m "feat(domain): add Order aggregate"

# Bug 修复
git commit -m "fix(persistence): resolve N+1 query"

# 文档
git commit -m "docs(conventions): add git workflow"

# 测试
git commit -m "test(domain): add order validation tests"

# 重构
git commit -m "refactor(application): simplify usecase"

# 性能
git commit -m "perf(repository): add caching"

# 构建
git commit -m "build: upgrade dependencies"

# CI
git commit -m "ci: add lint check"

# 杂项
git commit -m "chore: update .gitignore"
```

---

## 参考资料

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

