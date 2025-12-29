"""Application shutdown lifecycle management."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


async def shutdown_modules(runtime: "BentoRuntime") -> None:
    """Shutdown all modules in reverse order.

    Args:
        runtime: BentoRuntime instance
    """
    modules = list(reversed(runtime.registry.resolve_order()))
    logger.info(f"Shutting down {len(modules)} modules...")

    for module in modules:
        try:
            logger.debug(f"Shutting down module: {module.name}")
            await module.on_shutdown(runtime.container)
        except Exception as e:
            logger.error(f"Error shutting down {module.name}: {e}")

    logger.info("All modules shut down successfully")


async def cleanup_database(runtime: "BentoRuntime") -> None:
    """Cleanup database connections on shutdown.

    Args:
        runtime: BentoRuntime instance
    """
    try:
        engine = runtime.container.get("db.engine")
        if engine:
            from bento.infrastructure.database import cleanup_database

            await cleanup_database(engine)
            logger.info("Database cleaned up")
    except KeyError:
        pass
