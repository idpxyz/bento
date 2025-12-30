"""Identity module for my-shop.

Provides identity context:
- User repository
- API routers
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bento.runtime import BentoModule

if TYPE_CHECKING:
    from bento.runtime import BentoContainer

logger = logging.getLogger(__name__)


class IdentityModule(BentoModule):
    """Identity bounded context module."""

    name = "identity"
    requires = ["infra"]
    scan_packages = [
        "contexts.identity.infrastructure.repositories.user_repository_impl",
    ]

    async def on_register(self, container: "BentoContainer") -> None:
        """Register identity services."""
        from contexts.identity.infrastructure.repositories.user_repository_impl import (
            UserRepository,
        )

        container.set_factory("identity.user_repository", UserRepository)

        logger.info("Identity services registered")

    def get_routers(self) -> list:
        """Return identity API routers with /api/v1 prefix."""
        from fastapi import APIRouter
        from contexts.identity.interfaces import register_routes

        router = APIRouter(prefix="/api/v1")
        register_routes(router)
        return [router]
