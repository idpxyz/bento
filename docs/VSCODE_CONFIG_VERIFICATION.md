# VS Code 配置验证指南

本文档说明如何验证 Bento 项目的 VS Code 配置是否正确。

## 快速验证

### 自动化验证脚本

```bash
# 运行配置验证脚本
./scripts/check-config.sh
```

**预期输出：**
```
🔍 VS Code 配置验证
══════════════════════════════════════

1️⃣  格式化工具配置
✅ 所有配置使用 Ruff 格式化

2️⃣  扩展推荐
✅ 推荐 Ruff 扩展
✅ 排除冲突扩展 (Black, Flake8)

3️⃣  任务配置
✅ 使用 Makefile 命令

4️⃣  Makefile 命令
✅ 所有必需命令存在: fmt lint test test-cov dev clean

5️⃣  PYTHONPATH 配置
✅ 跨平台 PYTHONPATH 配置正确

══════════════════════════════════════
📊 验证结果: 6 通过 / 0 失败
══════════════════════════════════════
✅ 所有检查通过！
```

## 手动验证清单

### 1. 扩展推荐 (extensions.json)

#### ✅ 检查点
- [ ] 推荐 `charliermarsh.ruff` 扩展
- [ ] 推荐 `ms-python.python` 和 `ms-python.vscode-pylance`
- [ ] **不推荐** `ms-python.black-formatter` (在 unwantedRecommendations 中)
- [ ] **不推荐** `ms-python.flake8` (在 unwantedRecommendations 中)

#### 验证命令
```bash
# 检查项目根目录
grep "charliermarsh.ruff" .vscode/extensions.json
grep "unwantedRecommendations" .vscode/extensions.json

# 检查 my-shop
grep "charliermarsh.ruff" applications/my-shop/.vscode/extensions.json

# 检查 CLI 模板
grep "charliermarsh.ruff" src/bento/toolkit/templates/project/vscode/extensions.json.tpl
```

### 2. 编辑器设置 (settings.json)

#### ✅ 检查点
- [ ] 使用 Ruff 作为默认格式化工具
- [ ] 配置保存时自动格式化
- [ ] 配置自动组织导入和修复
- [ ] 禁用 Python 扩展内置的 linter
- [ ] 配置跨平台 PYTHONPATH

#### 验证命令
```bash
# 检查格式化工具
grep '"editor.defaultFormatter": "charliermarsh.ruff"' .vscode/settings.json

# 检查 Ruff 配置
grep '"ruff.nativeServer": true' .vscode/settings.json

# 检查禁用冲突的 linter
grep '"python.linting.enabled": false' .vscode/settings.json

# 检查 PYTHONPATH
grep 'terminal.integrated.env.linux' .vscode/settings.json
```

### 3. 任务配置 (tasks.json)

#### ✅ 检查点
- [ ] 所有任务使用 `make` 命令
- [ ] 包含 `make test` 任务
- [ ] 包含 `make fmt` 任务
- [ ] 包含 `make lint` 任务
- [ ] 包含 `make dev` 任务

#### 验证命令
```bash
# 检查任务使用 Makefile
grep '"command": "make ' .vscode/tasks.json

# 检查各个任务
grep '"command": "make test"' .vscode/tasks.json
grep '"command": "make fmt"' .vscode/tasks.json
grep '"command": "make lint"' .vscode/tasks.json
grep '"command": "make dev"' .vscode/tasks.json
```

### 4. Makefile

#### ✅ 检查点
- [ ] 存在 `fmt` 目标 (使用 Ruff 格式化)
- [ ] 存在 `lint` 目标 (使用 Ruff 检查)
- [ ] 存在 `test` 目标 (运行 Pytest)
- [ ] 存在 `test-cov` 目标 (覆盖率报告)
- [ ] 存在 `dev` 目标 (启动开发服务器)
- [ ] 存在 `clean` 目标 (清理缓存)

#### 验证命令
```bash
# 检查所有必需的目标
make help

# 测试各个命令 (需要安装依赖)
make fmt --dry-run
make lint --dry-run
make test --dry-run
```

### 5. 调试配置 (launch.json)

#### ✅ 检查点
- [ ] FastAPI 调试配置
- [ ] 当前文件调试配置
- [ ] Pytest 调试配置
- [ ] 正确的 PYTHONPATH 环境变量

#### 验证命令
```bash
grep '"name": "Python: FastAPI"' .vscode/launch.json
grep 'PYTHONPATH' .vscode/launch.json
```

## 配置一致性验证

### 检查点
所有三个位置的配置应该保持一致：

1. **项目根目录**: `/workspace/bento/.vscode/`
2. **示例项目**: `/workspace/bento/applications/my-shop/.vscode/`
3. **CLI 模板**: `/workspace/bento/src/bento/toolkit/templates/project/vscode/`

### 对比命令

```bash
# 对比扩展推荐
diff -u .vscode/extensions.json \
        applications/my-shop/.vscode/extensions.json

# 对比格式化配置
grep -A 5 '\[python\]' .vscode/settings.json
grep -A 5 '\[python\]' applications/my-shop/.vscode/settings.json
```

## 实际使用测试

### 1. 测试 CLI 生成的项目

```bash
# 生成测试项目
bento init test-project --output /tmp

# 验证配置
ls -la /tmp/test-project/.vscode/
cat /tmp/test-project/.vscode/extensions.json | grep ruff
cat /tmp/test-project/Makefile | grep "^fmt:"
```

### 2. 测试格式化功能

```bash
# 创建测试文件
echo 'import os,sys
def test( ):
    print("test")' > test_format.py

# 使用 Ruff 格式化
make fmt

# 检查格式化结果
cat test_format.py
```

预期：代码应该被正确格式化。

### 3. 测试 VS Code 集成

在 VS Code 中打开项目：

1. **扩展提示**: 应该提示安装 Ruff 扩展
2. **保存自动格式化**: 编辑 Python 文件保存时自动格式化
3. **任务运行**: 按 `Ctrl+Shift+P` → `Tasks: Run Task` → 看到 Makefile 任务
4. **调试**: 按 `F5` → 看到预配置的调试选项

## 常见问题排查

### Q: 保存时没有自动格式化？

**检查：**
```bash
# 1. 确认 Ruff 扩展已安装
code --list-extensions | grep ruff

# 2. 确认配置正确
grep 'formatOnSave' .vscode/settings.json
grep 'defaultFormatter.*ruff' .vscode/settings.json
```

### Q: make 命令找不到？

**检查：**
```bash
# 1. 确认 Makefile 存在
ls -la Makefile

# 2. 确认在正确的目录
pwd

# 3. 手动运行 Python 命令
python3 -m ruff check .
```

### Q: 任务列表中没有 Makefile 任务？

**检查：**
```bash
# 1. 确认 tasks.json 存在
ls -la .vscode/tasks.json

# 2. 确认配置正确
grep 'make ' .vscode/tasks.json

# 3. 重新加载 VS Code 窗口
# 按 Ctrl+Shift+P → "Developer: Reload Window"
```

## 配置标准总结

| 配置项 | 标准值 | 位置 |
|-------|--------|------|
| 格式化工具 | `charliermarsh.ruff` | `settings.json` |
| 自动格式化 | `true` | `settings.json` |
| 推荐扩展 | Ruff, Python, Pylance | `extensions.json` |
| 排除扩展 | Black, Flake8 | `extensions.json` |
| 任务命令 | `make test/fmt/lint/dev` | `tasks.json` |
| Makefile 工具 | Ruff (格式化), Pytest (测试) | `Makefile` |
| PYTHONPATH | `${workspaceFolder}:${workspaceFolder}/src` | `settings.json` |

## 验证成功标准

当所有以下条件满足时，配置即为正确：

✅ **自动化验证脚本通过** (`./scripts/check-config.sh`)
✅ **CLI 生成的项目包含完整配置**
✅ **VS Code 打开项目时推荐安装 Ruff**
✅ **保存 Python 文件时自动格式化**
✅ **任务列表中有 Makefile 任务**
✅ **调试配置可用**

---

**最后更新**: 2025-11-17
**维护者**: Bento Team
