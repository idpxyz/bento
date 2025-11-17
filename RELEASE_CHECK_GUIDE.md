# 🚀 GitHub Actions 发布检查指南

## ✅ Tag 推送成功

你已经成功推送了 `v0.1.0` tag！

```bash
✅ Tag v0.1.0 已推送到远程
```

---

## 📋 检查步骤

### 1. 🌐 查看 GitHub Actions 运行状态

访问 Actions 页面查看 workflow 运行情况：

```
https://github.com/idpxyz/bento/actions
```

**查找**：名为 "Release v0.1.0" 的 workflow run

**预期状态**：
- 🔵 **Running** - 正在运行（3-5分钟）
- ✅ **Success** - 成功完成
- ❌ **Failed** - 失败（需要检查日志）

---

### 2. 📦 查看 Releases

访问 Releases 页面：

```
https://github.com/idpxyz/bento/releases/tag/v0.1.0
```

**成功后应该看到**：
- 📝 Release 说明
- 📎 附件文件：
  - `bento_framework-0.1.0-py3-none-any.whl`
  - `bento_framework-0.1.0.tar.gz`

---

### 3. 🔍 查看 PyPI

如果发布到 PyPI 成功：

```
https://pypi.org/project/bento-framework/
```

**验证安装**：
```bash
pip install bento-framework
```

---

## 🔧 首次发布配置

### ⚠️ 必需：配置 PyPI API Token

如果这是首次发布，需要配置 PyPI token：

#### 步骤 1: 生成 PyPI Token

1. 登录 PyPI: https://pypi.org/
2. 访问 Account settings → API tokens
   ```
   https://pypi.org/manage/account/token/
   ```
3. 点击 **"Add API token"**
4. 配置：
   - **Token name**: `github-actions-bento`
   - **Scope**: `Entire account` 或 `Project: bento-framework`
5. 点击 **"Add token"**
6. **复制 token**（只显示一次！格式：`pypi-AgE...`）

#### 步骤 2: 添加到 GitHub Secrets

1. 访问仓库 Settings → Secrets and variables → Actions
   ```
   https://github.com/idpxyz/bento/settings/secrets/actions
   ```
2. 点击 **"New repository secret"**
3. 添加 secret：
   - **Name**: `PYPI_API_TOKEN`
   - **Secret**: 粘贴你的 token（`pypi-AgE...`）
4. 点击 **"Add secret"**

#### 步骤 3: 重新触发发布

如果 Actions 因为缺少 token 失败：

```bash
# 删除 tag
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0

# 重新创建并推送
git tag v0.1.0
git push origin v0.1.0
```

---

## 📊 快速检查命令

使用提供的检查脚本：

```bash
./check-release.sh
```

或手动检查 PyPI：

```bash
python3 -c "
import urllib.request, json
try:
    data = json.loads(urllib.request.urlopen('https://pypi.org/pypi/bento-framework/json').read())
    print(f'✅ 包已发布: v{data[\"info\"][\"version\"]}')
    print(f'🔗 {data[\"info\"][\"package_url\"]}')
except:
    print('⏳ 包尚未发布')
"
```

---

## 🐛 故障排除

### 问题 1: Actions 一直显示 "Waiting"

**原因**：Workflow 可能在排队

**解决**：
- 等待几分钟
- 检查仓库是否有其他正在运行的 workflows

### 问题 2: Actions 失败 - "PYPI_API_TOKEN not found"

**原因**：未配置 PyPI token

**解决**：按照上面 "配置 PyPI API Token" 步骤操作

### 问题 3: Actions 失败 - "Permission denied"

**原因**：Workflow 权限不足

**解决**：
1. 访问 Settings → Actions → General
   ```
   https://github.com/idpxyz/bento/settings/actions
   ```
2. 在 "Workflow permissions" 部分
3. 选择 **"Read and write permissions"**
4. 勾选 **"Allow GitHub Actions to create and approve pull requests"**
5. 保存

### 问题 4: PyPI 发布失败 - "File already exists"

**原因**：版本号已存在

**解决**：
- PyPI 不允许重新上传相同版本
- 需要修改版本号（如 v0.1.1）
- 或使用 Test PyPI 测试

### 问题 5: 测试失败

**原因**：代码有问题或环境问题

**解决**：
1. 查看 Actions 日志
2. 本地运行 `make test` 确保通过
3. 修复问题后重新推送 tag

---

## 📈 Workflow 流程说明

你的 `release.yml` workflow 会执行：

### 阶段 1: 构建和测试
- ✅ Checkout 代码
- ✅ 设置 Python 3.12
- ✅ 安装依赖
- ✅ 运行测试
- ✅ 运行 lint 检查

### 阶段 2: 构建包
- ✅ 从 tag 提取版本号
- ✅ 更新 pyproject.toml 版本
- ✅ 构建 wheel 和 sdist

### 阶段 3: 发布
- ✅ 上传到 PyPI
- ✅ 创建 GitHub Release
- ✅ 上传构建产物

---

## 📝 后续步骤

发布成功后：

### 1. 验证安装

```bash
# 创建测试环境
python3 -m venv test_env
source test_env/bin/activate

# 安装发布的包
pip install bento-framework

# 验证
python -c "import bento; print(bento.__version__)"
```

### 2. 更新文档

- 更新 README.md
- 更新 CHANGELOG.md
- 发布 Release Notes

### 3. 通知团队

- 发送发布通知
- 更新项目文档
- 通知依赖方升级

---

## 🔗 相关链接

| 资源 | 链接 |
|------|------|
| GitHub Actions | https://github.com/idpxyz/bento/actions |
| GitHub Releases | https://github.com/idpxyz/bento/releases |
| PyPI 包 | https://pypi.org/project/bento-framework/ |
| Workflow 配置 | https://github.com/idpxyz/bento/blob/main/.github/workflows/release.yml |
| 仓库设置 | https://github.com/idpxyz/bento/settings |

---

## 💡 最佳实践

### 发布前检查清单

- [ ] 所有测试通过 (`make test`)
- [ ] 代码检查通过 (`make lint`)
- [ ] 包构建成功 (`make build`)
- [ ] CHANGELOG.md 已更新
- [ ] 版本号符合语义化版本规范
- [ ] 文档已更新

### 语义化版本规范

- **v0.1.0** - 初始版本
- **v0.1.1** - Bug 修复
- **v0.2.0** - 新功能（向后兼容）
- **v1.0.0** - 稳定版本
- **v2.0.0** - 重大变更（不向后兼容）

### Alpha/Beta 版本

- **v0.1.0a1** - Alpha 1
- **v0.1.0b1** - Beta 1
- **v0.1.0rc1** - Release Candidate 1

---

## 🎉 成功发布的标志

当看到以下所有内容时，说明发布成功：

- ✅ GitHub Actions workflow 显示绿色勾号
- ✅ GitHub Releases 页面有新的 release
- ✅ PyPI 上可以搜索到包
- ✅ 可以通过 `pip install bento-framework` 安装
- ✅ 版本号正确

---

**祝发布顺利！🚀**
