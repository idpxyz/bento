"""Bento Runtime Module.

Provides application bootstrap, module system, and dependency injection.

Example:
    ```python
    from bento.runtime import BentoRuntime, BentoModule

    class CatalogModule(BentoModule):
        name = "catalog"
        requires = ["infra"]

        async def on_register(self, container):
            container.set("catalog.repo", CategoryRepository)

        def get_routers(self):
            return [catalog_router]

    runtime = (
        BentoRuntime()
        .with_config(service_name="my-shop")
        .with_contracts("./contracts")
        .with_modules(InfraModule(), CatalogModule())
    )

    app = runtime.create_fastapi_app(title="My Shop API")
    ```
"""

from bento.runtime.bootstrap import BentoRuntime, DatabaseConfig, RuntimeConfig
from bento.runtime.container import BentoContainer
from bento.runtime.module import BentoModule
from bento.runtime.registry import ModuleRegistry

__all__ = [
    "BentoRuntime",
    "RuntimeConfig",
    "DatabaseConfig",
    "BentoContainer",
    "BentoModule",
    "ModuleRegistry",
]
