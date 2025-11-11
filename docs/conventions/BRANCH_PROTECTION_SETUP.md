# GitHub 分支保护规则设置指南

本文档指导如何为 Bento 项目设置分支保护规则。

## 📋 目录

- [为什么需要分支保护](#为什么需要分支保护)
- [设置步骤](#设置步骤)
- [推荐配置](#推荐配置)

## 🛡️ 为什么需要分支保护

分支保护规则确保：
- ✅ 所有代码变更都经过审查
- ✅ CI/CD 测试必须通过
- ✅ 防止意外的直接推送
- ✅ 保持代码质量和稳定性

## 🚀 设置步骤

### 步骤 1: 访问设置页面

1. 打开浏览器，访问：
   ```
   https://github.com/idpxyz/bento/settings/branches
   ```

2. 如果没有权限，确保你是仓库的 **Owner** 或 **Admin**

### 步骤 2: 设置 `main` 分支保护

#### 2.1 创建保护规则

1. 点击 **"Add branch protection rule"** 按钮
2. 在 **Branch name pattern** 输入：`main`

#### 2.2 配置保护选项

勾选以下选项：

**Protect matching branches（保护匹配的分支）**

✅ **Require a pull request before merging**
   - 要求通过 PR 才能合并
   - 勾选子选项：
     - ✅ **Require approvals**: 设置为 `1`（至少 1 人审查）
     - ✅ **Dismiss stale pull request approvals when new commits are pushed**
       （新提交时清除旧的审查）
     - ✅ **Require review from Code Owners**（如果有 CODEOWNERS 文件）

✅ **Require status checks to pass before merging**
   - 要求 CI 检查通过
   - 勾选子选项：
     - ✅ **Require branches to be up to date before merging**
       （合并前必须是最新代码）
   - 在 **Status checks** 中添加：
     - `test` （测试检查）
     - `lint` （代码检查）
     - 等你配置 CI 后会自动出现

✅ **Require conversation resolution before merging**
   - 要求解决所有讨论才能合并

✅ **Require signed commits**（可选，推荐）
   - 要求签名提交（更安全）

✅ **Require linear history**（可选，推荐）
   - 要求线性历史（禁止 merge commits，只允许 rebase 或 squash）

✅ **Include administrators**（推荐）
   - 规则也适用于管理员

❌ **Allow force pushes** - 保持禁用
❌ **Allow deletions** - 保持禁用

#### 2.3 保存规则

1. 滚动到页面底部
2. 点击 **"Create"** 按钮

### 步骤 3: 设置 `develop` 分支保护

重复步骤 2，但有以下区别：

1. **Branch name pattern** 输入：`develop`
2. 配置选项（稍微宽松）：

✅ **Require a pull request before merging**
   - ✅ **Require approvals**: 设置为 `1`

✅ **Require status checks to pass before merging**
   - ✅ **Require branches to be up to date before merging**

✅ **Require conversation resolution before merging**

✅ **Include administrators**

其他选项可以根据团队需求调整。

## 📊 推荐配置总览

### `main` 分支（生产环境）

```yaml
Branch: main
Protection Rules:
  ✅ Require PR before merging
    - Require 1 approval
    - Dismiss stale reviews
  ✅ Require status checks
    - Require up-to-date branch
  ✅ Require conversation resolution
  ✅ Require signed commits (可选)
  ✅ Require linear history (可选)
  ✅ Include administrators
  ❌ Allow force pushes (禁用)
  ❌ Allow deletions (禁用)
```

### `develop` 分支（开发主线）

```yaml
Branch: develop
Protection Rules:
  ✅ Require PR before merging
    - Require 1 approval
  ✅ Require status checks
    - Require up-to-date branch
  ✅ Require conversation resolution
  ✅ Include administrators
  ❌ Allow force pushes (禁用)
  ❌ Allow deletions (禁用)
```

## 🔍 验证设置

设置完成后，测试一下：

### 测试 1: 尝试直接推送（应该失败）

```bash
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "test: direct push"
git push origin main
```

**预期结果**：
```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Changes must be made through a pull request.
```

✅ 如果看到这个错误，说明保护规则生效了！

### 测试 2: 通过 PR 合并（应该成功）

```bash
# 1. 创建功能分支
git checkout develop
git checkout -b feature/test-pr

# 2. 提交变更
echo "test" >> test.txt
git add test.txt
git commit -m "feat: test PR workflow"
git push origin feature/test-pr

# 3. 在 GitHub 上创建 PR
# 4. 等待审查和合并
```

## 📝 配置 CODEOWNERS（可选）

创建 `.github/CODEOWNERS` 文件指定代码负责人：

```bash
# 创建文件
mkdir -p .github
cat > .github/CODEOWNERS << 'EOF'
# Bento 项目代码负责人

# 默认负责人（所有文件）
* @idpxyz

# 核心框架
/src/bento/ @idpxyz

# 应用示例
/applications/ @idpxyz

# 文档
/docs/ @idpxyz

# CI/CD
/.github/ @idpxyz
/scripts/ @idpxyz
EOF

# 提交
git add .github/CODEOWNERS
git commit -m "chore: add CODEOWNERS file"
git push origin develop
```

## 🎓 最佳实践

### 1. 命名规范

功能分支应该遵循：
```
feature/<issue-number>-<description>
bugfix/<issue-number>-<description>
hotfix/<version>-<description>
```

### 2. PR 描述模板

创建 `.github/pull_request_template.md`：

```markdown
## 📝 变更说明
<!-- 简要描述这个 PR 做了什么 -->

## 🎯 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] 测试 (test)
- [ ] 其他

## 🔗 关联 Issue
Closes #

## 📋 变更详情
-
-
-

## 🧪 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

## ✅ 检查清单
- [ ] 代码遵循项目规范
- [ ] 通过 `make lint`
- [ ] 通过 `make test`
- [ ] 更新了相关文档
- [ ] 添加了必要的测试
- [ ] 无 Breaking Changes
```

### 3. 审查检查清单

审查者应该检查：
- [ ] 代码符合架构规范（六边形架构）
- [ ] Domain 层无 I/O 操作
- [ ] 使用 Result 类型处理错误
- [ ] 类型注解完整
- [ ] 有对应的测试
- [ ] 通过所有 CI 检查
- [ ] 命名清晰，使用业务语言

## 🔧 配置 GitHub Actions（CI）

创建 `.github/workflows/pr-checks.yml`：

```yaml
name: PR Checks

on:
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run linter
        run: uv run ruff check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest
```

## 📚 相关文档

- [Git 工作流规范](./git-workflow.md)
- [代码审查指南](./git-workflow.md#代码审查)
- [提交规范](./git-workflow.md#提交规范)

## ❓ 常见问题

### Q1: 如果需要紧急修复怎么办？

使用 hotfix 流程：
```bash
git checkout main
git checkout -b hotfix/v0.1.1-critical-fix
# 修复 bug
git push origin hotfix/v0.1.1-critical-fix
# 创建 PR，标记为紧急，快速审查合并
```

### Q2: 可以临时禁用保护规则吗？

可以，但**强烈不推荐**。如果必须：
1. 访问 branch protection settings
2. 点击 "Edit" 按钮
3. 取消勾选规则
4. 完成操作后立即重新启用

### Q3: 如何处理合并冲突？

```bash
# 1. 更新你的分支
git checkout feature/your-branch
git fetch origin
git rebase origin/develop

# 2. 解决冲突
# 编辑文件...
git add .
git rebase --continue

# 3. 强制推送（因为 rebase 改变了历史）
git push origin feature/your-branch --force-with-lease
```

## 🎯 下一步

设置完成后：
1. ✅ 测试分支保护是否生效
2. ✅ 配置 GitHub Actions CI
3. ✅ 创建 PR 模板
4. ✅ 添加 CODEOWNERS 文件
5. ✅ 培训团队成员使用 PR 流程

---

**设置时间**: 约 10-15 分钟
**难度**: ⭐⭐☆☆☆ (简单)
**重要性**: ⭐⭐⭐⭐⭐ (必须)

**祝你配置顺利！** 🎊

