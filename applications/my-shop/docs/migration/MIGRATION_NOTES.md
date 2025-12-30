# BC 隔离重构迁移说明

## 📝 变更概述

为了遵守 DDD 的 Bounded Context 隔离原则，我们重构了 `CreateOrderUseCase`，移除了对 `catalog.Product` 的直接依赖。

### 变更前（❌ 违反 BC 隔离）

```python
from contexts.catalog.domain.product import Product  # ❌ 跨 BC 依赖

class CreateOrderUseCase:
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    async def handle(self, command):
        product_repo = self.uow.repository(Product)  # ❌ 直接访问 Catalog BC
        product = await product_repo.get(product_id)
```

### 变更后（✅ 符合 BC 隔离）

```python
from contexts.ordering.application.ports.product_catalog_service import IProductCatalogService

class CreateOrderUseCase:
    def __init__(
        self,
        uow: IUnitOfWork,
        product_catalog: IProductCatalogService  # ✅ 通过反腐败层
    ):
        super().__init__(uow)
        self._product_catalog = product_catalog

    async def handle(self, command):
        _, unavailable = await self._product_catalog.check_products_available(
            [item.product_id for item in command.items]
        )
```

---

## 🔧 如何更新现有代码

### 1. API 端点（已更新）

**文件：** `contexts/ordering/interfaces/order_api.py`

```python
async def get_create_order_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> CreateOrderUseCase:
    from contexts.ordering.infrastructure.services.product_catalog_service import (
        ProductCatalogService,
    )

    product_catalog = ProductCatalogService(uow.session)
    return CreateOrderUseCase(uow, product_catalog)  # ✅ 已更新
```

### 2. 单元测试（已更新）

**文件：** `tests/ordering/unit/application/test_create_order.py`

```python
@pytest.fixture
def mock_product_catalog():
    """Mock 产品目录服务"""
    return AsyncMock()

@pytest.fixture
def usecase(mock_uow, mock_product_catalog):
    return CreateOrderUseCase(
        uow=mock_uow,
        product_catalog=mock_product_catalog,  # ✅ 已更新
    )
```

### 3. 手动测试脚本（需要手动更新）

以下文件需要更新，添加 `product_catalog` 参数：

#### 文件：`manual_test_outbox.py`

```python
# 更新前
use_case = CreateOrderUseCase(uow)  # ❌

# 更新后
from contexts.ordering.infrastructure.services.product_catalog_service import (
    ProductCatalogService,
)

product_catalog = ProductCatalogService(session)
use_case = CreateOrderUseCase(uow, product_catalog)  # ✅
```

#### 文件：`scenario_complete_shopping_flow.py`

```python
# 在创建 use_case 之前添加
from contexts.ordering.infrastructure.services.product_catalog_service import (
    ProductCatalogService,
)

product_catalog = ProductCatalogService(session)
use_case = CreateOrderUseCase(uow, product_catalog)
```

#### 文件：`demo_event_handlers.py`

```python
# 同上
product_catalog = ProductCatalogService(session)
use_case = CreateOrderUseCase(uow, product_catalog)
```

#### 文件：`test_outbox_end_to_end.py`

```python
# 同上
product_catalog = ProductCatalogService(session)
use_case = CreateOrderUseCase(uow, product_catalog)
```

#### 文件：`tests/e2e_outbox_test.py`

```python
# 同上
product_catalog = ProductCatalogService(session)
use_case = CreateOrderUseCase(uow, product_catalog)
```

---

## 🎯 快速修复模板

如果你在任何地方看到以下错误：

```
TypeError: __init__() missing 1 required positional argument: 'product_catalog'
```

使用以下模板修复：

```python
# 1. 添加导入
from contexts.ordering.infrastructure.services.product_catalog_service import (
    ProductCatalogService,
)

# 2. 创建服务实例（在创建 use_case 之前）
product_catalog = ProductCatalogService(session)  # 或 uow.session

# 3. 更新 use_case 创建
use_case = CreateOrderUseCase(uow, product_catalog)
```

---

## 📦 新增文件清单

本次重构新增了以下文件：

### 领域层
- `contexts/ordering/domain/product_info.py` - ProductInfo 值对象

### 应用层
- `contexts/ordering/application/ports/__init__.py`
- `contexts/ordering/application/ports/product_catalog_service.py` - 反腐败层接口

### 基础设施层
- `contexts/ordering/infrastructure/services/__init__.py`
- `contexts/ordering/infrastructure/services/product_catalog_service.py` - 反腐败层实现

### 文档
- `docs/BC_ISOLATION_GUIDE.md` - BC 隔离完整指南
- `docs/MIGRATION_NOTES.md` - 本文件

---

## ✅ 验证清单

重构后，确保以下测试通过：

```bash
# 1. 单元测试
pytest tests/ordering/unit/application/test_create_order.py -v

# 2. 集成测试
pytest tests/ordering/integration/ -v

# 3. 端到端测试
pytest tests/e2e/ -k order -v
```

---

## 🎓 学习资源

- 阅读 `docs/BC_ISOLATION_GUIDE.md` 了解完整的架构原理
- 参考 `contexts/ordering/application/commands/create_order.py` 查看重构后的代码
- 查看 `tests/ordering/unit/application/test_create_order.py` 了解如何测试

---

## 💡 未来改进

当前实现使用直接查询数据库的方式（适合 Modular Monolith）。

未来可以考虑：

1. **集成事件同步**：通过监听 `ProductCreated` 等事件同步产品信息副本
2. **HTTP 调用**：迁移到微服务时，将 `ProductCatalogService` 改为 HTTP 客户端
3. **缓存层**：在 `ProductCatalogService` 中添加缓存以提高性能

这些改进只需修改 `ProductCatalogService` 实现，不影响 `CreateOrderUseCase` 的代码。
