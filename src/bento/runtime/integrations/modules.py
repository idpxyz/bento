"""Module management for Bento Runtime."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class ModuleManager:
    """Manages module lifecycle operations."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize module manager.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    async def reload(self, name: str) -> "BentoRuntime":
        """Reload a module at runtime (hot reload).

        Unregisters the module, clears its services, and re-registers it.
        Useful for development and testing.

        Args:
            name: Module name to reload

        Returns:
            Self for chaining

        Raises:
            KeyError: If module not found

        Example:
            ```python
            # Reload a module during development
            await runtime.reload_module("catalog")
            # Module is re-registered with fresh state
            ```
        """
        if not self.runtime.registry.has(name):
            raise KeyError(f"Module not found: {name}")

        module = self.runtime.registry.get(name)
        logger.info(f"Reloading module: {name}")

        # Clear module services from container
        # (Note: This is a best-effort cleanup; some services may have dependencies)
        for key in list(self.runtime.container.keys()):
            if key.startswith(f"{name}."):
                try:
                    self.runtime.container._services.pop(key, None)
                    self.runtime.container._factories.pop(key, None)
                except Exception as e:
                    logger.warning(f"Failed to clear service {key}: {e}")

        # Re-register the module
        await module.on_register(self.runtime.container)
        logger.info(f"Module reloaded: {name}")

        return self.runtime

    async def unload(self, name: str) -> "BentoRuntime":
        """Unload a module at runtime.

        Calls module shutdown hooks and removes it from the registry.

        Args:
            name: Module name to unload

        Returns:
            Self for chaining

        Raises:
            KeyError: If module not found

        Example:
            ```python
            # Unload a module
            await runtime.unload_module("catalog")
            # Module shutdown hooks are called
            ```
        """
        if not self.runtime.registry.has(name):
            raise KeyError(f"Module not found: {name}")

        module = self.runtime.registry.get(name)
        logger.info(f"Unloading module: {name}")

        # Call shutdown hook
        try:
            await module.on_shutdown(self.runtime.container)
        except Exception as e:
            logger.error(f"Error shutting down module {name}: {e}")

        # Clear module services
        for key in list(self.runtime.container.keys()):
            if key.startswith(f"{name}."):
                try:
                    self.runtime.container._services.pop(key, None)
                    self.runtime.container._factories.pop(key, None)
                except Exception as e:
                    logger.warning(f"Failed to clear service {key}: {e}")

        # Remove from registry
        self.runtime.registry._modules.pop(name, None)
        logger.info(f"Module unloaded: {name}")

        return self.runtime

    async def load(self, module: "BentoRuntime._BentoModule") -> "BentoRuntime":
        """Load a module at runtime.

        Registers the module and calls its registration hooks.

        Args:
            module: BentoModule instance to load

        Returns:
            Self for chaining

        Example:
            ```python
            # Load a module at runtime
            await runtime.load_module(new_module)
            # Module is registered with fresh state
            ```
        """
        logger.info(f"Loading module: {module.name}")

        # Register the module
        self.runtime.registry.register(module)

        # Call registration hook
        await module.on_register(self.runtime.container)

        logger.info(f"Module loaded: {module.name}")

        return self.runtime
