"""Lifecycle management and coordination."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages application lifecycle phases."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize lifecycle manager.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    async def startup(self) -> None:
        """Run all startup phases in order.

        Phases:
        1. Run gates (contract validation)
        2. Register modules
        3. Start modules
        """
        from bento.runtime.lifecycle import startup as lifecycle_startup

        await lifecycle_startup.run_gates(self.runtime)
        await lifecycle_startup.register_modules(self.runtime)
        await self._startup_modules()

    async def shutdown(self) -> None:
        """Run all shutdown phases in reverse order.

        Phases:
        1. Shutdown modules
        2. Cleanup database
        """
        await self._shutdown_modules()
        await self._cleanup_database()

    async def _startup_modules(self) -> None:
        """Run startup hooks for all modules."""
        modules = self.runtime.registry.resolve_order()
        for module in modules:
            logger.debug(f"Starting module: {module.name}")
            await module.on_startup(self.runtime.container)

    async def _shutdown_modules(self) -> None:
        """Run shutdown hooks for all modules (reverse order)."""
        modules = list(reversed(self.runtime.registry.resolve_order()))
        for module in modules:
            logger.debug(f"Shutting down module: {module.name}")
            try:
                await module.on_shutdown(self.runtime.container)
            except Exception as e:
                logger.error(f"Error shutting down {module.name}: {e}")

    async def _cleanup_database(self) -> None:
        """Cleanup database connections on shutdown."""
        try:
            engine = self.runtime.container.get("db.engine")
            if engine:
                from bento.infrastructure.database import cleanup_database

                await cleanup_database(engine)
        except KeyError:
            pass  # No database configured
        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")
