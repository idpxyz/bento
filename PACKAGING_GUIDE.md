# Bento Framework 打包和发布指南

## ✅ 打包成功！

Bento Framework 已经可以打包并安装，无需源代码！

---

## 📦 打包方式

### 1. 使用 build 工具（推荐）

```bash
cd /workspace/bento

# 安装打包工具
uv pip install build

# 清理旧文件
rm -rf dist build

# 打包
python -m build
```

### 生成的文件

```
dist/
├── bento_framework-0.1.0a2-py3-none-any.whl  # Wheel 包（推荐）
└── bento_framework-0.1.0a2.tar.gz            # 源代码包
```

---

## 🚀 安装方式

### 方式 1: 从本地 wheel 安装

```bash
# 创建新环境
python3 -m venv myenv
source myenv/bin/activate

# 安装
pip install /path/to/bento_framework-0.1.0a2-py3-none-any.whl

# 验证
python -m bento.toolkit.cli --help
```

### 方式 2: 从 PyPI 安装（未来）

```bash
# 发布到 PyPI 后
pip install bento-framework

# 使用
python -m bento.toolkit.cli --help
```

### 方式 3: 开发模式（源代码）

```bash
# 克隆源码
git clone https://github.com/your-org/bento.git
cd bento

# 安装（可编辑模式）
pip install -e ".[dev]"

# 使用
python -m bento.toolkit.cli --help
```

---

## 💻 使用方法

### CLI 命令

安装后可以直接使用 `bento` 命令：

```bash
# ✅ 方式 1: 直接使用 bento 命令（推荐）
bento init my-project
bento gen module Product --context catalog

# 方式 2: 使用 python -m
python -m bento.toolkit.cli init my-project
python -m bento.toolkit.cli gen module Product --context catalog

# 方式 3: 使用源码目录的 bin/bento（开发时）
/path/to/bento/bin/bento init my-project
```

---

## 📋 完整示例

### 安装并创建项目

```bash
# 1. 创建新环境
cd ~/projects
python3 -m venv bento-env
source bento-env/bin/activate

# 2. 安装 Bento Framework
pip install /path/to/bento_framework-0.1.0a2-py3-none-any.whl

# 3. 初始化项目（bento 命令已自动安装）
bento init my-shop --description "E-commerce platform"

cd my-shop

# 5. 生成模块
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float,stock:int"

# 6. 安装项目依赖
pip install -e ".[dev]"

# 7. 运行测试
python -m pytest -v

# 8. 启动应用
uvicorn main:app --reload
```

---

## 📤 发布到 PyPI

### 准备工作

```bash
# 安装发布工具
pip install twine

# 检查包
twine check dist/*
```

### 发布到 TestPyPI（测试）

```bash
# 上传到 TestPyPI
twine upload --repository testpypi dist/*

# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ bento-framework
```

### 发布到 PyPI（正式）

```bash
# 上传到 PyPI
twine upload dist/*

# 安装
pip install bento-framework
```

---

## 📊 包含内容

打包后的 wheel 包含：

### ✅ 核心模块

- `bento.core` - 核心类型和接口
- `bento.domain` - 领域层
- `bento.application` - 应用层
- `bento.adapters` - 适配器层
- `bento.interfaces` - 接口层
- `bento.persistence` - 持久化
- `bento.security` - 安全模块

### ✅ CLI 工具

- `bento.toolkit.cli` - 代码生成器
- `bento.toolkit.templates/` - 所有模板文件
  - `aggregate.py.tpl`
  - `event.py.tpl`
  - `repository.py.tpl`
  - `usecase.py.tpl`
  - `test_*.tpl`
  - `project/**/*.tpl`

### ✅ 依赖项

自动安装：
- FastAPI
- SQLAlchemy
- Pydantic
- Jinja2
- 等...

---

## 🔍 验证安装

### 检查包信息

```bash
pip show bento-framework
```

### 检查 CLI 工具

```bash
python -m bento.toolkit.cli --help
```

### 检查模板文件

```python
import bento.toolkit.cli
import pathlib

# 获取模板目录
templates_dir = pathlib.Path(bento.toolkit.cli.__file__).parent / "templates"
print(f"Templates: {templates_dir}")
print(f"Exists: {templates_dir.exists()}")
print(f"Files: {list(templates_dir.glob('*.tpl'))}")
```

---

## ⚙️ pyproject.toml 配置说明

### 关键配置

```toml
[project]
name = "bento-framework"
version = "0.1.0a2"

[project.scripts]
bento = "bento.toolkit.cli:main"  # 命令行入口

[tool.setuptools.package-data]
"bento.toolkit" = ["templates/**/*", "templates/**/**/*"]  # 包含模板
```

---

## 🎯 开发者工作流

### 对于 Framework 开发者

```bash
# 克隆源码
git clone https://github.com/your-org/bento.git
cd bento

# 安装开发依赖
pip install -e ".[dev]"

# 修改代码
vim src/bento/toolkit/cli.py

# 打包
python -m build

# 测试安装
pip install dist/bento_framework-*.whl

# 发布
twine upload dist/*
```

### 对于应用开发者

```bash
# 安装 Bento Framework
pip install bento-framework

# 创建项目
python -m bento.toolkit.cli init my-app

# 开发
cd my-app
pip install -e ".[dev]"
python -m pytest
uvicorn main:app --reload
```

---

## 🐛 已知问题

### Issue 1: console_scripts 未生成（✅ 已修复）

**现象**: 安装后没有 `bento` 命令

**解决**: 已修复 `main()` 函数的返回值，现在可以正确生成 `bento` 命令

### Issue 2: 模板文件缺失（✅ 已修复）

**现象**: 生成代码时找不到模板

**原因**: package-data 配置缺失

**解决**: 已在 pyproject.toml 中添加
```toml
[tool.setuptools.package-data]
"bento.toolkit" = ["templates/**/*", "templates/**/**/*"]
```

---

## 📈 版本发布流程

### 1. 更新版本号

编辑 `pyproject.toml`:
```toml
version = "0.1.0a3"  # 或 0.1.0, 0.2.0 等
```

### 2. 更新 CHANGELOG

记录变更内容

### 3. 打包

```bash
rm -rf dist build
python -m build
```

### 4. 测试

```bash
# 本地测试
pip install dist/bento_framework-*.whl

# TestPyPI 测试
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ bento-framework
```

### 5. 发布

```bash
twine upload dist/*
```

### 6. 标记版本

```bash
git tag v0.1.0a3
git push origin v0.1.0a3
```

---

## 🎊 总结

### ✅ 已实现

- [x] 完整打包配置
- [x] 包含所有模板文件
- [x] CLI 工具可用
- [x] 依赖自动安装
- [x] 开发模式支持
- [x] `bento` 命令自动安装 ⭐

### 🚧 待优化

- [ ] 发布到 PyPI
- [ ] CI/CD 自动打包
- [ ] 文档网站
- [ ] 单元测试覆盖

### 📖 推荐用法

**目前最佳实践**:

```bash
# 安装
pip install /path/to/bento_framework-*.whl

# 使用（bento 命令已自动安装）
bento init my-app
cd my-app
bento gen module Product --context catalog

# 运行测试
pytest -v

# 启动应用
uvicorn main:app --reload
```

---

**Bento Framework 现在可以打包发布了！** 🎉

**打包文件**: `/workspace/bento/dist/bento_framework-0.1.0a2-py3-none-any.whl`
**大小**: 165KB
**状态**: ✅ 可用
