# CI/CD 测试方法总结

## 🎯 三种测试方式

### 1. 🚀 一键测试（推荐）

```bash
./test-ci.sh
```

**测试内容**：
- ✅ Python 版本检查
- ✅ 运行测试套件
- ✅ 代码检查
- ✅ 构建包
- ✅ Release 脚本
- ✅ YAML 语法验证

**时间**: 约 2 分钟

---

### 2. 📋 分步测试

```bash
# 1. 检查 Python
make help
make check-python

# 2. 运行测试
make test

# 3. 代码检查
make lint

# 4. 构建
make build

# 5. 完整流程
make release
```

**适用于**: 调试特定步骤

---

### 3. 🌐 GitHub Actions 测试

#### 测试 Build Workflow

```bash
# 创建测试分支并推送
git checkout -b test-ci
echo "test" >> test.txt
git add test.txt
git commit -m "test: CI workflow"
git push origin test-ci

# 创建 PR
gh pr create --base develop --title "Test CI"

# 查看结果
# https://github.com/your-org/bento/actions
```

#### 测试 Release Workflow

```bash
# 创建 alpha tag
git tag v0.1.0a99
git push origin v0.1.0a99

# GitHub Actions 会自动：
# 1. 运行测试
# 2. 构建包
# 3. 创建 Release
# 4. 发布到 Test PyPI
```

---

## 🔍 验证方法

### 本地验证

```bash
# 检查构建产物
ls -lh dist/
# 应该看到:
# bento_framework-0.1.0a2-py3-none-any.whl
# bento_framework-0.1.0a2.tar.gz

# 测试安装
pip install dist/bento_framework-*.whl
bento --help
```

### GitHub Actions 验证

1. **访问 Actions 页面**
   ```
   https://github.com/your-org/bento/actions
   ```

2. **检查状态**
   - 🟢 绿色勾 = 成功
   - 🔴 红色叉 = 失败
   - 🟡 黄色点 = 运行中

3. **查看日志**
   - 点击工作流名称
   - 展开各个步骤
   - 查看详细输出

### PyPI 验证

```bash
# Test PyPI（alpha 版本）
pip install --index-url https://test.pypi.org/simple/ bento-framework

# PyPI（正式版本）
pip install bento-framework
```

---

## 📊 完整测试流程

### Day 1: 本地测试 ✅

```bash
# 运行本地测试
./test-ci.sh

# 如果全部通过 → 进入 Day 2
```

### Day 2: CI 测试 ✅

```bash
# 推送测试分支
git push origin test-ci

# 创建 PR
gh pr create

# 验证 Actions 运行成功
```

### Day 3: 发布测试 ✅

```bash
# 创建 alpha tag
git tag v0.1.0a99
git push origin v0.1.0a99

# 验证：
# 1. GitHub Release 创建
# 2. 发布到 Test PyPI
# 3. 可以安装使用
```

---

## ✅ 测试清单

使用前确认：

- [ ] 运行 `./test-ci.sh` 全部通过
- [ ] `make help` 显示 Python 3.12.x
- [ ] `make test` 测试通过
- [ ] `make build` 构建成功
- [ ] Push 触发 Build workflow
- [ ] Tag 触发 Release workflow
- [ ] 包可以从 Test PyPI 安装

---

## 🆘 常见问题

### Q: test-ci.sh 运行失败？

**检查**:
```bash
# 确认可执行权限
chmod +x test-ci.sh

# 确认虚拟环境
ls .venv/bin/python3

# 单独运行各步骤
make test
make build
```

### Q: GitHub Actions 未触发？

**原因**:
1. YAML 语法错误
2. 文件路径错误
3. Actions 被禁用

**解决**:
```bash
# 检查 YAML
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml'))"

# 检查 Actions 设置
# GitHub → Settings → Actions → Allow all actions
```

### Q: Release 失败？

**检查**:
1. Secrets 是否配置
2. 版本号是否冲突
3. Tag 格式是否正确

---

## 📚 详细文档

- **[CI_CD_TESTING_GUIDE.md](./CI_CD_TESTING_GUIDE.md)** ⭐ - 完整测试指南
- **[CI_CD_GUIDE.md](./CI_CD_GUIDE.md)** - CI/CD 配置指南
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速命令参考

---

**🎉 开始测试**: `./test-ci.sh`
