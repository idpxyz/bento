# 🔍 CI/CD 失败诊断报告

## 📋 检查结果

### ✅ 已确认的信息

- **Tag**: v0.1.0 已成功推送
- **版本类型**: 正式版本（不是 alpha/beta）
- **Tag 数量**: 这是第一个 tag

---

## ❌ 发现的问题

### 问题 1: Changelog 生成会失败 ⚠️

**位置**: `.github/workflows/release.yml` 第 53 行

```yaml
git log --pretty=format:"- %s (%h)" $(git describe --tags --abbrev=0 HEAD^)..HEAD
```

**原因**:
- 这是第一个 tag，没有之前的 tag
- `git describe --tags --abbrev=0 HEAD^` 会失败
- 导致 changelog 生成步骤失败

**影响**:
- GitHub Release 创建可能失败
- 或者 Release Notes 为空

---

### 问题 2: 缺少 PyPI API Token ⚠️⚠️

**位置**: `.github/workflows/release.yml` 第 69-74 行

```yaml
- name: Publish to PyPI
  if: ${{ !contains(steps.get_version.outputs.version, 'a') }}
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

**原因**:
- v0.1.0 不包含 'a'，会触发发布到 PyPI
- 需要 `PYPI_API_TOKEN` secret
- 如果没有配置，发布步骤会失败

**影响**:
- ❌ 无法发布到 PyPI
- Workflow 会报错并失败

---

### 问题 3: 包名可能冲突 ⚠️

**检查**: PyPI 上是否已存在 `bento-framework` 包

如果包名已被占用，需要：
- 更改包名
- 或者联系 PyPI 管理员

---

## 🔧 修复方案

### 方案 1: 修复 Changelog 生成（推荐）

更新 `.github/workflows/release.yml` 第 48-54 行：

```yaml
- name: Generate changelog
  id: changelog
  run: |
    echo "## What's Changed" > RELEASE_NOTES.md

    # 检查是否有之前的 tag
    PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")

    if [ -z "$PREV_TAG" ]; then
      # 第一个 release，显示所有提交
      echo "Initial release" >> RELEASE_NOTES.md
      echo "" >> RELEASE_NOTES.md
      echo "### Recent commits:" >> RELEASE_NOTES.md
      git log --pretty=format:"- %s (%h)" -n 20 >> RELEASE_NOTES.md
    else
      # 显示自上个 tag 以来的更改
      git log --pretty=format:"- %s (%h)" ${PREV_TAG}..HEAD >> RELEASE_NOTES.md
    fi

    cat RELEASE_NOTES.md
```

---

### 方案 2: 配置 PyPI Token

#### 选项 A: 发布到 PyPI（正式版）

1. **创建 PyPI 账号**（如果没有）
   - 访问: https://pypi.org/account/register/

2. **生成 API Token**
   - 访问: https://pypi.org/manage/account/token/
   - 点击 "Add API token"
   - Token name: `github-actions-bento`
   - Scope: `Entire account`（首次）或 `Project: bento-framework`
   - 点击 "Add token"
   - **复制 token**（格式：`pypi-AgE...`，只显示一次！）

3. **添加到 GitHub Secrets**
   - 访问: https://github.com/idpxyz/bento/settings/secrets/actions
   - 点击 "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Secret: 粘贴你的 token
   - 点击 "Add secret"

#### 选项 B: 使用 Test PyPI（测试）

如果只想测试，使用 alpha 版本：

```bash
# 删除当前 tag
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0

# 创建 alpha 版本 tag
git tag v0.1.0a1
git push origin v0.1.0a1
```

这样会发布到 Test PyPI，需要配置 `TEST_PYPI_API_TOKEN`：

1. 访问: https://test.pypi.org/manage/account/token/
2. 创建 token
3. 添加到 GitHub Secrets，名称：`TEST_PYPI_API_TOKEN`

#### 选项 C: 暂时跳过 PyPI 发布

修改 workflow，注释掉 PyPI 发布步骤：

```yaml
# - name: Publish to PyPI
#   if: ${{ !contains(steps.get_version.outputs.version, 'a') }}
#   env:
#     TWINE_USERNAME: __token__
#     TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
#   run: |
#     twine upload dist/*
```

---

### 方案 3: 检查包名是否可用

运行检查：

```bash
curl -s https://pypi.org/pypi/bento-framework/json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'❌ 包名已被占用: {data[\"info\"][\"name\"]}')
    print(f'   作者: {data[\"info\"][\"author\"]}')
except:
    print('✅ 包名可用')
"
```

如果包名被占用，需要更改 `pyproject.toml` 中的包名。

---

## 🚀 快速修复步骤

### 立即修复（推荐顺序）

#### 1. 修复 Changelog 生成

```bash
# 编辑 workflow 文件
nano .github/workflows/release.yml

# 按照上面的方案 1 修改第 48-54 行
```

#### 2. 配置 PyPI Token

按照方案 2 的选项 A 或 B 操作。

#### 3. 重新触发 workflow

```bash
# 删除失败的 tag
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0

# 提交 workflow 修复
git add .github/workflows/release.yml
git commit -m "fix: update release workflow for first release"
git push

# 重新创建 tag
git tag v0.1.0
git push origin v0.1.0
```

---

## 📊 预期的成功流程

修复后，workflow 应该：

1. ✅ **Checkout 代码**
2. ✅ **设置 Python 3.12**
3. ✅ **安装依赖** (build, twine)
4. ✅ **提取版本号** (0.1.0)
5. ✅ **更新 pyproject.toml**
6. ✅ **构建包** (wheel + tar.gz)
7. ✅ **检查包** (twine check)
8. ✅ **生成 changelog** (修复后不会失败)
9. ✅ **创建 GitHub Release** (包含构建产物)
10. ✅ **发布到 PyPI** (如果配置了 token)

---

## 🔍 如何查看具体错误

### 方法 1: GitHub Actions 日志

1. 访问: https://github.com/idpxyz/bento/actions
2. 点击失败的 workflow run
3. 点击具体的失败步骤查看详细日志

### 方法 2: 使用 GitHub CLI

```bash
# 安装 gh CLI（如果未安装）
sudo apt install gh

# 查看最近的 workflow runs
gh run list --workflow=release.yml

# 查看具体的 run 日志
gh run view <run-id> --log
```

---

## 📝 验证清单

修复后验证：

- [ ] Changelog 生成步骤成功
- [ ] GitHub Release 创建成功
- [ ] 构建产物上传成功
- [ ] PyPI 发布成功（如果配置了）
- [ ] 可以通过 `pip install bento-framework` 安装

---

## 💡 建议

### 短期
1. 先修复 changelog 生成问题
2. 配置 PyPI token
3. 重新触发发布

### 长期
1. 添加 workflow 测试
2. 使用 Test PyPI 进行测试
3. 完善错误处理
4. 添加发布前检查

---

## 🆘 需要更多帮助？

如果以上方案无法解决问题，请提供：

1. GitHub Actions 的具体错误日志
2. 失败的步骤名称
3. 完整的错误消息

我会帮你进一步诊断！
