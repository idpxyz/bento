# CI/CD 测试指南

## 🎯 测试策略

分为三个层次：本地测试 → 功能测试 → 完整发布测试

---

## 📋 测试清单

### ✅ 第一步：本地测试（不触发 GitHub Actions）

#### 1. 测试 Makefile 命令

```bash
# 检查 Python 版本
make help
# 输出应该显示：
# Python: .venv/bin/python3
# 版本:   3.12 (需要 3.12.x)

# 测试清理
make clean

# 测试构建
make build
# 应该成功生成 dist/ 目录

# 测试版本检查
make check-python
# 如果 Python >= 3.12 应该通过

# 测试完整流程
make release
# 应该运行：测试 → Lint → 构建 → 检查
```

#### 2. 测试 Release 脚本

```bash
# 干运行（不发布）
./scripts/release.sh dry-run

# 应该输出：
# 🍱 Bento Framework 发布脚本
# ℹ️  当前版本: 0.1.0a2
# ℹ️  发布模式: 干运行（不发布）
# ℹ️  运行测试...
# ✅ 测试通过
# ℹ️  运行代码检查...
# ✅ 代码检查通过
# ℹ️  清理构建文件...
# ✅ 清理完成
# ℹ️  构建包...
# ✅ 构建完成
# ℹ️  检查包...
# ✅ 包检查通过
# ✅ 干运行完成，包已准备好但未发布
# ✅ 🎉 发布流程完成！
```

#### 3. 验证工作流文件

```bash
# 检查 YAML 语法
cat .github/workflows/build.yml | python3 -c "import sys, yaml; yaml.safe_load(sys.stdin)"

# 或使用 yamllint（如果安装了）
yamllint .github/workflows/*.yml
```

---

### ✅ 第二步：功能测试（触发 GitHub Actions）

#### 测试 1: Build Workflow（自动测试）

**触发方式**：推送到 main/develop 分支

```bash
# 方式 1: 创建测试分支
git checkout -b test-ci
echo "# Test CI" >> README.md
git add README.md
git commit -m "test: trigger CI workflow"
git push origin test-ci

# 创建 PR 到 main
gh pr create --title "Test CI/CD" --body "测试 CI/CD 工作流"

# 方式 2: 直接推送到 develop
git checkout develop
git merge test-ci
git push origin develop
```

**验证步骤**：

1. **访问 Actions 页面**
   ```
   https://github.com/your-org/bento/actions
   ```

2. **查看运行状态**
   - 应该看到 "Build and Test" 工作流
   - 状态应该是 🟡 运行中 或 ✅ 成功

3. **检查执行步骤**
   点击工作流 → 查看每个步骤：
   - ✅ Set up Python
   - ✅ Install dependencies
   - ✅ Run linters
   - ✅ Run type check
   - ✅ Run tests
   - ✅ Build package
   - ✅ Upload artifacts

4. **下载构建产物**（可选）
   - 点击 "Artifacts"
   - 下载 `dist` 包
   - 验证包的完整性

#### 测试 2: Dependency Review（PR 依赖检查）

**触发方式**：创建 PR 到 main

```bash
# 如果已经有 PR（从上面的测试）
# GitHub Actions 会自动运行

# 或创建新的 PR
git checkout -b update-deps
# 修改 pyproject.toml 添加/更新依赖
vim pyproject.toml
git add pyproject.toml
git commit -m "chore: update dependencies"
git push origin update-deps
gh pr create --base main
```

**验证步骤**：
1. 查看 PR 页面
2. 检查 "Dependency Review" 状态
3. 查看依赖变更评论（如果有）

---

### ✅ 第三步：发布测试（完整流程）

#### 测试 3: Release Workflow（自动发布）

**⚠️ 注意**：这会创建真实的 Release，建议先在测试仓库测试

**准备工作**：

1. **配置 Secrets**（仅第一次）
   ```
   Settings → Secrets and variables → Actions

   添加：
   - PYPI_API_TOKEN
   - TEST_PYPI_API_TOKEN
   ```

2. **选择版本号**
   ```bash
   # Alpha 版本（发布到 Test PyPI）
   VERSION="0.1.0a3"

   # 或正式版本（发布到 PyPI）
   VERSION="0.1.0"
   ```

**执行步骤**：

```bash
# 1. 确保在 main 分支
git checkout main
git pull origin main

# 2. 更新版本号
vim pyproject.toml
# 修改: version = "0.1.0a3"

# 3. 更新 CHANGELOG
vim CHANGELOG.md
# 添加版本变更

# 4. 提交更改
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to ${VERSION}"
git push origin main

# 5. 创建并推送 tag
git tag v${VERSION}
git push origin v${VERSION}

# 6. 等待 GitHub Actions 完成
```

**验证步骤**：

1. **查看 Actions**
   ```
   https://github.com/your-org/bento/actions
   ```
   - 应该看到 "Release" 工作流运行

2. **检查步骤**
   - ✅ Get version from tag
   - ✅ Build package
   - ✅ Create GitHub Release
   - ✅ Publish to PyPI/Test PyPI

3. **验证 Release**
   ```
   https://github.com/your-org/bento/releases
   ```
   - 应该创建了新的 Release
   - 包含 wheel 和 tar.gz 文件
   - 有 Release Notes

4. **验证 PyPI 发布**

   **Alpha 版本**（Test PyPI）：
   ```bash
   # 检查 Test PyPI
   # https://test.pypi.org/project/bento-framework/

   # 测试安装
   pip install --index-url https://test.pypi.org/simple/ bento-framework==${VERSION}
   bento --help
   ```

   **正式版本**（PyPI）：
   ```bash
   # 检查 PyPI
   # https://pypi.org/project/bento-framework/

   # 测试安装
   pip install bento-framework==${VERSION}
   bento --help
   ```

---

## 🧪 分步测试计划

### Day 1: 本地验证

```bash
# 1. 测试所有 make 命令
make help
make clean
make build
make test
make lint

# 2. 测试 release 脚本
./scripts/release.sh dry-run

# 3. 验证 YAML 文件
yamllint .github/workflows/*.yml
```

### Day 2: CI 基础测试

```bash
# 1. 创建测试分支
git checkout -b test-ci-basic
echo "test" >> test.txt
git add test.txt
git commit -m "test: basic CI"
git push origin test-ci-basic

# 2. 创建 PR
gh pr create --base develop

# 3. 观察 Actions 运行
# 访问 GitHub Actions 页面
```

### Day 3: 发布测试（Test PyPI）

```bash
# 1. 创建 alpha 版本
vim pyproject.toml  # version = "0.1.0a99"
git add pyproject.toml
git commit -m "chore: test release"
git push

# 2. 创建 tag
git tag v0.1.0a99
git push origin v0.1.0a99

# 3. 验证发布到 Test PyPI
# 等待几分钟后检查 https://test.pypi.org/
```

---

## 🔍 故障排查

### 问题 1: Actions 未触发

**检查**：
```bash
# 1. 确认工作流文件存在
ls -la .github/workflows/

# 2. 检查 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml'))"

# 3. 检查分支保护规则
# GitHub → Settings → Branches
```

**常见原因**：
- ❌ YAML 语法错误
- ❌ 文件路径错误
- ❌ 分支名称不匹配
- ❌ GitHub Actions 被禁用

### 问题 2: 测试失败

**调试步骤**：

```bash
# 1. 本地运行完整测试
make test-cov

# 2. 检查覆盖率
open htmlcov/index.html

# 3. 查看 Actions 日志
# GitHub Actions → 点击失败的工作流 → 查看错误

# 4. 本地复现
# 使用 Actions 中的 Python 版本
python3.12 -m pytest
```

### 问题 3: 发布失败

**常见原因**：

1. **PyPI Token 错误**
   ```bash
   # 检查 Secrets 是否设置
   # Settings → Secrets → Actions

   # 测试 token
   twine upload --repository testpypi dist/* --verbose
   ```

2. **版本号冲突**
   ```bash
   # 错误: Version 0.1.0 already exists

   # 解决: 使用新版本号
   vim pyproject.toml  # version = "0.1.1"
   git tag v0.1.1
   ```

3. **包构建失败**
   ```bash
   # 本地测试构建
   make clean
   make build
   twine check dist/*
   ```

### 问题 4: Python 版本不匹配

**错误信息**：
```
❌ Python 版本不符合要求
   需要: Python 3.12.x
   当前: Python 3.11
```

**解决**：
```bash
# 方式 1: 安装 Python 3.12
sudo apt install python3.12  # Ubuntu
brew install python@3.12     # macOS

# 方式 2: 创建虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate

# 方式 3: 使用 pyenv
pyenv install 3.12.3
pyenv local 3.12.3
```

---

## 📊 测试矩阵

### 推荐测试顺序

| 步骤 | 测试内容 | 预期结果 | 耗时 |
|-----|---------|---------|------|
| 1 | `make help` | 显示版本信息 | 1s |
| 2 | `make test` | 所有测试通过 | 30s |
| 3 | `make build` | 构建成功 | 20s |
| 4 | `./scripts/release.sh dry-run` | 完整流程 | 1min |
| 5 | Push to develop | Actions 运行 | 2-3min |
| 6 | Create PR | 依赖检查 | 1-2min |
| 7 | Push tag (alpha) | 发布到 Test PyPI | 3-5min |
| 8 | Push tag (release) | 发布到 PyPI | 3-5min |

### 环境测试

| 环境 | 测试命令 | 状态 |
|-----|---------|------|
| Linux (Ubuntu 22.04) | `make build` | ✅ |
| macOS (13+) | `make build` | ✅ |
| Windows (WSL2) | `make build` | ✅ |
| Docker | `make build` | ✅ |
| GitHub Actions | Push tag | ✅ |

---

## 🎯 快速测试脚本

创建测试脚本 `test-ci.sh`：

```bash
#!/bin/bash
set -e

echo "🧪 Bento CI/CD 测试脚本"
echo "================================"

# 1. 本地测试
echo ""
echo "1️⃣  本地测试..."
make clean
make help
make check-python
make test
make build

echo ""
echo "2️⃣  Release 脚本测试..."
./scripts/release.sh dry-run

# 3. YAML 验证
echo ""
echo "3️⃣  验证 YAML 文件..."
for file in .github/workflows/*.yml; do
    echo "检查: $file"
    python3 -c "import yaml; yaml.safe_load(open('$file'))" && echo "✅ 语法正确"
done

echo ""
echo "✅ 本地测试全部通过！"
echo ""
echo "下一步："
echo "  1. git push origin develop  # 测试 Build workflow"
echo "  2. git tag v0.1.0a99 && git push origin v0.1.0a99  # 测试 Release workflow"
```

使用：
```bash
chmod +x test-ci.sh
./test-ci.sh
```

---

## 📚 参考文档

- **[CI_CD_GUIDE.md](./CI_CD_GUIDE.md)** - 完整配置指南
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速命令参考
- **[GitHub Actions 文档](https://docs.github.com/en/actions)**

---

## ✅ 测试完成检查清单

在正式使用前，确认：

- [ ] `make help` 显示正确的 Python 版本
- [ ] `make test` 所有测试通过
- [ ] `make build` 构建成功
- [ ] `./scripts/release.sh dry-run` 完整流程通过
- [ ] Push to develop 触发 Build workflow
- [ ] PR 触发 Dependency Review
- [ ] Push alpha tag 发布到 Test PyPI
- [ ] 从 Test PyPI 安装并验证
- [ ] Push release tag 发布到 PyPI（可选）
- [ ] GitHub Release 自动创建
- [ ] 包可以通过 `pip install` 安装

---

**🎉 完成所有测试后，CI/CD 就完全就绪了！**

**测试时间**: 约 30 分钟（不含等待 GitHub Actions）
**推荐**: 在测试仓库先完整测试一遍
