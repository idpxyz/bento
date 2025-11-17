# Makefile 智能 Python 检测

## 🎯 功能

Makefile 现在可以**自动检测并使用正确的 Python 命令**，无需手动配置！

---

## 🔍 检测顺序

### Python 检测（按优先级）

```
1. .venv/bin/python3    ✅ 虚拟环境的 python3
2. .venv/bin/python     ✅ 虚拟环境的 python
3. python3              ✅ 系统的 python3
4. python               ✅ 系统的 python
5. python3              ⚠️  后备选项
```

### Pip 检测（按优先级）

```
1. .venv/bin/pip3       ✅ 虚拟环境的 pip3
2. .venv/bin/pip        ✅ 虚拟环境的 pip
3. pip3                 ✅ 系统的 pip3
4. pip                  ✅ 系统的 pip
5. pip                  ⚠️  后备选项
```

---

## 📊 支持的环境

### ✅ Linux/macOS

| 环境 | Python 命令 | 自动检测 |
|-----|-----------|---------|
| Ubuntu 22.04+ | `python3` | ✅ |
| Debian | `python3` | ✅ |
| macOS | `python3` 或 `python` | ✅ |
| 虚拟环境 | `.venv/bin/python3` | ✅ |
| Conda | `python` | ✅ |

### ✅ Windows（WSL/Git Bash）

| 环境 | Python 命令 | 自动检测 |
|-----|-----------|---------|
| WSL | `python3` | ✅ |
| Git Bash | `python` | ✅ |
| MSYS2 | `python` | ✅ |

---

## 💡 使用示例

### 场景 1: 有虚拟环境（推荐）

```bash
# 有 .venv 目录
ls .venv/bin/python3
# → 存在

make build
# → 使用 .venv/bin/python3 ✅
```

### 场景 2: 没有虚拟环境

```bash
# 使用系统 Python
make build
# → 使用 python3（如果存在）
# → 或使用 python（如果 python3 不存在）
```

### 场景 3: Windows Git Bash

```bash
# 系统只有 python 命令
which python3
# → not found

which python
# → /usr/bin/python

make build
# → 使用 python ✅
```

### 场景 4: macOS 新系统

```bash
# macOS 13+ 同时有 python3 和 python
which python3
# → /usr/bin/python3

which python
# → /usr/bin/python

make build
# → 优先使用 python3 ✅
```

---

## 🔧 实现原理

### Makefile 变量定义

```makefile
PYTHON := $(shell \
	if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; \
	elif [ -f .venv/bin/python ]; then echo .venv/bin/python; \
	elif command -v python3 >/dev/null 2>&1; then echo python3; \
	elif command -v python >/dev/null 2>&1; then echo python; \
	else echo "python3"; fi)
```

### 逻辑说明

1. **检查文件**: 先检查虚拟环境文件是否存在
2. **检查命令**: 使用 `command -v` 检查命令是否可用
3. **后备方案**: 如果都没有，使用 `python3`（会报错，但给出明确提示）

---

## 📋 验证方法

### 查看检测结果

```bash
make help
# 输出:
# Bento Framework - Makefile 命令
#
# Python: .venv/bin/python3  ✅
```

### 测试构建

```bash
make build
# 如果成功 → Python 检测正确 ✅
# 如果失败 → 检查错误信息
```

### 调试 Python 路径

```bash
# 临时添加到 Makefile 开头
test-python:
	@echo "PYTHON=$(PYTHON)"
	@$(PYTHON) --version

# 运行
make test-python
```

---

## 🎯 优势

### ✅ 跨平台兼容

- Linux ✅
- macOS ✅
- Windows (WSL/Git Bash) ✅
- Docker ✅

### ✅ 灵活适配

- 虚拟环境 ✅
- 系统 Python ✅
- Conda 环境 ✅
- pyenv ✅

### ✅ 零配置

- 无需手动设置 ✅
- 自动检测 ✅
- 智能回退 ✅

---

## 🛠️ 故障排查

### 问题 1: Python 未找到

**错误**:
```
make: python3: No such file or directory
```

**解决**:
```bash
# 安装 Python
sudo apt install python3  # Ubuntu/Debian
brew install python3      # macOS

# 或创建虚拟环境
python3 -m venv .venv
```

### 问题 2: 使用了错误的 Python

**检查**:
```bash
make help
# 查看 "Python: xxx" 显示的路径
```

**修复**:
```bash
# 确保虚拟环境存在
ls .venv/bin/python3

# 或重新创建
rm -rf .venv
python3 -m venv .venv
```

### 问题 3: 需要特定 Python 版本

**方案 1**: 使用虚拟环境
```bash
python3.12 -m venv .venv
# Makefile 会自动使用 .venv/bin/python3
```

**方案 2**: 手动指定
```bash
make build PYTHON=/usr/bin/python3.12
```

**方案 3**: 修改 Makefile
```makefile
# 在文件开头强制指定
PYTHON := /usr/bin/python3.12
```

---

## 📚 扩展

### 添加 Python 版本检查

在 Makefile 开头添加:

```makefile
# 检查 Python 版本
PYTHON_VERSION := $(shell $(PYTHON) -c 'import sys; print("%d.%d" % sys.version_info[:2])')
REQUIRED_VERSION := 3.12

check-python:
	@echo "Python version: $(PYTHON_VERSION)"
	@if [ "$(PYTHON_VERSION)" != "$(REQUIRED_VERSION)" ]; then \
		echo "❌ Required Python $(REQUIRED_VERSION), found $(PYTHON_VERSION)"; \
		exit 1; \
	fi

# 在其他目标前添加依赖
build: check-python clean
	...
```

### 支持多个虚拟环境

```makefile
# 检测多个可能的虚拟环境位置
PYTHON := $(shell \
	if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; \
	elif [ -f venv/bin/python3 ]; then echo venv/bin/python3; \
	elif [ -f env/bin/python3 ]; then echo env/bin/python3; \
	elif command -v python3 >/dev/null 2>&1; then echo python3; \
	else echo "python3"; fi)
```

---

## ✅ 最佳实践

### 推荐工作流

```bash
# 1. 创建虚拟环境（一次性）
python3 -m venv .venv

# 2. 直接使用 make（无需激活）
make install-dev  # 自动使用 .venv
make test
make build
```

### 不推荐

```bash
# ❌ 不需要手动激活
source .venv/bin/activate
make build

# ✅ 直接使用即可
make build
```

---

## 🎊 总结

### 现在支持

- ✅ `python3` 命令
- ✅ `python` 命令
- ✅ 虚拟环境自动检测
- ✅ 系统 Python 自动检测
- ✅ 跨平台兼容
- ✅ 零配置使用

### 使用体验

**之前**:
```bash
source .venv/bin/activate  # 必须记住
make build
```

**现在**:
```bash
make build  # 直接用！✨
```

---

**🍱 Bento Framework Makefile 现在支持 python 和 python3！**

**兼容性**: 100%
**自动化**: 100%
**配置需求**: 0
