"""Runtime builder for fluent configuration API.

Separates configuration (builder) from execution (runtime).
"""

from typing import TYPE_CHECKING, Any

from bento.infrastructure.database.config import DatabaseConfig
from bento.runtime.bootstrap import BentoRuntime
from bento.runtime.config import RuntimeConfig
from bento.runtime.container import BentoContainer
from bento.runtime.registry import ModuleRegistry

if TYPE_CHECKING:
    from bento.runtime.module import BentoModule


class RuntimeBuilder:
    """Builder for configuring BentoRuntime.

    Provides fluent API for configuration before building the runtime.

    Example:
        ```python
        runtime = (
            RuntimeBuilder()
            .with_config(service_name="my-shop")
            .with_contracts("./contracts")
            .with_modules(InfraModule(), CatalogModule())
            .build_runtime()
        )

        await runtime.build_async()
        ```
    """

    def __init__(self) -> None:
        """Initialize builder with default configuration."""
        self._config = RuntimeConfig()
        self._container = BentoContainer()
        self._registry = ModuleRegistry()
        self._uow_factory: Any = None
        self._event_bus: Any = None

    def with_config(
        self,
        service_name: str | None = None,
        environment: str | None = None,
        **kwargs: Any,
    ) -> "RuntimeBuilder":
        """Configure runtime settings.

        Args:
            service_name: Service name for logging/tracing
            environment: Environment (local/dev/stage/prod)
            **kwargs: Additional config options

        Returns:
            Self for chaining
        """
        if service_name:
            self._config.service_name = service_name
        if environment:
            self._config.environment = environment
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        return self

    def with_contracts(
        self,
        path: str,
        require: bool = True,
    ) -> "RuntimeBuilder":
        """Enable contract validation.

        Args:
            path: Path to contracts directory
            require: If True, fail if contracts are missing

        Returns:
            Self for chaining
        """
        self._config.contracts_path = path
        self._config.require_contracts = require
        return self

    def with_modules(self, *modules: "BentoModule") -> "RuntimeBuilder":
        """Register application modules.

        Args:
            *modules: BentoModule instances

        Returns:
            Self for chaining
        """
        self._registry.register_all(*modules)
        return self

    def with_service(self, key: str, value: Any) -> "RuntimeBuilder":
        """Register a service in the container.

        Args:
            key: Service identifier
            value: Service instance

        Returns:
            Self for chaining
        """
        self._container.set(key, value)
        return self

    def with_database(
        self,
        url: str | None = None,
        config: "DatabaseConfig | None" = None,
        **kwargs: Any,
    ) -> "RuntimeBuilder":
        """Configure database connection.

        Args:
            url: Database URL (shorthand)
            config: Full DatabaseConfig object
            **kwargs: Additional database config options

        Returns:
            Self for chaining
        """
        if config:
            self._config.database = config
        elif url:
            self._config.database = DatabaseConfig(url=url, **kwargs)
        return self

    def with_uow_factory(self, factory: Any) -> "RuntimeBuilder":
        """Configure custom UnitOfWork factory.

        Args:
            factory: Callable that creates UnitOfWork instances

        Returns:
            Self for chaining
        """
        self._uow_factory = factory
        return self

    def with_event_bus(self, event_bus: Any) -> "RuntimeBuilder":
        """Configure event bus for dual publishing strategy.

        Args:
            event_bus: Event bus instance

        Returns:
            Self for chaining
        """
        self._event_bus = event_bus
        return self

    def build_runtime(self) -> BentoRuntime:
        """Build the runtime from configuration.

        Returns:
            Configured BentoRuntime instance
        """
        runtime = BentoRuntime(
            config=self._config,
            container=self._container,
            registry=self._registry,
        )

        if self._uow_factory:
            runtime._uow_factory = self._uow_factory

        if self._event_bus:
            runtime._event_bus = self._event_bus

        return runtime
