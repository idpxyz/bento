"""Cache warmup strategies for my-shop application.

This module implements application-specific cache warmup strategies.
Each strategy encapsulates business logic about what data to warm up.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ==================== Strategy 1: Hot Products ====================


class HotProductsWarmupStrategy:
    """预热热销商品缓存.

    业务逻辑：预热最近30天销量最高的前100个商品
    这些是用户最常访问的商品，应该始终在缓存中。

    优先级：HIGH (100) - 对用户体验至关重要
    """

    def __init__(self, product_repository, order_repository):
        """初始化策略.

        Args:
            product_repository: 商品仓储
            order_repository: 订单仓储（用于统计销量）
        """
        self._product_repo = product_repository
        self._order_repo = order_repository

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的商品缓存键.

        Returns:
            商品缓存键列表
        """
        # 业务逻辑：从订单中统计最近30天的热销商品
        # 使用 Repository 的聚合查询功能
        try:
            # 业务逻辑：从订单中统计最近30天的热销商品
            # 使用 Repository 的聚合查询功能
            from datetime import datetime, timedelta

            datetime.now() - timedelta(days=30)

            # 实际实现中会调用：
            # hot_product_ids = await self._order_repo.group_by_field(
            #     "product_id",
            #     aggregate_method="count",
            #     specification=OrderDateSpec(start_date),
            #     limit=100
            # )

            # 简化示例：假设已有热销商品ID列表
            hot_product_ids = await self._get_hot_product_ids()

            # 生成缓存键：Product:id:{id}
            cache_keys = [f"Product:id:{pid}" for pid in hot_product_ids]

            logger.info(f"准备预热 {len(cache_keys)} 个热销商品")
            return cache_keys

        except Exception as e:
            logger.error(f"获取热销商品失败: {e}", exc_info=True)
            return []

    async def load_data(self, key: str) -> Any:
        """加载商品数据.

        Args:
            key: 缓存键 (格式: "Product:id:{id}")

        Returns:
            商品实体或None
        """
        try:
            # 从键中提取商品ID
            product_id = key.split(":")[-1]

            # 通过 Repository 加载商品
            product = await self._product_repo.get_by_id(product_id)

            if product:
                logger.debug(f"成功加载商品: {product_id}")
            else:
                logger.warning(f"商品不存在: {product_id}")

            return product

        except Exception as e:
            logger.error(f"加载商品数据失败 {key}: {e}", exc_info=True)
            raise

    def get_priority(self) -> int:
        """返回高优先级."""
        return 100

    def get_ttl(self) -> int:
        """返回自定义TTL：2小时."""
        return 7200  # 热销商品缓存2小时

    async def _get_hot_product_ids(self) -> list[str]:
        """获取热销商品ID（业务逻辑）."""
        # 实际实现会查询数据库
        # 这里返回示例数据
        return [f"prod_{i:03d}" for i in range(1, 101)]


# ==================== Strategy 2: Category Cache ====================


class CategoryCacheWarmupStrategy:
    """预热分类缓存.

    业务逻辑：预热所有一级和二级分类
    分类数据变化不频繁，但访问量大。

    优先级：MEDIUM (50)
    """

    def __init__(self, category_repository):
        """初始化策略.

        Args:
            category_repository: 分类仓储
        """
        self._category_repo = category_repository

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的分类缓存键."""
        try:
            # 业务逻辑：查询所有一级和二级分类
            # categories = await self._category_repo.find_all(
            #     specification=CategoryLevelSpec(max_level=2)
            # )

            # 简化示例
            categories = await self._get_top_categories()

            cache_keys = [f"Category:id:{c['id']}" for c in categories]

            # 额外预热：分类树缓存
            cache_keys.append("Category:tree:root")

            logger.info(f"准备预热 {len(cache_keys)} 个分类")
            return cache_keys

        except Exception as e:
            logger.error(f"获取分类失败: {e}", exc_info=True)
            return []

    async def load_data(self, key: str) -> Any:
        """加载分类数据."""
        try:
            if key == "Category:tree:root":
                # 加载整个分类树
                return await self._build_category_tree()

            # 加载单个分类
            category_id = key.split(":")[-1]
            category = await self._category_repo.get_by_id(category_id)

            if category:
                logger.debug(f"成功加载分类: {category_id}")

            return category

        except Exception as e:
            logger.error(f"加载分类数据失败 {key}: {e}", exc_info=True)
            raise

    def get_priority(self) -> int:
        """返回中等优先级."""
        return 50

    def get_ttl(self) -> int:
        """返回自定义TTL：4小时."""
        return 14400  # 分类数据缓存4小时

    async def _get_top_categories(self) -> list[dict]:
        """获取顶级分类（业务逻辑）."""
        return [
            {"id": f"cat_{i:02d}", "name": f"Category {i}", "level": 1 if i <= 5 else 2}
            for i in range(1, 21)
        ]

    async def _build_category_tree(self) -> dict:
        """构建分类树（业务逻辑）."""
        return {"root": {"children": await self._get_top_categories()}}


# ==================== Strategy 3: Recommendations ====================


class RecommendationWarmupStrategy:
    """预热推荐数据缓存.

    业务逻辑：预热首页推荐、热门推荐等常用推荐位
    这些数据计算成本高，应该提前缓存。

    优先级：MEDIUM-HIGH (60)
    """

    def __init__(self, recommendation_service):
        """初始化策略.

        Args:
            recommendation_service: 推荐服务
        """
        self._rec_service = recommendation_service

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的推荐缓存键."""
        # 业务逻辑：预热所有推荐位
        recommendation_slots = [
            "recommendations:homepage",  # 首页推荐
            "recommendations:trending",  # 热门商品
            "recommendations:new_arrivals",  # 新品推荐
            "recommendations:best_sellers",  # 畅销榜
        ]

        logger.info(f"准备预热 {len(recommendation_slots)} 个推荐位")
        return recommendation_slots

    async def load_data(self, key: str) -> Any:
        """加载推荐数据."""
        try:
            # 根据键调用不同的推荐逻辑
            slot_name = key.split(":")[-1]

            if slot_name == "homepage":
                data = await self._rec_service.get_homepage_recommendations()
            elif slot_name == "trending":
                data = await self._rec_service.get_trending_products()
            elif slot_name == "new_arrivals":
                data = await self._rec_service.get_new_arrivals()
            elif slot_name == "best_sellers":
                data = await self._rec_service.get_best_sellers()
            else:
                logger.warning(f"未知的推荐位: {slot_name}")
                return None

            logger.debug(f"成功加载推荐数据: {slot_name}")
            return data

        except Exception as e:
            logger.error(f"加载推荐数据失败 {key}: {e}", exc_info=True)
            raise

    def get_priority(self) -> int:
        """返回中等偏高优先级."""
        return 60

    def get_ttl(self) -> int:
        """返回自定义TTL：30分钟."""
        return 1800  # 推荐数据缓存30分钟


# ==================== Strategy 4: User Session ====================


class ActiveUserSessionWarmupStrategy:
    """预热活跃用户会话缓存.

    业务逻辑：预热最近活跃的用户会话数据
    避免用户首次访问时的缓存未命中。

    优先级：LOW (20) - 非关键数据
    """

    def __init__(self, user_service, session_store):
        """初始化策略.

        Args:
            user_service: 用户服务
            session_store: 会话存储
        """
        self._user_service = user_service
        self._session_store = session_store

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的用户会话键."""
        try:
            # 业务逻辑：获取最近1小时内活跃的用户ID
            from datetime import datetime, timedelta

            datetime.now() - timedelta(hours=1)

            # active_user_ids = await self._user_service.get_active_users(since=since)

            # 简化示例
            active_user_ids = _get_active_user_ids_mock_sync()

            cache_keys = [f"User:session:{uid}" for uid in active_user_ids]

            logger.info(f"准备预热 {len(cache_keys)} 个用户会话")
            return cache_keys

        except Exception as e:
            logger.error(f"获取活跃用户失败: {e}", exc_info=True)
            return []

    async def load_data(self, key: str) -> Any:
        """加载用户会话数据."""
        try:
            user_id = key.split(":")[-1]

            # 加载用户会话信息
            session_data = await self._session_store.get_session(user_id)

            if session_data:
                logger.debug(f"成功加载用户会话: {user_id}")

            return session_data

        except Exception as e:
            logger.error(f"加载用户会话失败 {key}: {e}", exc_info=True)
            raise

    def get_priority(self) -> int:
        """返回低优先级."""
        return 20

    def get_ttl(self) -> int:
        """返回自定义TTL：15分钟."""
        return 900


# ==================== Mock Services (for demonstration) ====================


class MockRecommendationService:
    """模拟推荐服务（实际应用中替换为真实服务）."""

    async def get_homepage_recommendations(self):
        return {"products": [f"prod_{i}" for i in range(1, 11)]}

    async def get_trending_products(self):
        return {"products": [f"prod_{i}" for i in range(11, 21)]}

    async def get_new_arrivals(self):
        return {"products": [f"prod_{i}" for i in range(21, 31)]}

    async def get_best_sellers(self):
        return {"products": [f"prod_{i}" for i in range(31, 41)]}


class MockSessionStore:
    """模拟会话存储（实际应用中替换为真实存储）."""

    async def get_session(self, user_id: str):
        return {"user_id": user_id, "last_active": "2025-11-24T13:00:00", "cart_items": []}


def _get_active_user_ids_mock_sync() -> list[str]:
    """模拟获取活跃用户ID."""
    return [f"user_{i:04d}" for i in range(1, 51)]
