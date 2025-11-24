# 缓存预热架构分析

## 🔍 **当前实现分析**

### 当前目录结构

```
applications/my-shop/
└── warmup/                           # ❌ 问题：直接放在应用根目录
    ├── __init__.py
    ├── strategies.py                 # 4个预热策略
    ├── setup.py                      # 启动集成
    ├── fastapi_integration.py        # API集成
    ├── scheduled_tasks.py            # 定时任务
    └── README.md
```

---

## ❌ **架构问题分析**

### 问题1：违反DDD分层原则

**当前问题：**
```
warmup/ 直接放在 applications/my-shop/ 根目录下
```

**违反的原则：**
- ❌ 没有按照 DDD 的 4 层结构（Domain, Application, Infrastructure, Interfaces）
- ❌ 混淆了不同层次的职责
- ❌ 不符合 my-shop 已有的标准结构

### 问题2：违反限界上下文（Bounded Context）原则

**当前问题：**
```python
# strategies.py 中混合了多个上下文的逻辑
class HotProductsWarmupStrategy:      # 属于 Catalog BC
class CategoryCacheWarmupStrategy:     # 属于 Catalog BC
class ActiveUserSessionWarmupStrategy: # 属于 Identity BC
```

**违反的原则：**
- ❌ 跨越了多个限界上下文边界
- ❌ 将不同上下文的业务逻辑混在一个文件中
- ❌ 破坏了上下文的独立性

### 问题3：违反六边形架构原则

**当前问题：**
```
- setup.py: 包含应用启动逻辑（应该在 Application Layer）
- fastapi_integration.py: 包含API逻辑（应该在 Interfaces Layer）
- strategies.py: 包含业务逻辑（应该在对应的BC中）
- scheduled_tasks.py: 包含基础设施逻辑（应该在 Infrastructure Layer）
```

**违反的原则：**
- ❌ 没有清晰的端口（Port）和适配器（Adapter）分离
- ❌ 业务逻辑和技术实现混在一起
- ❌ 依赖方向不清晰

---

## ✅ **正确的架构设计**

### 方案：按DDD分层和BC重构

```
my-shop/
├── contexts/                          # 限界上下文
│   ├── catalog/                      # 商品目录上下文
│   │   ├── domain/
│   │   ├── application/
│   │   │   └── warmup/               # ✅ 应用层：预热用例
│   │   │       ├── __init__.py
│   │   │       └── product_warmup_service.py
│   │   ├── infrastructure/
│   │   └── interfaces/
│   │
│   ├── ordering/                     # 订单上下文
│   │   └── application/
│   │       └── warmup/               # ✅ 订单相关预热
│   │           └── order_warmup_service.py
│   │
│   └── identity/                     # 身份上下文
│       └── application/
│           └── warmup/               # ✅ 用户相关预热
│               └── user_warmup_service.py
│
├── shared/                            # 共享内核
│   └── infrastructure/
│       └── cache/
│           └── warmup/               # ✅ 共享：预热协调器
│               ├── __init__.py
│               ├── coordinator.py    # 协调多个上下文的预热
│               └── scheduler.py      # 定时任务配置
│
├── config/                            # 应用配置
│   └── warmup_config.py              # ✅ 预热配置
│
└── interfaces/                        # 接口层
    └── api/
        └── admin/
            └── warmup_api.py         # ✅ 预热管理API
```

---

## 📐 **重构方案详解**

### 1. Catalog BC 中的预热策略

```python
# contexts/catalog/application/warmup/product_warmup_service.py
"""
商品目录上下文的预热服务
职责：定义商品相关的缓存预热策略
"""

from bento.application.ports.cache_warmup import CacheWarmupStrategy
from ..services import ProductService


class HotProductsWarmupStrategy:
    """预热热销商品（属于Catalog BC）"""

    def __init__(self, product_service: ProductService):
        self._product_service = product_service

    async def get_keys_to_warmup(self) -> list[str]:
        # 使用本上下文的服务
        hot_products = await self._product_service.get_hot_products(limit=100)
        return [f"Product:id:{p.id}" for p in hot_products]

    async def load_data(self, key: str):
        product_id = key.split(":")[-1]
        return await self._product_service.get_by_id(product_id)

    def get_priority(self) -> int:
        return 100

    def get_ttl(self) -> int:
        return 7200


class CategoryWarmupStrategy:
    """预热分类（属于Catalog BC）"""

    def __init__(self, category_service):
        self._category_service = category_service

    async def get_keys_to_warmup(self) -> list[str]:
        categories = await self._category_service.get_all_categories()
        return [f"Category:id:{c.id}" for c in categories]

    async def load_data(self, key: str):
        category_id = key.split(":")[-1]
        return await self._category_service.get_by_id(category_id)

    def get_priority(self) -> int:
        return 50

    def get_ttl(self) -> int:
        return 14400
```

### 2. Identity BC 中的预热策略

```python
# contexts/identity/application/warmup/user_warmup_service.py
"""
身份认证上下文的预热服务
职责：定义用户相关的缓存预热策略
"""

from bento.application.ports.cache_warmup import CacheWarmupStrategy
from ..services import UserService


class ActiveUserSessionWarmupStrategy:
    """预热活跃用户会话（属于Identity BC）"""

    def __init__(self, user_service: UserService):
        self._user_service = user_service

    async def get_keys_to_warmup(self) -> list[str]:
        active_users = await self._user_service.get_active_users(hours=1)
        return [f"User:session:{u.id}" for u in active_users]

    async def load_data(self, key: str):
        user_id = key.split(":")[-1]
        return await self._user_service.get_session(user_id)

    def get_priority(self) -> int:
        return 20

    def get_ttl(self) -> int:
        return 900
```

### 3. 共享基础设施：预热协调器

```python
# shared/infrastructure/cache/warmup/coordinator.py
"""
跨上下文的缓存预热协调器
职责：协调多个BC的预热策略
"""

import logging
from typing import Any

from bento.adapters.cache.warmer import CacheWarmer
from bento.application.ports.cache import Cache

logger = logging.getLogger(__name__)


class CacheWarmupCoordinator:
    """缓存预热协调器（基础设施层）"""

    def __init__(self, cache: Cache, max_concurrency: int = 20):
        self._warmer = CacheWarmer(
            cache,
            max_concurrency=max_concurrency,
            default_ttl=3600,
            enable_progress=True,
        )
        self._strategies = []

    def register_strategy(self, strategy: Any) -> None:
        """注册预热策略（从各个BC）"""
        self._strategies.append(strategy)

    async def warmup_all(self) -> dict:
        """执行所有已注册策略的预热"""
        logger.info(f"开始执行缓存预热，共 {len(self._strategies)} 个策略")

        results = await self._warmer.warmup_multiple(self._strategies)

        # 统计
        total_warmed = sum(s.warmed_keys for s in results.values())
        total_keys = sum(s.total_keys for s in results.values())

        logger.info(f"缓存预热完成: {total_warmed}/{total_keys} 个键")

        return results

    async def warmup_by_context(self, context_name: str) -> dict:
        """按上下文预热（例如只预热Catalog BC）"""
        # 根据策略类名或标记过滤
        context_strategies = [
            s for s in self._strategies
            if context_name.lower() in s.__class__.__module__.lower()
        ]

        return await self._warmer.warmup_multiple(context_strategies)
```

### 4. 应用配置：预热设置

```python
# config/warmup_config.py
"""
应用启动时的预热配置
职责：组装各个BC的预热策略
"""

from bento.application.ports.cache import Cache
from shared.infrastructure.cache.warmup import CacheWarmupCoordinator

# 导入各个BC的预热策略
from contexts.catalog.application.warmup import (
    HotProductsWarmupStrategy,
    CategoryWarmupStrategy,
)
from contexts.identity.application.warmup import (
    ActiveUserSessionWarmupStrategy,
)


async def setup_cache_warmup(
    cache: Cache,
    # 各BC的服务
    product_service,
    category_service,
    user_service,
) -> CacheWarmupCoordinator:
    """设置缓存预热（应用启动时调用）"""

    # 1. 创建协调器（共享基础设施）
    coordinator = CacheWarmupCoordinator(cache, max_concurrency=20)

    # 2. 注册 Catalog BC 的策略
    coordinator.register_strategy(
        HotProductsWarmupStrategy(product_service)
    )
    coordinator.register_strategy(
        CategoryWarmupStrategy(category_service)
    )

    # 3. 注册 Identity BC 的策略
    coordinator.register_strategy(
        ActiveUserSessionWarmupStrategy(user_service)
    )

    # 4. 执行启动时预热
    await coordinator.warmup_all()

    return coordinator
```

### 5. 接口层：API端点

```python
# interfaces/api/admin/warmup_api.py
"""
预热管理API（接口层）
职责：提供HTTP接口触发预热
"""

from fastapi import APIRouter, Depends
from shared.infrastructure.cache.warmup import CacheWarmupCoordinator

router = APIRouter(prefix="/admin/warmup", tags=["admin"])


def get_warmup_coordinator() -> CacheWarmupCoordinator:
    """依赖注入：获取预热协调器"""
    # 从应用状态获取
    from main import app
    return app.state.warmup_coordinator


@router.post("/{context_name}")
async def trigger_warmup(
    context_name: str,
    coordinator: CacheWarmupCoordinator = Depends(get_warmup_coordinator)
):
    """触发指定上下文的预热"""
    results = await coordinator.warmup_by_context(context_name)

    return {
        "success": True,
        "context": context_name,
        "results": {
            name: {
                "warmed": stats.warmed_keys,
                "total": stats.total_keys,
                "success_rate": stats.success_rate,
            }
            for name, stats in results.items()
        }
    }


@router.post("/all")
async def trigger_full_warmup(
    coordinator: CacheWarmupCoordinator = Depends(get_warmup_coordinator)
):
    """触发全量预热"""
    results = await coordinator.warmup_all()

    total_warmed = sum(s.warmed_keys for s in results.values())
    total_keys = sum(s.total_keys for s in results.values())

    return {
        "success": True,
        "total_warmed": total_warmed,
        "total_keys": total_keys,
        "success_rate": total_warmed / total_keys if total_keys > 0 else 0,
    }
```

### 6. 定时任务

```python
# shared/infrastructure/cache/warmup/scheduler.py
"""
预热定时任务（基础设施层）
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .coordinator import CacheWarmupCoordinator


def setup_warmup_scheduler(
    coordinator: CacheWarmupCoordinator
) -> AsyncIOScheduler:
    """设置预热定时任务"""

    scheduler = AsyncIOScheduler()

    # 夜间全量预热
    @scheduler.scheduled_job(CronTrigger(hour=2, minute=0))
    async def nightly_warmup():
        await coordinator.warmup_all()

    # Catalog BC 增量预热
    @scheduler.scheduled_job(CronTrigger(minute="*/30"))
    async def catalog_incremental():
        await coordinator.warmup_by_context("catalog")

    return scheduler
```

---

## 📊 **架构对比**

| 维度 | 当前实现 | 正确实现 | 改进 |
|------|---------|---------|------|
| **DDD分层** | ❌ 无分层 | ✅ 4层清晰 | 符合标准 |
| **BC隔离** | ❌ 混在一起 | ✅ 按BC分离 | 独立性强 |
| **依赖方向** | ❌ 不清晰 | ✅ 向内依赖 | 符合六边形 |
| **职责分离** | ❌ 混合 | ✅ 单一职责 | 易维护 |
| **可测试性** | 🟡 中等 | ✅ 高 | 单元测试友好 |
| **扩展性** | 🟡 中等 | ✅ 高 | 易添加新BC |

---

## 🎯 **重构路线图**

### Phase 1: 按BC拆分策略（优先）

1. 创建各BC的预热目录
2. 移动策略到对应BC
3. 确保依赖隔离

### Phase 2: 提取共享协调器

1. 创建 shared/infrastructure/cache/warmup/
2. 实现协调器
3. 移除根目录的warmup/

### Phase 3: 重构接口层

1. 移动API到 interfaces/api/admin/
2. 移动定时任务到基础设施层

### Phase 4: 更新配置和文档

1. 更新 config/warmup_config.py
2. 更新文档
3. 更新测试

---

## ✅ **最佳实践总结**

### DDD原则

- ✅ **按BC组织代码**：每个BC独立管理自己的预热策略
- ✅ **明确分层**：Domain → Application → Infrastructure → Interfaces
- ✅ **依赖方向**：外层依赖内层，内层不依赖外层

### 六边形架构原则

- ✅ **Port在Domain**：框架的 `CacheWarmupStrategy` 是Port
- ✅ **Adapter在BC**：各BC的策略类是Adapter
- ✅ **协调器是基础设施**：在 shared/infrastructure

### 单一职责原则

- ✅ **策略只关注业务逻辑**：什么数据需要预热
- ✅ **协调器只关注技术实现**：如何预热
- ✅ **API只关注接口**：HTTP接口

---

## 🎓 **总结**

### 当前实现的问题

1. ❌ 违反DDD分层原则
2. ❌ 违反BC隔离原则
3. ❌ 违反六边形架构原则
4. ❌ 不符合项目现有架构标准

### 建议

**立即重构**，按照上述方案重新组织代码，以符合：
- ✅ DDD的限界上下文和分层架构
- ✅ 六边形架构的端口和适配器模式
- ✅ my-shop 已有的高标准架构

这样才能保持架构的一致性和可维护性！
