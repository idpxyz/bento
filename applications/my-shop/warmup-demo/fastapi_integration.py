"""FastAPI integration example for cache warmup.

This module shows how to integrate cache warmup into a FastAPI application.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory
from fastapi import FastAPI

from .setup import setup_cache_warmup, warmup_single_strategy

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ==================== FastAPI Application Setup ====================


def create_app() -> FastAPI:
    """创建 FastAPI 应用并集成缓存预热.

    Returns:
        配置好的 FastAPI 应用实例
    """
    app = FastAPI(
        title="My Shop API", description="电商应用 API with cache warmup", version="1.0.0"
    )

    # ==================== Startup Event ====================

    @app.on_event("startup")
    async def startup():
        """应用启动时执行.

        包括：
        1. 创建缓存实例
        2. 初始化 Repository 和 Service
        3. 执行缓存预热
        """
        logger.info("🚀 应用启动中...")

        try:
            # 1. 创建缓存实例
            cache = await CacheFactory.create(
                CacheConfig(
                    backend=CacheBackend.REDIS,
                    redis_url="redis://localhost:6379/0",
                    ttl=3600,
                )
            )
            logger.info("✅ Redis 缓存已连接")

            # 2. 初始化各种Repository和Service
            # 实际应用中，这里会初始化真实的依赖
            product_repo = MockProductRepository()
            order_repo = MockOrderRepository()
            category_repo = MockCategoryRepository()
            user_service = MockUserService()

            logger.info("✅ Repository 和 Service 已初始化")

            # 3. 设置缓存预热
            warmer = await setup_cache_warmup(
                cache,
                product_repo,
                order_repo,
                category_repo,
                user_service,
                warmup_on_startup=True,  # 启动时立即预热
                max_concurrency=20,
            )

            # 保存到应用状态，供后续使用
            app.state.cache = cache
            app.state.cache_warmer = warmer
            app.state.product_repo = product_repo
            app.state.order_repo = order_repo
            app.state.category_repo = category_repo
            app.state.user_service = user_service

            logger.info("🎉 应用启动完成！")

        except Exception as e:
            logger.error(f"❌ 应用启动失败: {e}", exc_info=True)
            raise

    # ==================== Shutdown Event ====================

    @app.on_event("shutdown")
    async def shutdown():
        """应用关闭时执行."""
        logger.info("👋 应用关闭中...")

        if hasattr(app.state, "cache"):
            # 关闭缓存连接
            await app.state.cache.close()
            logger.info("✅ 缓存连接已关闭")

    # ==================== Health Check Endpoint ====================

    @app.get("/health")
    async def health_check():
        """健康检查端点.

        Returns:
            应用健康状态
        """
        return {
            "status": "healthy",
            "cache_enabled": hasattr(app.state, "cache"),
            "cache_warmup_enabled": hasattr(app.state, "cache_warmer"),
        }

    # ==================== Warmup Management Endpoints ====================

    @app.post("/admin/warmup/{strategy_name}")
    async def trigger_warmup(strategy_name: str):
        """手动触发缓存预热.

        Args:
            strategy_name: 策略名称（hot_products, categories, recommendations, sessions）

        Returns:
            预热结果

        Example:
            ```bash
            curl -X POST http://localhost:8000/admin/warmup/hot_products
            ```
        """
        if not hasattr(app.state, "cache_warmer"):
            return {"error": "Cache warmer not initialized"}

        logger.info(f"🔥 手动触发预热: {strategy_name}")

        try:
            await warmup_single_strategy(
                app.state.cache_warmer,
                strategy_name,
                product_repository=app.state.product_repo,
                order_repository=app.state.order_repo,
                category_repository=app.state.category_repo,
                user_service=app.state.user_service,
            )

            return {
                "success": True,
                "strategy": strategy_name,
                "message": f"Successfully warmed up {strategy_name}",
            }

        except Exception as e:
            logger.error(f"预热失败: {e}", exc_info=True)
            return {"success": False, "strategy": strategy_name, "error": str(e)}

    @app.get("/admin/warmup/stats")
    async def get_warmup_stats():
        """获取预热统计信息.

        Returns:
            预热统计
        """
        if not hasattr(app.state, "cache_warmer"):
            return {"error": "Cache warmer not initialized"}

        # 注意：这里需要保存预热历史才能返回统计
        # 简化示例只返回基本信息
        return {
            "enabled": True,
            "strategies": ["hot_products", "categories", "recommendations", "sessions"],
            "last_warmup": "2025-11-24T13:00:00",  # 实际应用需要记录时间戳
        }

    return app


# ==================== Mock Dependencies ====================


class MockProductRepository:
    """模拟商品仓储."""

    async def get_by_id(self, product_id: str):
        return {"id": product_id, "name": f"Product {product_id}", "price": 99.99}


class MockOrderRepository:
    """模拟订单仓储."""

    pass


class MockCategoryRepository:
    """模拟分类仓储."""

    async def get_by_id(self, category_id: str):
        return {"id": category_id, "name": f"Category {category_id}"}


class MockUserService:
    """模拟用户服务."""

    pass


# ==================== Run Application ====================


if __name__ == "__main__":
    import uvicorn

    app = create_app()

    # 运行应用
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
