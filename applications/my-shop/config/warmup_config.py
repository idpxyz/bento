"""缓存预热配置（应用启动配置）.

职责：组装各个BC的预热策略到协调器
符合DDD原则：应用配置层，连接基础设施和业务逻辑
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bento.adapters.cache.warmup_coordinator import CacheWarmupCoordinator

# 导入各BC的预热策略
from contexts.catalog.application.warmup import (
    CategoryWarmupStrategy,
    HotProductsWarmupStrategy,
)

if TYPE_CHECKING:
    from bento.application.ports.cache import Cache

    from contexts.catalog.domain.ports.repositories.i_category_repository import (
        ICategoryRepository,
    )
    from contexts.catalog.domain.ports.repositories.i_product_repository import (
        IProductRepository,
    )

logger = logging.getLogger(__name__)


async def setup_cache_warmup(
    cache: Cache,
    # Catalog BC 依赖
    product_repository: IProductRepository,
    category_repository: ICategoryRepository,
    # 可选：启动时是否立即预热
    warmup_on_startup: bool = True,
    max_concurrency: int = 20,
) -> CacheWarmupCoordinator:
    """设置缓存预热（应用启动时调用）.

    职责：
    1. 创建协调器
    2. 从各BC收集预热策略
    3. 注册到协调器
    4. 可选：执行启动时预热

    Args:
        cache: 缓存实例
        product_repository: 商品仓储（Catalog BC）
        category_repository: 分类仓储（Catalog BC）
        warmup_on_startup: 是否在启动时立即预热（默认True）
        max_concurrency: 最大并发数

    Returns:
        配置好的协调器实例

    Example:
        ```python
        # 在 FastAPI 启动时
        @app.on_event("startup")
        async def startup():
            cache = await CacheFactory.create(...)

            coordinator = await setup_cache_warmup(
                cache,
                product_repository=product_repo,
                category_repository=category_repo,
                warmup_on_startup=True,
            )

            app.state.warmup_coordinator = coordinator
        ```
    """
    logger.info("Configuring cache warmup system...")

    # 1. Create coordinator (shared infrastructure)
    coordinator = CacheWarmupCoordinator(
        cache,
        max_concurrency=max_concurrency,
        default_ttl=3600,
        enable_progress=True,
    )

    # 2. Register Catalog BC warmup strategies
    logger.info("Registering Catalog BC warmup strategies...")

    coordinator.register_strategy(
        HotProductsWarmupStrategy(product_repository),
        tags=["catalog", "product", "high-priority"],
        metadata={"description": "Warm up hot products (top 100 most accessed products)"},
    )

    coordinator.register_strategy(
        CategoryWarmupStrategy(category_repository),
        tags=["catalog", "category"],
        metadata={"description": "Warm up category data (all categories + list pages)"},
    )

    # 3. TODO: Register warmup strategies from other BCs
    # coordinator.register_strategy(
    #     UserSessionWarmupStrategy(user_service),
    #     bc_name="identity",
    #     description="Warm up active user sessions",
    # )

    # coordinator.register_strategy(
    #     RecentOrdersWarmupStrategy(order_repository),
    #     bc_name="ordering",
    #     description="Warm up recent orders",
    # )

    # 4. Print registered strategies
    strategies = coordinator.list_strategies()
    logger.info(f"Registered {len(strategies)} warmup strategies:")
    for name, metadata in strategies.items():
        tags_str = ", ".join(metadata.get("tags", []))
        logger.info(f"   - {name} (Tags: {tags_str}, Priority: {metadata['priority']})")

    # 5. Optional: Execute warmup on startup
    if warmup_on_startup:
        logger.info("Executing startup warmup...")
        await coordinator.warmup_all()
    else:
        logger.info("Skipping startup warmup (warmup_on_startup=False)")

    logger.info("Cache warmup system configuration completed")

    return coordinator


async def warmup_catalog_only(
    cache: Cache,
    product_repository: IProductRepository,
    category_repository: ICategoryRepository,
) -> dict:
    """仅预热 Catalog BC（用于增量预热）.

    Args:
        cache: 缓存实例
        product_repository: 商品仓储
        category_repository: 分类仓储

    Returns:
        预热统计结果
    """
    coordinator = CacheWarmupCoordinator(cache)

    coordinator.register_strategy(
        HotProductsWarmupStrategy(product_repository),
        tags=["catalog"],
    )

    coordinator.register_strategy(
        CategoryWarmupStrategy(category_repository),
        tags=["catalog"],
    )

    return await coordinator.warmup_by_tags(["catalog"])
