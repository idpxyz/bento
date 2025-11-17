# Bento Framework - 快速参考

## 🚀 常用命令

### 快速测试 CI/CD

```bash
# 一键运行所有本地测试
./test-ci.sh

# 或分步测试
make help         # 检查 Python 版本
make test         # 运行测试
make build        # 构建包
```

### Makefile 命令

```bash
# 查看所有命令（显示检测到的 Python）
make help

# 💡 无需激活虚拟环境，Makefile 自动检测！

# 开发
make fmt          # 格式化代码
make lint         # 代码检查
make test         # 运行测试
make test-cov     # 测试 + 覆盖率
make dev          # 启动开发服务器

# 构建和发布
make clean        # 清理构建文件
make build        # 构建包
make release      # 完整发布流程（测试、检查、构建）
make publish-test # 发布到 Test PyPI
make publish      # 发布到 PyPI
```

### Release 脚本

```bash
# 干运行（只检查，不发布）
./scripts/release.sh dry-run

# 发布到 Test PyPI
./scripts/release.sh test

# 发布到 PyPI（生产）
./scripts/release.sh prod

# 创建 tag（触发 CI/CD）
./scripts/release.sh tag
```

---

## 📦 发布流程

### 方式 1: 使用 Makefile（推荐）

```bash
# 1. 完整检查
make release

# 2. 查看输出，确认一切正常

# 3a. 手动发布（需要 PyPI token）
make publish

# 3b. 或创建 tag 让 CI/CD 自动发布
git tag v0.1.0
git push origin v0.1.0
```

### 方式 2: 使用 Release 脚本

```bash
# 创建 tag 并触发 CI/CD
./scripts/release.sh tag
git push origin v0.1.0a2  # 推送 tag
```

### 方式 3: 完全自动（GitHub Actions）

```bash
# 只需要推送 tag
git tag v0.1.0
git push origin v0.1.0

# GitHub Actions 会自动：
# 1. 运行测试
# 2. 构建包
# 3. 创建 Release
# 4. 上传到 PyPI
```

---

## 🔧 开发工作流

### 日常开发

```bash
# 1. 修改代码
vim src/bento/...

# 2. 格式化
make fmt

# 3. 运行测试
make test

# 4. 提交
git add .
git commit -m "feat: add new feature"
git push
```

### 完整检查

```bash
# 运行所有检查
make lint        # 代码检查
make test-cov    # 测试 + 覆盖率
make build       # 构建验证
```

---

## 📊 CI/CD 工作流

### 自动触发

| 事件 | 触发的 Workflow | 执行内容 |
|-----|----------------|---------|
| Push to `main` | Build and Test | 测试、Lint、构建 |
| Pull Request | Build and Test<br>Dependency Review | 完整检查 + 依赖审查 |
| Push tag `v*` | Release | 测试、构建、发布到 PyPI |

### 手动触发发布

```bash
# 1. 确保在 main 分支
git checkout main
git pull

# 2. 更新版本号（在 pyproject.toml）
vim pyproject.toml
# version = "0.1.1"

# 3. 更新 CHANGELOG
vim CHANGELOG.md

# 4. 提交
git add .
git commit -m "chore: bump version to 0.1.1"
git push

# 5. 创建并推送 tag
git tag v0.1.1
git push origin v0.1.1

# 6. 查看 GitHub Actions
# https://github.com/your-org/bento/actions
```

---

## 🎯 版本号规范

```
格式: MAJOR.MINOR.PATCH[pre-release]

示例:
0.1.0     - 初始版本
0.1.1     - Bug 修复
0.2.0     - 新特性（向后兼容）
1.0.0     - 稳定版本
1.0.0a1   - Alpha（发布到 Test PyPI）
1.0.0b1   - Beta
1.0.0rc1  - Release Candidate
```

### 何时增加版本号

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的新功能
- **PATCH**: 向后兼容的 Bug 修复

---

## 🔐 必需的 Secrets

在 GitHub 仓库设置中配置：

```
Settings → Secrets and variables → Actions

PYPI_API_TOKEN       - PyPI 发布 token
TEST_PYPI_API_TOKEN  - Test PyPI 发布 token
```

获取 token：
1. 访问 https://pypi.org/manage/account/token/
2. 创建 API token
3. 复制并保存到 GitHub Secrets

---

## 📝 文件说明

| 文件 | 用途 |
|-----|------|
| `Makefile` | 本地开发命令 |
| `scripts/release.sh` | 发布脚本 |
| `.github/workflows/build.yml` | 自动测试 |
| `.github/workflows/release.yml` | 自动发布 |
| `CI_CD_GUIDE.md` | CI/CD 详细指南 |

---

## 🆘 常见问题

### Q: 如何本地测试发布？

```bash
# 使用 dry-run 模式
./scripts/release.sh dry-run

# 或使用 make
make release  # 只检查，不发布
```

### Q: 如何发布 alpha 版本？

```bash
# 1. 版本号包含 'a'
# pyproject.toml: version = "0.1.0a1"

# 2. 创建 tag
git tag v0.1.0a1
git push origin v0.1.0a1

# 3. GitHub Actions 自动发布到 Test PyPI
```

### Q: 如何回滚发布？

```bash
# PyPI 不支持删除已发布版本
# 只能发布新版本

# 立即发布修复版本
git tag v0.1.2
git push origin v0.1.2
```

### Q: 构建失败怎么办？

```bash
# 1. 查看详细错误
make build

# 2. 清理后重试
make clean
make build

# 3. 检查依赖
pip install build twine
```

---

## ✅ 发布前检查清单

- [ ] 所有测试通过: `make test`
- [ ] 代码检查通过: `make lint`
- [ ] 版本号已更新
- [ ] CHANGELOG 已更新
- [ ] 文档已更新
- [ ] 本地构建成功: `make build`
- [ ] Git 工作目录干净
- [ ] 在正确的分支（main）

---

**快速开始**: `make help` 或 `./scripts/release.sh`
