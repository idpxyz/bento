# 架构重构执行计划

## 🎯 目标

将 Ordering BC 的反腐败层调整为标准的六边形架构 + DDD 结构。

---

## 📋 重构步骤

### 步骤 1: 移动 Port 到 domain 层

#### 1.1 创建正确的目录结构

```bash
# 创建目录
mkdir -p contexts/ordering/domain/ports/services
mkdir -p contexts/ordering/domain/vo
mkdir -p contexts/ordering/infrastructure/adapters/services
```

#### 1.2 移动和重命名文件

**移动 Port:**
```bash
# 从
contexts/ordering/application/ports/product_catalog_service.py
# 移动到
contexts/ordering/domain/ports/services/i_product_catalog_service.py
```

**移动值对象:**
```bash
# 从
contexts/ordering/domain/product_info.py
# 移动到
contexts/ordering/domain/vo/product_info.py
```

**移动 Adapter:**
```bash
# 从
contexts/ordering/infrastructure/services/product_catalog_service.py
# 移动到
contexts/ordering/infrastructure/adapters/services/product_catalog_adapter.py
```

---

### 步骤 2: 更新文件内容

#### 2.1 更新 i_product_catalog_service.py

```python
"""IProductCatalogService - 反腐败层接口（Secondary Port）

这是 Ordering Context 访问 Catalog Context 的契约定义。
符合六边形架构原则：Domain 层定义接口，Infrastructure 层实现。
"""

from abc import ABC, abstractmethod

from contexts.ordering.domain.vo.product_info import ProductInfo  # ✅ 更新导入


class IProductCatalogService(ABC):
    """产品目录服务接口（Secondary Port - 被驱动端口）

    职责：
    1. 定义 Ordering BC 需要的产品查询契约
    2. 隔离两个 BC 的变化
    3. 支持依赖倒置（Domain 不依赖 Infrastructure）

    实现方式由 Adapter 决定：
    - ProductCatalogAdapter: 查询本地只读副本
    - ProductCatalogHttpAdapter: HTTP 调用
    - ProductCatalogEventAdapter: 事件驱动同步
    """

    @abstractmethod
    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        """获取产品信息"""
        pass

    @abstractmethod
    async def get_products_info(self, product_ids: list[str]) -> dict[str, ProductInfo]:
        """批量获取产品信息"""
        pass

    @abstractmethod
    async def check_products_available(
        self, product_ids: list[str]
    ) -> tuple[list[str], list[str]]:
        """检查产品是否可用"""
        pass
```

#### 2.2 更新 product_catalog_adapter.py

```python
"""ProductCatalogAdapter - 反腐败层实现（Secondary Adapter）

实现方式：直接查询 Catalog BC 的数据库表（适合 Modular Monolith）

说明：
1. 在 Modular Monolith 中，不同 BC 可以共享数据库，但应该：
   - 只读访问其他 BC 的表（不修改）
   - 通过 Adapter 隔离，而不是直接依赖领域模型

2. 未来迁移到微服务时，只需替换这个 Adapter 为 HTTP 客户端，
   Ordering BC 的其他代码无需修改（开闭原则）
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)
from contexts.ordering.domain.vo.product_info import ProductInfo


class ProductCatalogAdapter(IProductCatalogService):
    """产品目录适配器（Secondary Adapter - 被驱动适配器）

    职责：
    1. 实现 IProductCatalogService 接口
    2. 查询 Catalog BC 的只读视图
    3. 转换 ProductPO → ProductInfo（反腐败转换）
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        """获取产品信息"""
        stmt = select(ProductPO).where(
            ProductPO.id == product_id,
            ProductPO.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        product_po = result.scalar_one_or_none()

        if not product_po:
            return None

        return self._to_product_info(product_po)

    async def get_products_info(self, product_ids: list[str]) -> dict[str, ProductInfo]:
        """批量获取产品信息"""
        if not product_ids:
            return {}

        stmt = select(ProductPO).where(
            ProductPO.id.in_(product_ids),
            ProductPO.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        products = result.scalars().all()

        return {product.id: self._to_product_info(product) for product in products}

    async def check_products_available(
        self, product_ids: list[str]
    ) -> tuple[list[str], list[str]]:
        """检查产品是否可用"""
        products_info = await self.get_products_info(product_ids)

        available = []
        unavailable = []

        for product_id in product_ids:
            product_info = products_info.get(product_id)
            if product_info and product_info.is_available:
                available.append(product_id)
            else:
                unavailable.append(product_id)

        return available, unavailable

    def _to_product_info(self, product_po: ProductPO) -> ProductInfo:
        """反腐败转换：ProductPO → ProductInfo

        这是关键的隔离点：
        - 输入：Catalog BC 的 ProductPO（持久化对象）
        - 输出：Ordering BC 的 ProductInfo（值对象）

        如果 Catalog BC 的 Product 模型发生变化，只需修改这里，
        Ordering BC 的其他代码不受影响。
        """
        return ProductInfo(
            product_id=product_po.id,
            product_name=product_po.name,
            unit_price=float(product_po.price),
            is_available=not product_po.is_deleted
        )
```

---

### 步骤 3: 更新导入路径

#### 3.1 更新 create_order.py

```python
# 从
from contexts.ordering.application.ports.product_catalog_service import IProductCatalogService

# 改为
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)
```

#### 3.2 更新 order_api.py

```python
# 从
from contexts.ordering.infrastructure.services.product_catalog_service import (
    ProductCatalogService,
)

# 改为
from contexts.ordering.infrastructure.adapters.services.product_catalog_adapter import (
    ProductCatalogAdapter,
)

# 并更新实例化
product_catalog = ProductCatalogAdapter(uow.session)
```

#### 3.3 更新测试文件

```python
# test_create_order.py
# 更新导入
from contexts.ordering.domain.vo.product_info import ProductInfo
```

---

### 步骤 4: 清理旧文件

```bash
# 删除旧目录（如果为空）
rm -rf contexts/ordering/application/ports/
rm -rf contexts/ordering/infrastructure/services/
```

---

### 步骤 5: 更新 __init__.py

#### contexts/ordering/domain/ports/__init__.py

```python
"""Domain ports (interfaces) for Ordering context.

Ports define the contracts that adapters must implement.
Following Hexagonal Architecture principles.
"""

from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)

__all__ = [
    "IProductCatalogService",
]
```

#### contexts/ordering/domain/vo/__init__.py

```python
"""Value objects for Ordering context."""

from contexts.ordering.domain.vo.product_info import ProductInfo

__all__ = [
    "ProductInfo",
]
```

#### contexts/ordering/infrastructure/adapters/__init__.py

```python
"""Infrastructure adapters for Ordering context."""

from contexts.ordering.infrastructure.adapters.services.product_catalog_adapter import (
    ProductCatalogAdapter,
)

__all__ = [
    "ProductCatalogAdapter",
]
```

---

## 🧪 验证步骤

### 1. 运行测试

```bash
# 单元测试
pytest tests/ordering/unit/application/test_create_order.py -v

# 集成测试
pytest tests/ordering/integration/ -v

# 端到端测试
uv run scenario_complete_shopping_flow.py
```

### 2. 检查导入

```bash
# 检查是否有遗漏的旧导入
grep -r "application.ports.product_catalog" contexts/
grep -r "infrastructure.services.product_catalog" contexts/
```

### 3. 验证目录结构

```bash
tree contexts/ordering/ -L 3
```

期望输出：
```
contexts/ordering/
├── domain/
│   ├── order.py
│   ├── order_item.py
│   ├── events/
│   ├── vo/
│   │   └── product_info.py       ✅
│   └── ports/
│       └── services/
│           └── i_product_catalog_service.py  ✅
├── application/
│   └── commands/
│       └── create_order.py
└── infrastructure/
    ├── persistence/ (或 models/, mappers/, repositories/)
    └── adapters/                  ✅
        └── services/
            └── product_catalog_adapter.py  ✅
```

---

## 📚 更新文档

### 1. 更新 BC_ISOLATION_GUIDE.md

添加章节说明六边形架构和目录结构。

### 2. 更新 MIGRATION_NOTES.md

添加新的导入路径示例。

### 3. 创建 HEXAGONAL_ARCHITECTURE.md

详细说明 Ports and Adapters 模式。

---

## ✅ 完成标志

- [ ] 所有文件已移动到正确位置
- [ ] 所有导入路径已更新
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 旧文件已清理
- [ ] 目录结构符合六边形架构
- [ ] 命名规范统一（IXxx, XxxAdapter）

---

## 🎯 最终效果

### 清晰的依赖方向

```
infrastructure/adapters/
    ProductCatalogAdapter
            ↓ implements
domain/ports/services/
    IProductCatalogService
            ↑ depends on
application/commands/
    CreateOrderUseCase
```

### 符合六边形架构

```
    External System (Catalog BC)
            ↓
    ┌───────────────────────┐
    │ ProductCatalogAdapter │ ← Secondary Adapter
    └───────────────────────┘
            ↓ implements
    ┌───────────────────────────┐
    │ IProductCatalogService    │ ← Secondary Port
    └───────────────────────────┘
            ↑ uses
    ┌───────────────────────┐
    │ CreateOrderUseCase    │ ← Application Core
    └───────────────────────┘
            ↑ invokes
    ┌───────────────────────┐
    │ OrderController       │ ← Primary Adapter
    └───────────────────────┘
            ↑
    External World (API Client)
```

---

## 💡 扩展性示例

未来如果要改为 HTTP 调用，只需：

```python
# 新增 infrastructure/adapters/services/product_catalog_http_adapter.py

class ProductCatalogHttpAdapter(IProductCatalogService):
    """HTTP 客户端实现（微服务场景）"""

    def __init__(self, http_client: HttpClient, base_url: str):
        self._client = http_client
        self._base_url = base_url

    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        response = await self._client.get(
            f"{self._base_url}/products/{product_id}"
        )
        return ProductInfo(**response.json())
```

**关键：** CreateOrderUseCase 无需修改！只需在依赖注入时替换 Adapter。
