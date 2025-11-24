"""分类缓存预热服务（Catalog BC）.

职责：定义分类相关的缓存预热策略
符合DDD原则：应用层服务，使用仓储
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contexts.catalog.infrastructure.repositories.category_repository import (
        ICategoryRepository,
    )

logger = logging.getLogger(__name__)


class CategoryWarmupStrategy:
    """预热分类缓存.

    业务逻辑：
    - 查询所有分类（分类数据通常不多）
    - 预热分类列表页和详情页

    优先级：MEDIUM (50) - 分类变化不频繁，但访问量大
    """

    def __init__(self, category_repository: ICategoryRepository):
        """初始化策略.

        Args:
            category_repository: 分类仓储（依赖注入）
        """
        self._category_repo = category_repository

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的分类缓存键.

        Returns:
            分类缓存键列表
        """
        try:
            # 查询所有分类
            # 实际生产中可以：
            # 1. 只查询一级和二级分类
            # 2. 查询有商品的分类
            # 3. 按热度排序
            categories = await self._category_repo.list(limit=200)

            # 生成缓存键
            cache_keys = [f"Category:id:{category.id}" for category in categories]

            # 额外预热：分类列表（经常被访问）
            cache_keys.append("Category:list:all")

            logger.info(f"Catalog BC - 准备预热 {len(cache_keys)} 个分类")
            return cache_keys

        except Exception as e:
            logger.error(f"获取分类预热键失败: {e}", exc_info=True)
            return []

    async def load_data(self, key: str):
        """加载分类数据.

        Args:
            key: 缓存键

        Returns:
            分类聚合根、分类列表或None
        """
        try:
            # 特殊处理：分类列表
            if key == "Category:list:all":
                categories = await self._category_repo.list(limit=200)
                logger.debug(f"成功加载分类列表: {len(categories)} 个")
                return categories

            # 单个分类
            category_id = key.split(":")[-1]
            category = await self._category_repo.get(category_id)

            if category:
                logger.debug(f"成功加载分类: {category_id}")
            else:
                logger.warning(f"分类不存在: {category_id}")

            return category

        except Exception as e:
            logger.error(f"加载分类数据失败 {key}: {e}", exc_info=True)
            raise

    def get_priority(self) -> int:
        """返回中等优先级."""
        return 50

    def get_ttl(self) -> int:
        """返回自定义TTL: 4小时.

        分类数据变化不频繁，可以缓存更长时间
        """
        return 14400
