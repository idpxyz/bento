"""商品缓存预热服务（Catalog BC）.

职责：定义商品相关的缓存预热策略
符合DDD原则：应用层服务，使用仓储和查询
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contexts.catalog.infrastructure.repositories import IProductRepository

logger = logging.getLogger(__name__)


class HotProductsWarmupStrategy:
    """预热热销商品缓存.

    业务逻辑：
    - 查询最近活跃的商品（通过Repository的聚合查询功能）
    - 为最常访问的商品预热缓存

    优先级：HIGH (100) - 对用户体验最关键
    """

    def __init__(self, product_repository: IProductRepository):
        """初始化策略.

        Args:
            product_repository: 商品仓储（依赖注入）
        """
        self._product_repo = product_repository

    async def get_keys_to_warmup(self) -> list[str]:
        """获取需要预热的商品缓存键.

        Returns:
            商品缓存键列表
        """
        try:
            # 使用Repository查询所有商品
            # 实际生产中可以：
            # 1. 使用聚合查询统计浏览量/销量
            # 2. 从订单系统获取热销商品ID
            # 3. 从推荐系统获取热门商品
            products = await self._product_repo.list(limit=100)

            # 生成缓存键
            cache_keys = [f"Product:id:{product.id}" for product in products]

            logger.info(f"Catalog BC - 准备预热 {len(cache_keys)} 个商品")
            return cache_keys

        except Exception as e:
            logger.error(f"获取商品预热键失败: {e}", exc_info=True)
            return []

    async def load_data(self, key: str):
        """加载商品数据.

        Args:
            key: 缓存键 (格式: "Product:id:{id}")

        Returns:
            商品聚合根或None
        """
        try:
            # 从键中提取商品ID
            product_id = key.split(":")[-1]

            # 通过Repository加载聚合根
            product = await self._product_repo.get(product_id)

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
        """返回自定义TTL: 2小时.

        热销商品访问频繁，缓存时间可以长一些
        """
        return 7200
