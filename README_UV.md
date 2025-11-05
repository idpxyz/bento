# 使用 uv 管理项目

本项目使用 `uv` 作为 Python 包管理工具。

## 安装 uv

如果系统中没有 `uv`，请先安装：

### Ubuntu/Linux

```bash
# 方法 1: 使用官方安装脚本（推荐）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 方法 2: 使用项目自动配置脚本
./setup_ubuntu.sh

# 添加到 PATH
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 验证安装
```bash
uv --version
```

## 初始化项目

```bash
# 使用 uv 创建虚拟环境并安装依赖
uv sync

# 或者使用指定版本
uv sync --python 3.12
```

**注意**: `uv sync` 会自动创建和管理 `.venv` 虚拟环境，你不需要手动创建。

## 常用命令

```bash
# 同步依赖（根据 pyproject.toml）
uv sync

# 安装新的依赖
uv add package-name

# 安装开发依赖
uv sync --dev

# 运行命令（自动使用虚拟环境，无需手动激活）
uv run python -m examples.minimal_app.main

# 运行测试（自动使用虚拟环境）
uv run pytest

# 查看 uv 管理的 Python 版本
uv python list

# 安装特定 Python 版本
uv python install 3.12
```

### 如果需要手动激活虚拟环境（通常不需要）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 退出虚拟环境
deactivate
```

**推荐**: 使用 `uv run <command>` 来运行命令，它会自动使用正确的虚拟环境，无需手动激活。

## VS Code 配置

VS Code 已配置为自动识别 `.venv` 目录中的虚拟环境。

如果遇到问题：
1. 按 `Ctrl+Shift+P`，选择 "Python: Select Interpreter"
2. 选择 `.venv/bin/python`

