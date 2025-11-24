"""Cache warmup protocol and interfaces.

This module defines the protocol for cache warmup strategies.
Applications should implement these protocols to define their
specific warmup logic.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T", covariant=True)


@runtime_checkable
class CacheWarmupStrategy(Protocol[T]):
    """Cache warmup strategy protocol.

    Applications should implement this protocol to define their
    specific cache warmup logic and business rules.

    The framework provides the mechanism (CacheWarmer),
    while applications provide the policy (Strategy).

    Example:
        ```python
        class HotProductsWarmupStrategy:
            '''Warmup hot products cache.'''

            def __init__(self, product_service: ProductService):
                self._product_service = product_service

            async def get_keys_to_warmup(self) -> list[str]:
                # Business logic: get hot products
                products = await self._product_service.get_hot_products(limit=100)
                return [f"Product:id:{p.id}" for p in products]

            async def load_data(self, key: str) -> Product | None:
                # Business logic: load product data
                product_id = key.split(":")[-1]
                return await self._product_service.get_by_id(product_id)

            def get_priority(self) -> int:
                return 100  # High priority
        ```
    """

    async def get_keys_to_warmup(self) -> list[str]:
        """Get list of cache keys to warmup.

        This method should implement the business logic to determine
        which cache keys need to be warmed up.

        Returns:
            List of cache keys that need to be warmed up.
            Empty list if no keys need warmup.

        Example:
            ```python
            async def get_keys_to_warmup(self) -> list[str]:
                # Get hot products from last 30 days
                products = await self.product_service.get_hot_products(
                    days=30,
                    limit=100
                )
                return [f"Product:id:{p.id}" for p in products]
            ```
        """
        ...

    async def load_data(self, key: str) -> T | None:
        """Load data for a specific cache key.

        This method should implement the business logic to load
        the actual data that will be cached.

        Args:
            key: Cache key to load data for

        Returns:
            Data to cache, or None if data not found or should not be cached.

        Example:
            ```python
            async def load_data(self, key: str) -> Product | None:
                product_id = key.split(":")[-1]
                return await self.product_service.get_by_id(product_id)
            ```
        """
        ...

    def get_priority(self) -> int:
        """Get warmup priority.

        Higher priority strategies are executed first when using
        warmup_multiple(). This allows critical data to be warmed
        up before less important data.

        Returns:
            Priority value. Higher values = higher priority.
            Default is 0.

        Example:
            ```python
            def get_priority(self) -> int:
                return 100  # High priority for hot products
            ```
        """
        return 0

    def get_ttl(self) -> int | None:
        """Get TTL for warmed cache entries.

        Optional method to specify custom TTL for this strategy's
        cache entries. If not implemented or returns None, the
        CacheWarmer's default TTL will be used.

        Returns:
            TTL in seconds, or None to use default

        Example:
            ```python
            def get_ttl(self) -> int:
                return 7200  # 2 hours for this strategy
            ```
        """
        return None
