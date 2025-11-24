# Bento 项目测试指南

## 🎯 pytest 依赖说明

### ✅ 依赖已包含

Bento CLI 生成的项目**已经包含** pytest 及相关测试依赖：

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",          # 测试框架
    "pytest-asyncio>=0.24", # 异步测试支持
    "pytest-cov>=4.1",      # 覆盖率报告
    "httpx>=0.27",          # HTTP 测试客户端
    "ruff>=0.6",            # 代码检查
    "mypy>=1.11",           # 类型检查
]
```

---

## 🚀 运行测试的正确方法

### 方式 1: 使用 uv（推荐）

```bash
cd my-project

# 1. 安装项目及 dev 依赖
uv pip install -e ".[dev]"

# 2. 运行测试
uv run pytest -v

# 3. 带覆盖率
uv run pytest --cov

# 4. 生成 HTML 覆盖率报告
uv run pytest --cov --cov-report=html
```

### 方式 2: 使用虚拟环境

```bash
cd my-project

# 1. 创建虚拟环境（uv 自动创建）
uv venv

# 2. 安装依赖
uv pip install -e ".[dev]"

# 3. 激活环境
source .venv/bin/activate

# 4. 运行测试
pytest -v

# 或直接用 python
python -m pytest -v
```

### 方式 3: 不激活环境直接运行

```bash
cd my-project

# 安装依赖
uv pip install -e ".[dev]"

# 直接运行（推荐）
uv run python -m pytest -v
```

---

## ❌ 常见错误

### 错误 1: pytest 命令找不到

```bash
# ❌ 错误
uv run pytest -v

# 错误信息
error: Failed to spawn: `pytest`
  Caused by: No such file or directory (os error 2)
```

**原因**: 没有安装 dev 依赖

**解决**:
```bash
# 先安装 dev 依赖
uv pip install -e ".[dev]"

# 然后运行
uv run pytest -v
```

### 错误 2: 导入模块失败

```bash
# 错误信息
ModuleNotFoundError: No module named 'contexts'
```

**原因**:
1. pyproject.toml 的 `packages` 配置错误
2. pytest 配置的 `pythonpath` 不正确

**解决**: 确保 `pyproject.toml` 正确配置：

```toml
[tool.hatch.build.targets.wheel]
packages = ["contexts", "api"]  # ✅ Modular Monolith

[tool.pytest.ini_options]
pythonpath = ["."]  # ✅ 添加项目根目录到 Python 路径
testpaths = ["tests"]
```

---

## 📊 测试结果说明

### 正常的测试输出

```
============================= test session starts ==============================
collected 11 items

tests/catalog/unit/domain/test_product.py ✓✓✓✓              [ 36%]
tests/catalog/unit/application/test_create_product.py ✓✓✓   [ 63%]
tests/catalog/integration/test_product_repository.py ⏭️⏭️⏭️⏭️ [100%]

===================== 7 passed, 4 skipped in 1.78s ========================
```

### 预期的失败测试

```
FAILED test_create_valid_product - TypeError: missing required arguments
```

**说明**: 这是模板中的 TODO，开发者需要根据实际字段完善：

```python
# 需要从这样:
def test_create_valid_product(self):
    product = Product(
        id="test-id-123",
        # TODO: 添加其他字段
    )

# 改为这样:
def test_create_valid_product(self):
    product = Product(
        id="test-id-123",
        name="测试产品",
        price=99.0,
        stock=10
    )
```

### 跳过的集成测试

```
SKIPPED [4] tests/catalog/integration/: 需要实现数据库 fixture
```

**说明**: 集成测试需要配置数据库后才能运行。

---

## 🔧 pytest 配置详解

### pyproject.toml 配置

```toml
[tool.pytest.ini_options]
pythonpath = ["."]           # 添加当前目录到 Python 路径
testpaths = ["tests"]        # 测试目录
asyncio_mode = "auto"        # 自动检测异步测试

# 可选配置
markers = [
    "integration: 集成测试",
    "unit: 单元测试",
]
```

### pytest.ini 配置

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    -v                       # 详细输出
    --strict-markers         # 严格的 marker 检查
    --cov                    # 覆盖率
    --cov-report=term-missing # 显示未覆盖的行
```

---

## 📚 测试命令参考

### 基本命令

```bash
# 运行所有测试
uv run pytest

# 详细输出
uv run pytest -v

# 仅运行失败的测试
uv run pytest --lf

# 遇到失败立即停止
uv run pytest -x

# 显示本地变量
uv run pytest -l
```

### 按目录/文件运行

```bash
# 运行特定上下文的测试
uv run pytest tests/catalog/

# 运行特定文件
uv run pytest tests/catalog/unit/domain/test_product.py

# 运行特定测试
uv run pytest tests/catalog/unit/domain/test_product.py::TestProduct::test_create_valid_product
```

### 按标记运行

```bash
# 只运行单元测试
uv run pytest -m unit

# 只运行集成测试
uv run pytest -m integration

# 排除集成测试
uv run pytest -m "not integration"
```

### 覆盖率报告

```bash
# 基本覆盖率
uv run pytest --cov

# 显示未覆盖的行
uv run pytest --cov --cov-report=term-missing

# 生成 HTML 报告
uv run pytest --cov --cov-report=html
open htmlcov/index.html

# 指定覆盖率目录
uv run pytest --cov=contexts --cov=api
```

---

## 🎯 完整工作流示例

### 新项目初始化

```bash
# 1. 生成项目
bento init my-shop

cd my-shop

# 2. 生成模块
bento gen module Product --context catalog --fields "name:str,price:float"

# 3. 安装依赖（包含 pytest）
uv pip install -e ".[dev]"

# 4. 运行测试
uv run pytest -v

# 5. 查看覆盖率
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

### 日常开发

```bash
# 1. 修改代码
vim contexts/catalog/domain/product.py

# 2. 运行相关测试
uv run pytest tests/catalog/ -v

# 3. 修复失败的测试
vim tests/catalog/unit/domain/test_product.py

# 4. 再次运行
uv run pytest tests/catalog/ -v

# 5. 检查覆盖率
uv run pytest tests/catalog/ --cov=contexts.catalog
```

---

## 🐛 调试技巧

### 1. 使用 pdb 调试

```python
def test_something():
    import pdb; pdb.set_trace()  # 断点
    assert True
```

运行:
```bash
uv run pytest -s  # -s 禁用输出捕获
```

### 2. 打印调试信息

```python
def test_something(capsys):
    print("Debug info")
    assert True

    captured = capsys.readouterr()
    print(f"Captured: {captured.out}")
```

### 3. 查看失败原因

```bash
# 详细的回溯
uv run pytest --tb=long

# 简短的回溯
uv run pytest --tb=short

# 只显示一行
uv run pytest --tb=line

# 不显示回溯
uv run pytest --tb=no
```

---

## 📈 最佳实践

### 1. 测试组织

```
tests/
├── <context>/
│   ├── unit/
│   │   ├── domain/        # 聚合根测试
│   │   └── application/   # 用例测试
│   └── integration/       # 仓储测试
└── conftest.py            # 共享 fixtures
```

### 2. 测试命名

```python
# ✅ 好的命名
def test_product_price_must_be_positive():
    ...

def test_order_can_be_cancelled_when_pending():
    ...

# ❌ 不好的命名
def test1():
    ...

def test_product():
    ...
```

### 3. 使用 fixtures

```python
@pytest.fixture
def valid_product():
    return Product(
        id="p-001",
        name="测试产品",
        price=99.0,
        stock=10
    )

def test_product_creation(valid_product):
    assert valid_product.price == 99.0
```

### 4. 参数化测试

```python
@pytest.mark.parametrize("price,expected", [
    (-1, ValueError),
    (0, ValueError),
    (99.0, None),
])
def test_product_price_validation(price, expected):
    if expected:
        with pytest.raises(expected):
            Product(id="p-001", name="Test", price=price)
    else:
        product = Product(id="p-001", name="Test", price=price)
        assert product.price == price
```

---

## ✅ 检查清单

在提交代码前检查：

- [ ] 所有测试通过: `uv run pytest`
- [ ] 覆盖率 > 80%: `uv run pytest --cov`
- [ ] 没有类型错误: `uv run mypy contexts/`
- [ ] 代码格式正确: `uv run ruff format .`
- [ ] 代码检查通过: `uv run ruff check .`

---

**Bento CLI 生成的项目已包含完整的测试配置，开箱即用！** ✅
