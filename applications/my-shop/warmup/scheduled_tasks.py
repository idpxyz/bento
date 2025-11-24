"""Scheduled cache warmup tasks.

This module demonstrates how to set up scheduled/periodic cache warmup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .setup import execute_warmup, warmup_single_strategy

if TYPE_CHECKING:
    from bento.adapters.cache.warmer import CacheWarmer

logger = logging.getLogger(__name__)


# ==================== Scheduler Setup ====================


def setup_warmup_scheduler(
    warmer: CacheWarmer,
    product_repository,
    order_repository,
    category_repository,
    user_service,
) -> AsyncIOScheduler:
    """设置定时预热任务.

    Args:
        warmer: CacheWarmer实例
        product_repository: 商品仓储
        order_repository: 订单仓储
        category_repository: 分类仓储
        user_service: 用户服务

    Returns:
        配置好的调度器

    Example:
        ```python
        # 在应用启动时
        scheduler = setup_warmup_scheduler(
            warmer,
            product_repo,
            order_repo,
            category_repo,
            user_service
        )

        # 启动调度器
        scheduler.start()

        # 应用关闭时停止调度器
        scheduler.shutdown()
        ```
    """
    logger.info("⏰ 设置缓存预热定时任务...")

    scheduler = AsyncIOScheduler()

    # ==================== 任务1: 夜间全量预热 ====================

    @scheduler.scheduled_job(
        CronTrigger(hour=2, minute=0),  # 每天凌晨2点
        id="nightly_full_warmup",
        name="夜间全量预热",
    )
    async def nightly_full_warmup():
        """夜间全量预热.

        时间：每天凌晨2点（低峰期）
        策略：预热所有数据
        并发：高并发（50）
        """
        logger.info("🌙 开始夜间全量预热...")

        try:
            # 夜间低峰期，可以使用更高的并发数
            warmer._max_concurrency = 50

            results = await execute_warmup(
                warmer,
                product_repository,
                order_repository,
                category_repository,
                user_service,
            )

            # 恢复正常并发数
            warmer._max_concurrency = 20

            total_keys = sum(s.total_keys for s in results.values())
            total_warmed = sum(s.warmed_keys for s in results.values())

            logger.info(f"✅ 夜间全量预热完成: {total_warmed}/{total_keys} 个键")

        except Exception as e:
            logger.error(f"❌ 夜间全量预热失败: {e}", exc_info=True)

    # ==================== 任务2: 高峰期前预热 ====================

    @scheduler.scheduled_job(
        CronTrigger(hour=8, minute=30),  # 每天早上8:30
        id="morning_peak_warmup",
        name="高峰期前预热",
    )
    async def morning_peak_warmup():
        """高峰期前预热.

        时间：每天早上8:30（高峰期前）
        策略：只预热关键数据（热销商品、推荐数据）
        """
        logger.info("🌅 开始高峰期前预热（关键数据）...")

        try:
            # 只预热热销商品
            await warmup_single_strategy(
                warmer,
                "hot_products",
                product_repository=product_repository,
                order_repository=order_repository,
            )

            # 预热推荐数据
            await warmup_single_strategy(
                warmer,
                "recommendations",
            )

            logger.info("✅ 高峰期前预热完成")

        except Exception as e:
            logger.error(f"❌ 高峰期前预热失败: {e}", exc_info=True)

    # ==================== 任务3: 增量预热（热点数据） ====================

    @scheduler.scheduled_job(
        IntervalTrigger(minutes=30),  # 每30分钟
        id="incremental_hot_warmup",
        name="增量预热热点数据",
    )
    async def incremental_hot_warmup():
        """增量预热热点数据.

        时间：每30分钟
        策略：只预热热销商品（数据变化快）
        并发：低并发（10）避免影响业务
        """
        logger.info("🔄 开始增量预热（热点数据）...")

        try:
            # 使用低并发，避免影响正常业务
            warmer._max_concurrency = 10

            await warmup_single_strategy(
                warmer,
                "hot_products",
                product_repository=product_repository,
                order_repository=order_repository,
            )

            # 恢复正常并发数
            warmer._max_concurrency = 20

            logger.info("✅ 增量预热完成")

        except Exception as e:
            logger.error(f"❌ 增量预热失败: {e}", exc_info=True)

    # ==================== 任务4: 分类缓存刷新 ====================

    @scheduler.scheduled_job(
        CronTrigger(hour="*/6", minute=0),  # 每6小时
        id="category_refresh",
        name="分类缓存刷新",
    )
    async def category_refresh():
        """分类缓存刷新.

        时间：每6小时
        策略：预热分类数据（变化不频繁，但需要定期更新）
        """
        logger.info("📁 开始分类缓存刷新...")

        try:
            await warmup_single_strategy(
                warmer,
                "categories",
                category_repository=category_repository,
            )

            logger.info("✅ 分类缓存刷新完成")

        except Exception as e:
            logger.error(f"❌ 分类缓存刷新失败: {e}", exc_info=True)

    # ==================== 任务5: 周末大促前预热 ====================

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="sat", hour=1, minute=0),  # 每周六凌晨1点
        id="weekend_sale_warmup",
        name="周末大促前预热",
    )
    async def weekend_sale_warmup():
        """周末大促前预热.

        时间：每周六凌晨1点
        策略：全量预热所有数据，为周末大促做准备
        """
        logger.info("🎉 开始周末大促前预热（全量）...")

        try:
            # 使用最高并发
            warmer._max_concurrency = 100

            results = await execute_warmup(
                warmer,
                product_repository,
                order_repository,
                category_repository,
                user_service,
            )

            # 恢复正常并发数
            warmer._max_concurrency = 20

            total_keys = sum(s.total_keys for s in results.values())
            total_warmed = sum(s.warmed_keys for s in results.values())

            logger.info(f"✅ 周末大促前预热完成: {total_warmed}/{total_keys} 个键")

        except Exception as e:
            logger.error(f"❌ 周末大促前预热失败: {e}", exc_info=True)

    logger.info(f"✅ 已配置 {len(scheduler.get_jobs())} 个定时预热任务:")
    for job in scheduler.get_jobs():
        logger.info(f"   - {job.name} ({job.id})")
        logger.info(f"     触发器: {job.trigger}")

    return scheduler


# ==================== 手动触发示例 ====================


async def manual_warmup_example(
    warmer: CacheWarmer,
    product_repository,
    order_repository,
    category_repository,
    user_service,
):
    """手动触发预热示例.

    这可以在运维脚本、管理后台等地方调用。
    """
    logger.info("📝 手动触发预热示例...")

    # 场景1：手动触发全量预热
    logger.info("场景1: 全量预热")
    await execute_warmup(
        warmer,
        product_repository,
        order_repository,
        category_repository,
        user_service,
    )

    # 场景2：只预热特定策略
    logger.info("场景2: 只预热热销商品")
    await warmup_single_strategy(
        warmer,
        "hot_products",
        product_repository=product_repository,
        order_repository=order_repository,
    )

    # 场景3：预热单个缓存键
    logger.info("场景3: 预热单个商品")

    async def load_product(key: str):
        product_id = key.split(":")[-1]
        return await product_repository.get_by_id(product_id)

    await warmer.warmup_single_key(
        "Product:id:special_001",
        load_product,
        ttl=7200,  # 自定义TTL
    )


# ==================== 监控和告警集成 ====================


async def warmup_monitoring_task(warmer: CacheWarmer):
    """预热监控任务.

    定期收集预热指标并发送到监控系统。
    """
    while True:
        try:
            # 这里可以收集预热统计并发送到 Prometheus/CloudWatch/等
            logger.info("📊 收集预热监控指标...")

            # 实际应用中：
            # metrics = collect_warmup_metrics(warmer)
            # await send_to_prometheus(metrics)
            # await send_to_cloudwatch(metrics)

            await asyncio.sleep(60)  # 每分钟收集一次

        except Exception as e:
            logger.error(f"监控任务失败: {e}", exc_info=True)
            await asyncio.sleep(60)


# ==================== 使用示例 ====================


async def main_example():
    """完整使用示例."""
    from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory
    from bento.adapters.cache.warmer import CacheWarmer

    # 1. 创建缓存
    cache = await CacheFactory.create(CacheConfig(backend=CacheBackend.MEMORY))

    # 2. 创建预热器
    warmer = CacheWarmer(cache)

    # 3. 模拟依赖
    from .fastapi_integration import (
        MockCategoryRepository,
        MockOrderRepository,
        MockProductRepository,
        MockUserService,
    )

    product_repo = MockProductRepository()
    order_repo = MockOrderRepository()
    category_repo = MockCategoryRepository()
    user_service = MockUserService()

    # 4. 设置调度器
    scheduler = setup_warmup_scheduler(
        warmer,
        product_repo,
        order_repo,
        category_repo,
        user_service,
    )

    # 5. 启动调度器
    scheduler.start()
    logger.info("🚀 调度器已启动")

    # 6. 保持运行
    try:
        # 在实际应用中，这会是应用的主循环
        await asyncio.sleep(3600)  # 运行1小时作为示例
    except KeyboardInterrupt:
        logger.info("收到中断信号，停止调度器...")
    finally:
        scheduler.shutdown()
        logger.info("调度器已停止")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main_example())
