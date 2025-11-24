"""ProductCatalogAdapter - Secondary Adapter（被驱动适配器）

实现方式：直接查询 Catalog BC 的数据库表（适合 Modular Monolith）

六边形架构说明：
1. 本文件是 Secondary Adapter（被驱动适配器）
2. 实现了 domain/ports/services/i_product_catalog_service.py 定义的接口
3. 负责将外部系统（Catalog BC）的数据适配为 Domain 层需要的格式

技术选型：
1. 在 Modular Monolith 中，不同 BC 可以共享数据库，但应该：
   - 只读访问其他 BC 的表（不修改）
   - 通过 Adapter 隔离，而不是直接依赖领域模型

2. 未来迁移到微服务时，只需替换这个 Adapter 为 HTTP 客户端，
   Ordering BC 的其他代码无需修改（开闭原则）
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)
from contexts.ordering.domain.vo.product_info import ProductInfo


class ProductCatalogAdapter(IProductCatalogService):
    """产品目录适配器（Secondary Adapter - 被驱动适配器）

    职责：
    1. 实现 IProductCatalogService 接口
    2. 查询 Catalog BC 的只读视图
    3. 转换 ProductPO → ProductInfo（反腐败转换）

    未来可替换的实现：
    - ProductCatalogHttpAdapter: HTTP/gRPC 调用
    - ProductCatalogEventAdapter: 本地副本（事件同步）
    - ProductCatalogCacheAdapter: 添加缓存层
    """

    def __init__(self, session: AsyncSession):
        """初始化适配器

        Args:
            session: 数据库会话（只读访问 Catalog BC 的表）
        """
        self._session = session

    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        """获取产品信息"""
        stmt = select(ProductPO).where(
            ProductPO.id == product_id,
            ProductPO.deleted_at.is_(None),  # 只查询未删除的产品
        )
        result = await self._session.execute(stmt)
        product_po = result.scalar_one_or_none()

        if not product_po:
            return None

        return self._to_product_info(product_po)

    async def get_products_info(self, product_ids: list[str]) -> dict[str, ProductInfo]:
        """批量获取产品信息"""
        if not product_ids:
            return {}

        stmt = select(ProductPO).where(
            ProductPO.id.in_(product_ids),
            ProductPO.deleted_at.is_(None),  # 只查询未删除的产品
        )
        result = await self._session.execute(stmt)
        products = result.scalars().all()

        return {product.id: self._to_product_info(product) for product in products}

    async def check_products_available(self, product_ids: list[str]) -> tuple[list[str], list[str]]:
        """检查产品是否可用"""
        products_info = await self.get_products_info(product_ids)

        available = []
        unavailable = []

        for product_id in product_ids:
            product_info = products_info.get(product_id)
            if product_info and product_info.is_available:
                available.append(product_id)
            else:
                unavailable.append(product_id)

        return available, unavailable

    def _to_product_info(self, product_po: ProductPO) -> ProductInfo:
        """反腐败转换：ProductPO → ProductInfo

        这是关键的隔离点：
        - 输入：Catalog BC 的 ProductPO（持久化对象）
        - 输出：Ordering BC 的 ProductInfo（值对象）

        如果 Catalog BC 的 Product 模型发生变化，只需修改这里，
        Ordering BC 的其他代码不受影响（单一职责原则）。
        """
        return ProductInfo(
            product_id=product_po.id,
            product_name=product_po.name,
            unit_price=float(product_po.price),
            is_available=not product_po.is_deleted,  # 简化逻辑：未删除即可用
        )
