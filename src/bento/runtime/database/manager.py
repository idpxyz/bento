"""Database management for runtime."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database lifecycle and configuration."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize database manager.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    def setup(self) -> None:
        """Setup database session factory."""
        if self.runtime._session_factory is not None:
            return

        if not self.runtime.config.database or not self.runtime.config.database.url:
            import os

            env_url = os.getenv("DATABASE_URL")
            if not env_url:
                modules_needing_db = [
                    m.name
                    for m in self.runtime.registry.resolve_order()
                    if getattr(m, "requires_database", False)
                ]

                if modules_needing_db:
                    raise RuntimeError(
                        f"Modules {modules_needing_db} require database, "
                        f"but no DATABASE_URL configured.\n"
                        f"Set DATABASE_URL environment variable or use "
                        f"runtime.with_database(url='...')"
                    )

                logger.warning(
                    "No database configured. Database-dependent features will not be available."
                )
                return

            from bento.infrastructure.database import DatabaseConfig

            self.runtime.config.database = DatabaseConfig(url=env_url)

        try:
            from bento.infrastructure.database import (
                create_async_engine_from_config,
                create_async_session_factory,
            )

            engine = create_async_engine_from_config(self.runtime.config.database)
            self.runtime._session_factory = create_async_session_factory(engine)

            self.runtime.container.set("db.engine", engine)
            self.runtime.container.set("db.session_factory", self.runtime._session_factory)

            db_url = self.runtime.config.database.url
            masked_url = db_url.split("@")[-1] if "@" in db_url else db_url[:50]
            logger.info(f"Database configured: {masked_url}...")

        except Exception as e:
            raise RuntimeError(
                f"Failed to setup database: {e}\n"
                f"Check DATABASE_URL format and database connectivity."
            ) from e

    async def cleanup(self) -> None:
        """Cleanup database connections."""
        try:
            engine = self.runtime.container.get("db.engine")
            if engine:
                from bento.infrastructure.database import cleanup_database

                await cleanup_database(engine)
                logger.info("Database cleaned up")
        except KeyError:
            pass
