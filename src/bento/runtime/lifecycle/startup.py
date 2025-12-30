"""Application startup lifecycle management."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


async def run_gates(runtime: "BentoRuntime") -> None:
    """Run startup gates (contract validation).

    Args:
        runtime: BentoRuntime instance
    """
    if runtime.config.skip_gates_in_local and runtime.config.environment == "local":
        logger.debug("Skipping gates in local environment")
        return

    if not runtime.config.contracts_path:
        return

    from pathlib import Path

    contracts_dir = Path(runtime.config.contracts_path)
    if not contracts_dir.exists():
        if runtime.config.require_contracts:
            raise RuntimeError(f"Contracts directory not found: {contracts_dir}")
        return

    try:
        from bento.contracts import ContractLoader
        from bento.contracts.gates import ContractGate

        gate = ContractGate(
            contracts_root=str(contracts_dir),
            require_state_machines=False,
            require_reason_codes=True,
        )
        gate.validate()

        runtime._contracts = ContractLoader.load_from_dir(str(contracts_dir.parent))

        from bento.application.decorators import set_global_contracts
        from bento.core.exceptions import set_global_catalog

        if runtime._contracts.reason_codes:
            set_global_catalog(runtime._contracts.reason_codes)
        set_global_contracts(runtime._contracts)

        runtime.container.set("contracts", runtime._contracts)
        logger.info("Contracts loaded and validated")

    except ImportError:
        logger.warning("Contracts module not available, skipping validation")
    except Exception as e:
        if runtime.config.require_contracts:
            raise RuntimeError(f"Contract validation failed: {e}") from e
        logger.warning(f"Contract validation failed: {e}")


async def register_modules(runtime: "BentoRuntime") -> None:
    """Register all modules in dependency order.

    Args:
        runtime: BentoRuntime instance
    """
    modules = runtime.registry.resolve_order()
    logger.info(f"Registering {len(modules)} modules...")

    for module in modules:
        logger.debug(f"Registering module: {module.name}")
        await module.on_register(runtime.container)
        runtime._scan_module_packages(module)

    logger.info("All modules registered successfully")


def setup_database(runtime: "BentoRuntime") -> None:
    """Setup database session factory.

    Args:
        runtime: BentoRuntime instance
    """
    if runtime._session_factory is not None:
        return

    if not runtime.config.database or not runtime.config.database.url:
        import os

        env_url = os.getenv("DATABASE_URL")
        if not env_url:
            modules_needing_db = [
                m.name
                for m in runtime.registry.resolve_order()
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
                "No database configured. "
                "Database-dependent features will not be available."
            )
            return

        from bento.infrastructure.database import DatabaseConfig

        runtime.config.database = DatabaseConfig(url=env_url)

    try:
        from bento.infrastructure.database import (
            create_async_engine_from_config,
            create_async_session_factory,
        )

        engine = create_async_engine_from_config(runtime.config.database)
        runtime._session_factory = create_async_session_factory(engine)

        runtime.container.set("db.engine", engine)
        runtime.container.set("db.session_factory", runtime._session_factory)

        db_url = runtime.config.database.url
        masked_url = db_url.split("@")[-1] if "@" in db_url else db_url[:50]
        logger.info(f"Database configured: {masked_url}...")

    except Exception as e:
        raise RuntimeError(
            f"Failed to setup database: {e}\n"
            f"Check DATABASE_URL format and database connectivity."
        ) from e
