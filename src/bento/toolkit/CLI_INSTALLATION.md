# Bento CLI 安装和使用

## 🚀 快速设置（推荐）

**一键添加到 PATH：**
```bash
cd /workspace/bento
./scripts/setup-path.sh
source ~/.bashrc  # 或 source ~/.zshrc
```

验证：
```bash
bento --help
```

## 快速开始

### 方式 1: 相对路径（无需安装）

如果您在 Bento 项目目录中：

```bash
cd /workspace/bento
./bin/bento init my-project
./bin/bento gen module Product --context catalog
```

### 方式 2: 添加到 PATH（推荐）

**临时添加（当前会话）：**
```bash
export PATH="/workspace/bento/bin:$PATH"

# 现在可以直接使用
bento init my-project
bento gen module Product --context catalog
```

**永久添加（推荐用于开发）：**

添加到您的 shell 配置文件（`~/.bashrc` 或 `~/.zshrc`）：

```bash
# 添加到 ~/.bashrc
echo 'export PATH="/workspace/bento/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 或添加到 ~/.zshrc
echo 'export PATH="/workspace/bento/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

验证：
```bash
which bento
# 应该输出: /workspace/bento/bin/bento

bento --help
```

### 方式 3: 安装到系统（通过 pip）

**开发模式安装：**
```bash
cd /workspace/bento
pip install -e .

# 现在 bento 命令全局可用
bento init my-project
```

**优点：**
- ✅ 全局可用，无需指定路径
- ✅ 支持 `bento` 命令补全（需配置）
- ✅ 更符合 Python 包的使用习惯

**缺点：**
- 需要虚拟环境或系统 Python 权限
- 修改代码后需重新安装（开发模式除外）

## 验证安装

### 检查 bento 命令是否可用

```bash
# 方式 1: 检查是否在 PATH 中
which bento

# 方式 2: 直接运行
bento --help

# 方式 3: 检查版本（如果支持）
./bin/bento --version
```

### 测试基本功能

```bash
# 初始化项目
./bin/bento init test-project --output /tmp

# 检查生成的文件
ls -la /tmp/test-project/.vscode/
cat /tmp/test-project/Makefile

# 清理
rm -rf /tmp/test-project
```

## 常见问题

### Q: 为什么直接运行 `bento` 提示命令不存在？

**A:** 因为 `/workspace/bento/bin` 不在您的 `PATH` 环境变量中。

**解决方法：**
1. 使用相对路径：`./bin/bento`
2. 添加到 PATH：`export PATH="/workspace/bento/bin:$PATH"`
3. 安装到系统：`pip install -e .`

### Q: 每次重启终端都要重新 export PATH？

**A:** 是的，除非您将其添加到 shell 配置文件（`~/.bashrc` 或 `~/.zshrc`）。

```bash
# 永久添加
echo 'export PATH="/workspace/bento/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Q: bin/bento 是什么？

**A:** 这是一个 Bash 脚本，内容如下：

```bash
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BENTO_ROOT="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="${BENTO_ROOT}/src"

python3 -m bento.toolkit.cli "$@"
```

它会：
1. 设置正确的 `PYTHONPATH`
2. 调用 Python 模块 `bento.toolkit.cli`

### Q: 我可以创建别名吗？

**A:** 当然可以！

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
alias bento='/workspace/bento/bin/bento'

# 重新加载配置
source ~/.bashrc

# 现在可以直接使用
bento init my-project
```

## 开发工作流推荐

### 开发 Bento 框架本身

```bash
# 1. 不安装，使用相对路径
cd /workspace/bento
./bin/bento gen module Product --context catalog

# 2. 或者添加到 PATH（临时）
export PATH="/workspace/bento/bin:$PATH"
bento gen module Product --context catalog
```

### 使用 Bento 开发应用

```bash
# 1. 先安装 Bento（推荐开发模式）
cd /workspace/bento
pip install -e ".[dev]"

# 2. 创建新项目
cd ~/projects
bento init my-shop
cd my-shop

# 3. 生成模块
bento gen module Product --context catalog --fields 'name:str,price:float'

# 4. 启动开发
make dev
```

## 环境变量说明

### PYTHONPATH

`bin/bento` 脚本会自动设置：
```bash
export PYTHONPATH="${BENTO_ROOT}/src"
```

这确保 Python 能找到 `bento.toolkit.cli` 模块。

### 手动运行

如果您想直接运行 Python 模块而不使用 `bin/bento`：

```bash
cd /workspace/bento
PYTHONPATH=./src python3 -m bento.toolkit.cli init my-project
```

## VS Code 集成

在 VS Code 中，您可以配置任务来使用 bento 命令：

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Bento: Generate Module",
      "type": "shell",
      "command": "${workspaceFolder}/bin/bento",
      "args": [
        "gen",
        "module",
        "${input:moduleName}",
        "--context",
        "${input:contextName}"
      ],
      "problemMatcher": []
    }
  ],
  "inputs": [
    {
      "id": "moduleName",
      "type": "promptString",
      "description": "Module name (e.g., Product)"
    },
    {
      "id": "contextName",
      "type": "promptString",
      "description": "Context name (e.g., catalog)"
    }
  ]
}
```

---

**最后更新**: 2025-11-17
