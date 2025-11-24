"""Cache warmup setup for application startup.

This module integrates cache warmup into the application lifecycle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bento.adapters.cache.warmer import CacheWarmer

from .strategies import (
    ActiveUserSessionWarmupStrategy,
    CategoryCacheWarmupStrategy,
    HotProductsWarmupStrategy,
    MockRecommendationService,
    MockSessionStore,
    RecommendationWarmupStrategy,
)

if TYPE_CHECKING:
    from bento.application.ports.cache import Cache

logger = logging.getLogger(__name__)


async def setup_cache_warmup(
    cache: Cache,
    product_repository,
    order_repository,
    category_repository,
    user_service,
    *,
    warmup_on_startup: bool = True,
    max_concurrency: int = 20,
) -> CacheWarmer:
    """设置缓存预热.

    在应用启动时调用此函数，配置并执行缓存预热。

    Args:
        cache: 缓存实例
        product_repository: 商品仓储
        order_repository: 订单仓储
        category_repository: 分类仓储
        user_service: 用户服务
        warmup_on_startup: 是否在启动时立即预热（默认True）
        max_concurrency: 最大并发数（默认20）

    Returns:
        CacheWarmer实例，可用于后续预热操作

    Example:
        ```python
        # 在 FastAPI 启动时
        @app.on_event("startup")
        async def startup():
            warmer = await setup_cache_warmup(
                cache,
                product_repo,
                order_repo,
                category_repo,
                user_service
            )

            # warmer 可以保存下来，用于后续操作
            app.state.cache_warmer = warmer
        ```
    """
    logger.info("=" * 60)
    logger.info("🔥 初始化缓存预热系统")
    logger.info("=" * 60)

    # 1. 创建缓存预热器（框架提供）
    warmer = CacheWarmer(
        cache,
        max_concurrency=max_concurrency,
        default_ttl=3600,
        enable_progress=True,
    )

    logger.info(f"✅ 缓存预热器已创建（并发数: {max_concurrency}）")

    if warmup_on_startup:
        # 2. 执行启动时预热
        await execute_warmup(
            warmer,
            product_repository,
            order_repository,
            category_repository,
            user_service,
        )
    else:
        logger.info("⏸️  跳过启动时预热（warmup_on_startup=False）")

    logger.info("=" * 60)
    return warmer


async def execute_warmup(
    warmer: CacheWarmer,
    product_repository,
    order_repository,
    category_repository,
    user_service,
) -> dict:
    """执行缓存预热.

    Args:
        warmer: CacheWarmer实例
        product_repository: 商品仓储
        order_repository: 订单仓储
        category_repository: 分类仓储
        user_service: 用户服务

    Returns:
        预热统计结果字典
    """
    logger.info("🚀 开始执行缓存预热...")

    # 3. 创建预热策略（应用提供）
    # Mock services for demonstration
    rec_service = MockRecommendationService()
    session_store = MockSessionStore()

    strategies = [
        # 高优先级：热销商品（最先预热）
        HotProductsWarmupStrategy(product_repository, order_repository),
        # 中等偏高优先级：推荐数据
        RecommendationWarmupStrategy(rec_service),
        # 中等优先级：分类数据
        CategoryCacheWarmupStrategy(category_repository),
        # 低优先级：用户会话（最后预热）
        ActiveUserSessionWarmupStrategy(user_service, session_store),
    ]

    logger.info(f"📋 准备执行 {len(strategies)} 个预热策略:")
    for strategy in strategies:
        name = strategy.__class__.__name__
        priority = strategy.get_priority()
        logger.info(f"   - {name} (优先级: {priority})")

    # 4. 执行预热（按优先级自动排序）
    results = await warmer.warmup_multiple(strategies)

    # 5. 打印统计结果
    logger.info("")
    logger.info("✨ 缓存预热完成！统计结果:")
    logger.info("-" * 60)

    total_warmed = 0
    total_keys = 0
    total_duration = 0.0

    for strategy_name, stats in results.items():
        total_warmed += stats.warmed_keys
        total_keys += stats.total_keys
        total_duration += stats.duration_seconds

        logger.info(f"  📊 {strategy_name}:")
        logger.info(f"     - 预热键数: {stats.warmed_keys}/{stats.total_keys}")
        logger.info(f"     - 跳过: {stats.skipped_keys}, 失败: {stats.failed_keys}")
        logger.info(f"     - 成功率: {stats.success_rate:.1%}")
        logger.info(f"     - 耗时: {stats.duration_seconds:.2f}s")

        if stats.errors:
            logger.warning(f"     - 错误: {len(stats.errors)} 个")
            for error in stats.errors[:3]:  # 只显示前3个错误
                logger.warning(f"       {error}")

    logger.info("-" * 60)
    logger.info(f"  🎯 总计: {total_warmed}/{total_keys} 个键已预热")
    logger.info(f"  ⏱️  总耗时: {total_duration:.2f}s")
    logger.info(f"  🏆 总成功率: {total_warmed / total_keys * 100 if total_keys > 0 else 0:.1f}%")
    logger.info("=" * 60)

    return results


async def warmup_single_strategy(
    warmer: CacheWarmer,
    strategy_name: str,
    **dependencies,
) -> None:
    """预热单个策略（用于增量预热）.

    Args:
        warmer: CacheWarmer实例
        strategy_name: 策略名称（"hot_products", "categories", "recommendations", "sessions"）
        **dependencies: 策略依赖的服务

    Example:
        ```python
        # 只预热热销商品
        await warmup_single_strategy(
            warmer,
            "hot_products",
            product_repository=product_repo,
            order_repository=order_repo
        )
        ```
    """
    logger.info(f"🔄 开始增量预热: {strategy_name}")

    # 创建对应的策略
    if strategy_name == "hot_products":
        strategy = HotProductsWarmupStrategy(
            dependencies["product_repository"], dependencies["order_repository"]
        )
    elif strategy_name == "categories":
        strategy = CategoryCacheWarmupStrategy(dependencies["category_repository"])
    elif strategy_name == "recommendations":
        rec_service = MockRecommendationService()
        strategy = RecommendationWarmupStrategy(rec_service)
    elif strategy_name == "sessions":
        session_store = MockSessionStore()
        strategy = ActiveUserSessionWarmupStrategy(dependencies["user_service"], session_store)
    else:
        logger.error(f"❌ 未知的策略: {strategy_name}")
        return

    # 执行预热
    stats = await warmer.warmup(strategy)

    logger.info(f"✅ 增量预热完成: {stats.warmed_keys}/{stats.total_keys} 个键")


# ==================== 进度回调示例 ====================


async def progress_callback(current: int, total: int) -> None:
    """预热进度回调.

    Args:
        current: 当前完成数
        total: 总数
    """
    percentage = (current / total * 100) if total > 0 else 0

    # 每完成10%打印一次
    if current % max(total // 10, 1) == 0 or current == total:
        logger.info(f"  🔄 预热进度: {current}/{total} ({percentage:.1f}%)")


# ==================== 监控集成示例 ====================


async def collect_warmup_metrics(warmer: CacheWarmer) -> dict:
    """收集预热指标（用于监控系统）.

    Args:
        warmer: CacheWarmer实例

    Returns:
        指标字典

    Example:
        ```python
        # 定期收集指标
        while True:
            metrics = await collect_warmup_metrics(warmer)
            # 发送到 Prometheus/CloudWatch/等
            await send_to_monitoring(metrics)
            await asyncio.sleep(60)
        ```
    """
    # 注意：需要保存预热统计结果
    # 这里只是示例，实际应用需要持久化统计数据

    metrics = {
        "cache_warmup_enabled": True,
        "cache_warmup_last_run": "2025-11-24T13:00:00",  # 实际应用记录时间戳
        "cache_warmup_strategies_count": 4,
    }

    return metrics
