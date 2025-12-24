"""Catalog module for my-shop.

Provides catalog context:
- Category repository
- Product repository
- Cache warmup
- API routers
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bento.runtime import BentoModule

if TYPE_CHECKING:
    from bento.runtime import BentoContainer

logger = logging.getLogger(__name__)


class CatalogModule(BentoModule):
    """Catalog bounded context module."""

    name = "catalog"
    requires = ["infra"]

    async def on_register(self, container: "BentoContainer") -> None:
        """Register catalog services."""
        from contexts.catalog.infrastructure.repositories.category_repository_impl import (
            CategoryRepository,
        )
        from contexts.catalog.infrastructure.repositories.product_repository_impl import (
            ProductRepository,
        )

        container.set_factory("catalog.category_repository", CategoryRepository)
        container.set_factory("catalog.product_repository", ProductRepository)

        logger.info("Catalog services registered")

    async def on_startup(self, container: "BentoContainer") -> None:
        """Warm up catalog cache."""
        from config.warmup_config import setup_cache_warmup
        from contexts.catalog.infrastructure.repositories.category_repository_impl import (
            CategoryRepository,
        )
        from contexts.catalog.infrastructure.repositories.product_repository_impl import (
            ProductRepository,
        )

        cache = container.get("cache")
        session_factory = container.get("db.session_factory")

        async with session_factory() as session:
            product_repo = ProductRepository(session, actor="system")
            category_repo = CategoryRepository(session, actor="system")

            warmup_coordinator = await setup_cache_warmup(
                cache,
                product_repository=product_repo,
                category_repository=category_repo,
                warmup_on_startup=True,
                max_concurrency=20,
            )

            container.set("catalog.warmup_coordinator", warmup_coordinator)

        logger.info("Catalog cache warmed up")

    def get_routers(self) -> list[Any]:
        """Return catalog API routers with /api/v1 prefix."""
        from fastapi import APIRouter
        from contexts.catalog.interfaces import register_routes

        router = APIRouter(prefix="/api/v1")
        register_routes(router)
        return [router]
