"""IProductCatalogService - Secondary Port（被驱动端口）

这是 Ordering Context 访问 Catalog Context 的契约定义。
符合六边形架构原则：Domain 层定义接口，Infrastructure 层实现。

Port vs Adapter:
- Port（本文件）: Domain 层定义的接口契约
- Adapter（infrastructure/adapters/）: 接口的具体技术实现
"""

from abc import ABC, abstractmethod

from contexts.ordering.domain.vo.product_info import ProductInfo


class IProductCatalogService(ABC):
    """产品目录服务接口（Secondary Port - 被驱动端口）

    职责：
    1. 定义 Ordering BC 需要的产品查询契约
    2. 隔离两个 BC 的变化（反腐败层）
    3. 支持依赖倒置（Domain 不依赖 Infrastructure）

    实现方式由 Adapter 决定：
    - ProductCatalogAdapter: 查询本地只读副本（当前实现）
    - ProductCatalogHttpAdapter: HTTP 调用（微服务场景）
    - ProductCatalogEventAdapter: 事件驱动同步（最终一致性）
    """

    @abstractmethod
    async def get_product_info(self, product_id: str) -> ProductInfo | None:
        """获取产品信息

        Args:
            product_id: 产品ID

        Returns:
            ProductInfo 或 None（产品不存在）
        """
        pass

    @abstractmethod
    async def get_products_info(self, product_ids: list[str]) -> dict[str, ProductInfo]:
        """批量获取产品信息

        Args:
            product_ids: 产品ID列表

        Returns:
            产品ID到ProductInfo的映射（不存在的产品不在结果中）
        """
        pass

    @abstractmethod
    async def check_products_available(self, product_ids: list[str]) -> tuple[list[str], list[str]]:
        """检查产品是否可用

        Args:
            product_ids: 产品ID列表

        Returns:
            (可用的产品ID列表, 不可用的产品ID列表)
        """
        pass
