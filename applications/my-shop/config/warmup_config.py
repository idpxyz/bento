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

    from contexts.catalog.infrastructure.repositories.category_repository import (
        ICategoryRepository,
    )
    from contexts.catalog.infrastructure.repositories.product_repository import (
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
    logger.info("🔧 开始配置缓存预热系统...")

    # 1. 创建协调器（共享基础设施）
    coordinator = CacheWarmupCoordinator(
        cache,
        max_concurrency=max_concurrency,
        default_ttl=3600,
        enable_progress=True,
    )

    # 2. 注册 Catalog BC 的预热策略
    logger.info("📦 注册 Catalog BC 预热策略...")

    coordinator.register_strategy(
        HotProductsWarmupStrategy(product_repository),
        tags=["catalog", "product", "high-priority"],
        metadata={"description": "预热热销商品（最常访问的100个商品）"},
    )

    coordinator.register_strategy(
        CategoryWarmupStrategy(category_repository),
        tags=["catalog", "category"],
        metadata={"description": "预热分类数据（所有分类+列表页）"},
    )

    # 3. TODO: 注册其他BC的预热策略
    # coordinator.register_strategy(
    #     UserSessionWarmupStrategy(user_service),
    #     bc_name="identity",
    #     description="预热活跃用户会话",
    # )

    # coordinator.register_strategy(
    #     RecentOrdersWarmupStrategy(order_repository),
    #     bc_name="ordering",
    #     description="预热最近订单",
    # )

    # 4. 打印已注册策略
    strategies = coordinator.list_strategies()
    logger.info(f"✅ 已注册 {len(strategies)} 个预热策略:")
    for name, metadata in strategies.items():
        tags_str = ", ".join(metadata.get("tags", []))
        logger.info(f"   - {name} (Tags: {tags_str}, Priority: {metadata['priority']})")

    # 5. 可选：执行启动时预热
    if warmup_on_startup:
        logger.info("🚀 执行启动时预热...")
        await coordinator.warmup_all()
    else:
        logger.info("⏸️  跳过启动时预热（warmup_on_startup=False）")

    logger.info("✅ 缓存预热系统配置完成")

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
