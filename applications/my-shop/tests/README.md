# my-shop 测试

本目录包含 my-shop 应用的所有测试。

---

## 🧪 测试结构

```
tests/
├── unit/                    # 单元测试
│   ├── catalog/            # Catalog BC 单元测试
│   ├── identity/           # Identity BC 单元测试
│   └── ordering/           # Ordering BC 单元测试
│
├── integration/            # 集成测试
│   ├── api/               # API 集成测试
│   ├── database/          # 数据库集成测试
│   └── outbox/            # Outbox 集成测试
│
├── e2e/                   # 端到端测试
│   └── *.py              # 完整流程测试
│
└── conftest.py           # Pytest 配置和 fixtures
```

---

## 🚀 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定层次的测试
```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 端到端测试
pytest tests/e2e/
```

### 运行特定 BC 的测试
```bash
# Ordering BC 测试
pytest tests/ordering/

# Catalog BC 测试
pytest tests/catalog/

# Identity BC 测试
pytest tests/identity/
```

### 运行特定文件
```bash
pytest tests/ordering/unit/application/test_create_order.py -v
```

### 带覆盖率报告
```bash
pytest --cov=contexts --cov-report=html
```

---

## 📜 测试脚本

测试相关的 shell 脚本位于 `../scripts/test/` 目录：

```bash
# 幂等性测试
bash scripts/test/test_idempotency.sh

# 中间件测试
bash scripts/test/test_middleware.sh

# 订单流程测试
bash scripts/test/test_order_flow.sh
```

---

## 🎯 测试分层说明

### 单元测试（Unit Tests）
- **目的**: 测试单个组件的功能
- **范围**: Handler, Service, Domain Model
- **特点**: 快速、隔离、使用 Mock
- **示例**: `test_create_order.py`

### 集成测试（Integration Tests）
- **目的**: 测试组件之间的交互
- **范围**: API, Database, Outbox
- **特点**: 使用真实依赖、较慢
- **示例**: `test_auth_endpoints.py`

### 端到端测试（E2E Tests）
- **目的**: 测试完整的业务流程
- **范围**: 从 HTTP 请求到数据库持久化
- **特点**: 最接近真实场景、最慢
- **示例**: `test_outbox_end_to_end.py`

---

## 🔧 Pytest 配置

配置文件: `../pyproject.toml`

主要配置:
- 测试路径: `tests/`
- 异步支持: `pytest-asyncio`
- 覆盖率: `pytest-cov`

---

## 📊 测试覆盖率

查看测试覆盖率报告:
```bash
pytest --cov=contexts --cov-report=html
open htmlcov/index.html
```

---

## 🎓 最佳实践

### 1. 测试命名
- 文件: `test_*.py`
- 类: `Test*`
- 函数: `test_*`

### 2. 测试组织
- 按 BC 组织单元测试
- 按功能组织集成测试
- 按场景组织 E2E 测试

### 3. Fixtures 使用
- 共享 fixtures 在 `conftest.py`
- BC 特定 fixtures 在 BC 目录的 `conftest.py`

### 4. 异步测试
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

---

## 🐛 调试测试

### 运行单个测试
```bash
pytest tests/path/to/test.py::test_function_name -v
```

### 显示 print 输出
```bash
pytest -s
```

### 进入调试模式
```bash
pytest --pdb
```

---

## 📝 编写新测试

1. 确定测试类型（单元/集成/E2E）
2. 在对应目录创建测试文件
3. 使用适当的 fixtures
4. 遵循命名约定
5. 添加清晰的文档字符串

---

**最后更新**: 2024-12-30
