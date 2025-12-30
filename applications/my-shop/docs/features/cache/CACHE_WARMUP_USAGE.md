# 缓存预热使用指南（生产级实现）

## 📋 **概述**

这是基于DDD和六边形架构的生产级缓存预热实现，完全符合my-shop的架构标准。

---

## 🏗️ **架构设计**

### 目录结构

```
my-shop/
├── contexts/                    # 限界上下文
│   ├── catalog/
│   │   └── application/
│   │       └── warmup/         # ✅ Catalog BC的预热策略
│   │           ├── product_warmup_service.py
│   │           └── category_warmup_service.py
│   │
│   ├── identity/               # TODO: Identity BC预热策略
│   └── ordering/               # TODO: Ordering BC预热策略
│
├── shared/                      # 共享内核
│   └── infrastructure/
│       └── cache/
│           └── warmup/         # ✅ 跨BC的协调器
│               └── coordinator.py
│
├── config/
│   └── warmup_config.py        # ✅ 预热配置（组装）
│
└── warmup/                      # ⚠️ 保留作为示例参考
    └── (示例代码，不用于生产)
```

---

## 🎯 **已实现功能**

### ✅ Catalog BC 预热策略（2个）

**1. HotProductsWarmupStrategy**
- 优先级：100（最高）
- TTL：2小时
- 职责：预热最常访问的商品（前100个）
- 数据源：`IProductRepository.list()`

**2. CategoryWarmupStrategy**
- 优先级：50（中等）
- TTL：4小时
- 职责：预热所有分类+分类列表页
- 数据源：`ICategoryRepository.list()`

### ✅ 共享协调器

**CacheWarmupCoordinator**
- 位置：`shared/infrastructure/cache/warmup/`
- 职责：协调多个BC的预热策略
- 功能：
  - 注册策略
  - 按优先级执行
  - 按BC过滤预热
  - 统计收集

---

## 💻 **使用方式**

### 方式1：应用启动时预热（推荐）

```python
# main.py 或 app.py
from fastapi import FastAPI
from bento.adapters.cache import CacheFactory, CacheConfig, CacheBackend

from config.warmup_config import setup_cache_warmup
from contexts.catalog.infrastructure.repositories import (
    ProductRepository,
    CategoryRepository,
)

app = FastAPI()

@app.on_event("startup")
async def startup():
    # 1. 创建缓存
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.REDIS)
    )

    # 2. 创建Repository（实际应用中从DI容器获取）
    # 这里简化演示
    session = get_session()
    product_repo = ProductRepository(session)
    category_repo = CategoryRepository(session)

    # 3. 设置预热（自动执行）
    coordinator = await setup_cache_warmup(
        cache,
        product_repository=product_repo,
        category_repository=category_repo,
        warmup_on_startup=True,  # 启动时立即预热
        max_concurrency=20,
    )

    # 4. 保存coordinator供后续使用
    app.state.warmup_coordinator = coordinator
    app.state.cache = cache
```

### 方式2：按BC预热

```python
# 只预热 Catalog BC
from config.warmup_config import warmup_catalog_only

results = await warmup_catalog_only(
    cache,
    product_repository,
    category_repository,
)
```

### 方式3：通过协调器手动触发

```python
# 全量预热
coordinator = app.state.warmup_coordinator
results = await coordinator.warmup_all()

# 按BC预热
results = await coordinator.warmup_by_bc("catalog")
```

---

## 📊 **预期输出**

```
🔧 开始配置缓存预热系统...
📦 注册 Catalog BC 预热策略...
INFO: 注册预热策略: HotProductsWarmupStrategy (BC: catalog, Priority: 100)
INFO: 注册预热策略: CategoryWarmupStrategy (BC: catalog, Priority: 50)
✅ 已注册 2 个预热策略:
   - HotProductsWarmupStrategy (BC: catalog, Priority: 100)
   - CategoryWarmupStrategy (BC: catalog, Priority: 50)

🚀 执行启动时预热...
======================================================================
🔥 开始执行缓存预热，共 2 个策略
======================================================================
INFO: Catalog BC - 准备预热 100 个商品
INFO: Starting cache warmup: 100 keys (strategy: HotProductsWarmupStrategy)
INFO: Cache warmup completed: 100 warmed, 0 skipped, 0 failed in 2.34s

INFO: Catalog BC - 准备预热 21 个分类
INFO: Starting cache warmup: 21 keys (strategy: CategoryWarmupStrategy)
INFO: Cache warmup completed: 21 warmed, 0 skipped, 0 failed in 0.45s

✨ 缓存预热完成！
----------------------------------------------------------------------
  🎯 总计: 121/121 个键已预热
  ⏱️  总耗时: 2.79s
  🏆 总成功率: 100.0%
======================================================================
✅ 缓存预热系统配置完成
```

---

## 🔧 **扩展指南**

### 添加新的预热策略

**Step 1: 在对应BC中创建策略**

```python
# contexts/ordering/application/warmup/order_warmup_service.py

class RecentOrdersWarmupStrategy:
    """预热最近订单"""

    def __init__(self, order_repository):
        self._order_repo = order_repository

    async def get_keys_to_warmup(self) -> list[str]:
        recent_orders = await self._order_repo.list(limit=50)
        return [f"Order:id:{o.id}" for o in recent_orders]

    async def load_data(self, key: str):
        order_id = key.split(":")[-1]
        return await self._order_repo.get(order_id)

    def get_priority(self) -> int:
        return 30

    def get_ttl(self) -> int:
        return 1800  # 30分钟
```

**Step 2: 在配置中注册**

```python
# config/warmup_config.py

from contexts.ordering.application.warmup import RecentOrdersWarmupStrategy

async def setup_cache_warmup(
    cache,
    product_repository,
    category_repository,
    order_repository,  # 新增参数
    ...
):
    coordinator = CacheWarmupCoordinator(cache)

    # ... 注册其他策略 ...

    # 注册 Ordering BC 策略
    coordinator.register_strategy(
        RecentOrdersWarmupStrategy(order_repository),
        bc_name="ordering",
        description="预热最近50个订单",
    )

    return coordinator
```

---

## ✅ **符合架构原则**

### DDD分层原则

- ✅ **Domain Layer**: 没有预热逻辑（保持纯净）
- ✅ **Application Layer**: 预热策略在这里（各BC的`application/warmup/`）
- ✅ **Infrastructure Layer**: 协调器在这里（`shared/infrastructure/cache/warmup/`）
- ✅ **Interfaces Layer**: TODO（管理API）

### 限界上下文隔离

- ✅ **Catalog BC**: 只负责Catalog相关的预热
- ✅ **Identity BC**: TODO（未来添加用户相关预热）
- ✅ **Ordering BC**: TODO（未来添加订单相关预热）
- ✅ **共享内核**: 只有技术协调，没有业务逻辑

### 六边形架构

- ✅ **Port**: 框架的`CacheWarmupStrategy`协议
- ✅ **Adapter**: 各BC的预热策略实现
- ✅ **依赖方向**: 正确（外层依赖内层）

---

## 📚 **相关文档**

- `docs/WARMUP_ARCHITECTURE_ANALYSIS.md` - 架构分析和设计
- `warmup/README.md` - 示例代码参考（不用于生产）
- `docs/infrastructure/cache/CACHE_WARMUP_DESIGN.md` - 框架层设计

---

## 🎯 **下一步计划**

- [ ] 实现 Identity BC 的预热策略
- [ ] 实现 Ordering BC 的预热策略
- [ ] 添加定时任务支持
- [ ] 添加管理API（Interfaces层）
- [ ] 添加监控指标收集

---

## 🎓 **总结**

### 当前实现

- ✅ 符合DDD分层原则
- ✅ 符合BC隔离原则
- ✅ 符合六边形架构
- ✅ 使用真实的Repository
- ✅ 无Mock数据
- ✅ 生产就绪

### 示例代码

- ⚠️ `warmup/` 目录保留作为学习参考
- ⚠️ 不应在生产环境使用
- ⚠️ 是演示框架功能的完整示例

**现在可以安全地在生产环境中使用缓存预热功能！** 🎉
