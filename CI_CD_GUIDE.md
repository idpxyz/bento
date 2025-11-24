# Bento Framework CI/CD 配置指南

## 🎯 概述

完整的自动化工作流，包括测试、构建、发布。

---

## 📋 工作流说明

### 1. Build and Test (`.github/workflows/build.yml`)

**触发条件**：
- Push to `main` 或 `develop` 分支
- Pull Request to `main` 或 `develop` 分支

**执行步骤**：
1. ✅ 在 Python 3.12 上运行测试
2. ✅ 代码格式检查（Ruff）
3. ✅ 类型检查（MyPy）
4. ✅ 运行测试套件（Pytest）
5. ✅ 上传覆盖率报告到 Codecov
6. ✅ 构建 wheel 和 tar.gz
7. ✅ 验证包的完整性
8. ✅ 上传构建产物（保留 7 天）

### 2. Release (`.github/workflows/release.yml`)

**触发条件**：
- 推送版本标签（如 `v0.1.0`, `v1.0.0a1`）

**执行步骤**：
1. ✅ 从标签提取版本号
2. ✅ 更新 `pyproject.toml` 中的版本
3. ✅ 构建发布包
4. ✅ 生成 Release Notes
5. ✅ 创建 GitHub Release
6. ✅ 上传 wheel 和 tar.gz 到 Release
7. ✅ 发布到 PyPI（正式版本）
8. ✅ 发布到 Test PyPI（alpha 版本）

### 3. Dependency Review (`.github/workflows/dependency-review.yml`)

**触发条件**：
- Pull Request to `main`

**执行步骤**：
1. ✅ 检查依赖安全性
2. ✅ 在 PR 中添加依赖审查评论
3. ✅ 检测中等及以上严重性问题

---

## 🔧 初始设置

### 1. GitHub Secrets 配置

需要在 GitHub 仓库设置中添加以下 Secrets：

#### PyPI 发布（正式版）
```
Settings → Secrets and variables → Actions → New repository secret

Name: PYPI_API_TOKEN
Value: pypi-AgEIcHlwaS5vcmcC... (从 PyPI 获取)
```

#### Test PyPI 发布（测试版）
```
Name: TEST_PYPI_API_TOKEN
Value: pypi-AgEIcHlwaS5vcmcC... (从 Test PyPI 获取)
```

#### 如何获取 PyPI Token

1. **注册账号**
   - PyPI: https://pypi.org/account/register/
   - Test PyPI: https://test.pypi.org/account/register/

2. **生成 API Token**
   - 登录后访问：Account settings → API tokens
   - 点击 "Add API token"
   - 命名：`bento-framework-ci`
   - Scope: `Entire account` 或 `Project: bento-framework`
   - 复制生成的 token（只显示一次！）

3. **添加到 GitHub Secrets**
   - 粘贴到对应的 Secret 中

### 2. 启用 GitHub Actions

```bash
# 确保 .github/workflows/ 目录存在
ls .github/workflows/

# 应该看到：
# build.yml
# release.yml
# dependency-review.yml
```

推送到 GitHub 后，Actions 会自动启用。

### 3. 配置分支保护

在 GitHub 仓库设置中：

```
Settings → Branches → Add rule

Branch name pattern: main

☑️ Require status checks to pass before merging
  ☑️ test (Python 3.12)
  ☑️ build

☑️ Require pull request reviews before merging
  Require: 1 approval

☑️ Require linear history
```

---

## 🚀 发布流程

### 方式 1: 自动发布（推荐）

```bash
# 1. 确保所有测试通过
pytest

# 2. 更新 CHANGELOG.md
vim CHANGELOG.md

# 3. 提交更改
git add .
git commit -m "chore: prepare release v0.1.0"

# 4. 创建并推送标签
git tag v0.1.0
git push origin main
git push origin v0.1.0

# 5. GitHub Actions 自动执行：
#    - 运行测试
#    - 构建包
#    - 创建 Release
#    - 上传到 PyPI
```

### 方式 2: 手动发布

```bash
# 1. 本地构建
python -m build

# 2. 测试发布到 Test PyPI
twine upload --repository testpypi dist/*

# 3. 测试安装
pip install --index-url https://test.pypi.org/simple/ bento-framework

# 4. 正式发布到 PyPI
twine upload dist/*
```

---

## 📝 版本命名规范

遵循 [Semantic Versioning](https://semver.org/)：

### 格式

```
MAJOR.MINOR.PATCH[pre-release]

例如：
- 0.1.0      - 初始版本
- 0.1.1      - Bug 修复
- 0.2.0      - 新特性
- 1.0.0      - 稳定版本
- 1.0.0a1    - Alpha 版本
- 1.0.0b1    - Beta 版本
- 1.0.0rc1   - Release Candidate
```

### 标签命名

```bash
# 正式版本
git tag v0.1.0
git tag v0.2.0
git tag v1.0.0

# Alpha 版本（发布到 Test PyPI）
git tag v0.1.0a1
git tag v0.1.0a2

# Beta 版本
git tag v0.1.0b1

# Release Candidate
git tag v0.1.0rc1
```

### 自动发布规则

| 版本类型 | 标签示例 | 发布位置 | 标记为 Pre-release |
|---------|---------|----------|------------------|
| Alpha | `v0.1.0a1` | Test PyPI | ✅ |
| Beta | `v0.1.0b1` | Test PyPI | ✅ |
| RC | `v0.1.0rc1` | Test PyPI | ✅ |
| 正式版 | `v0.1.0` | PyPI | ❌ |

---

## 🎨 Badge 徽章

在 `README.md` 中添加状态徽章：

```markdown
# Bento Framework

[![Build Status](https://github.com/your-org/bento/actions/workflows/build.yml/badge.svg)](https://github.com/your-org/bento/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/your-org/bento/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/bento)
[![PyPI version](https://badge.fury.io/py/bento-framework.svg)](https://badge.fury.io/py/bento-framework)
[![Python Version](https://img.shields.io/pypi/pyversions/bento-framework.svg)](https://pypi.org/project/bento-framework/)
[![License](https://img.shields.io/github/license/your-org/bento.svg)](https://github.com/your-org/bento/blob/main/LICENSE)
```

---

## 📊 监控和通知

### 1. Slack 通知（可选）

在 `.github/workflows/release.yml` 中添加：

```yaml
- name: Notify Slack
  if: success()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "🎉 Bento Framework ${{ steps.get_version.outputs.version }} released!"
      }
```

### 2. Email 通知

GitHub Actions 会自动发送失败通知到：
- 提交者邮箱
- 仓库所有者邮箱

---

## 🔍 故障排查

### 问题 1: Actions 未触发

**检查**：
```bash
# 确认文件位置正确
ls -la .github/workflows/

# 确认 YAML 语法
yamllint .github/workflows/*.yml

# 查看 Actions 日志
# GitHub → Actions → 选择失败的工作流
```

### 问题 2: PyPI 上传失败

**常见原因**：
1. Token 未设置或错误
2. 包名已存在
3. 版本号已存在

**解决**：
```bash
# 检查 token 是否设置
# Settings → Secrets and variables → Actions

# 测试 token
twine upload --repository testpypi dist/*

# 使用新版本号
git tag v0.1.1
git push origin v0.1.1
```

### 问题 3: 测试失败

**常见原因**：
1. 依赖缺失
2. Python 版本不匹配
3. 测试环境问题

**解决**：
```bash
# 本地运行完整测试
pytest --cov

# 检查依赖
pip list

# 本地模拟 CI 环境
docker run -it python:3.12 bash
pip install -e ".[dev]"
pytest
```

---

## 📈 最佳实践

### 1. 版本发布前检查清单

- [ ] 所有测试通过
- [ ] 代码格式检查通过
- [ ] 类型检查通过
- [ ] 更新 CHANGELOG.md
- [ ] 更新版本号
- [ ] 更新文档
- [ ] 本地构建成功
- [ ] 在测试环境安装验证

### 2. 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```bash
# 特性
git commit -m "feat: add support for async repositories"

# Bug 修复
git commit -m "fix: resolve template loading issue"

# 文档
git commit -m "docs: update installation guide"

# 重构
git commit -m "refactor: simplify CLI argument parsing"

# 测试
git commit -m "test: add tests for module generation"

# 构建/CI
git commit -m "chore: update GitHub Actions workflow"
```

### 3. 分支策略

```
main (生产)
  ↑
develop (开发)
  ↑
feature/* (特性分支)
```

**工作流**：
```bash
# 1. 创建特性分支
git checkout -b feature/new-command

# 2. 开发和测试
git add .
git commit -m "feat: add new command"

# 3. 推送并创建 PR
git push origin feature/new-command

# 4. PR 合并到 develop
# 5. develop 测试通过后合并到 main
# 6. main 打标签发布
```

---

## 🛠️ 高级配置

### 1. 矩阵测试（多 Python 版本）

修改 `build.yml`：

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
    os: [ubuntu-latest, macos-latest, windows-latest]
```

### 2. 缓存依赖

添加到 `build.yml`：

```yaml
- name: Cache Python dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### 3. 自动版本号

使用 `python-semantic-release`：

```bash
pip install python-semantic-release

# .github/workflows/release.yml
- name: Semantic Release
  uses: python-semantic-release/python-semantic-release@v9
```

---

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [PyPI 发布指南](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 🎊 快速开始

### 完整设置步骤

```bash
# 1. 确保工作流文件存在
ls .github/workflows/

# 2. 推送到 GitHub
git add .github/
git commit -m "ci: add GitHub Actions workflows"
git push origin main

# 3. 配置 Secrets
# GitHub → Settings → Secrets → Actions → New secret
# 添加 PYPI_API_TOKEN 和 TEST_PYPI_API_TOKEN

# 4. 创建第一个发布
git tag v0.1.0
git push origin v0.1.0

# 5. 查看 Actions 执行
# GitHub → Actions → 查看工作流状态
```

### 验证

```bash
# 检查 Release 是否创建
# GitHub → Releases

# 检查 PyPI 是否发布
pip search bento-framework
# 或访问: https://pypi.org/project/bento-framework/

# 测试安装
pip install bento-framework
bento --help
```

---

**🚀 CI/CD 配置完成！享受自动化发布的便利！**
