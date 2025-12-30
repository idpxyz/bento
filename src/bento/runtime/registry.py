"""Module Registry with topological sorting.

Manages module registration and ensures correct initialization order
based on declared dependencies.

Example:
    ```python
    from bento.runtime import ModuleRegistry, BentoModule

    class InfraModule(BentoModule):
        name = "infra"

    class CatalogModule(BentoModule):
        name = "catalog"
        requires = ["infra"]

    registry = ModuleRegistry()
    registry.register(InfraModule())
    registry.register(CatalogModule())

    # Get modules in dependency order
    for module in registry.resolve_order():
        await module.on_register(container)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.module import BentoModule


class ModuleRegistry:
    """Registry for application modules with dependency resolution.

    Provides topological sorting to ensure modules are initialized
    in the correct order based on their dependencies.
    """

    def __init__(self) -> None:
        self._modules: dict[str, BentoModule] = {}
        self._cached_order: list[BentoModule] | None = None

    def register(self, module: BentoModule) -> ModuleRegistry:
        """Register a module.

        Args:
            module: BentoModule instance

        Returns:
            Self for chaining
        """
        if module.name in self._modules:
            raise ValueError(f"Module already registered: {module.name}")
        self._modules[module.name] = module
        self._cached_order = None  # Invalidate cache
        return self

    def register_all(self, *modules: BentoModule) -> ModuleRegistry:
        """Register multiple modules.

        Args:
            *modules: BentoModule instances

        Returns:
            Self for chaining
        """
        for module in modules:
            self.register(module)
        return self

    def get(self, name: str) -> BentoModule:
        """Get a module by name.

        Args:
            name: Module name

        Returns:
            BentoModule instance

        Raises:
            KeyError: If module not found
        """
        if name not in self._modules:
            raise KeyError(f"Module not found: {name}")
        return self._modules[name]

    def has(self, name: str) -> bool:
        """Check if module is registered."""
        return name in self._modules

    def validate(self) -> None:
        """Validate all module dependencies exist.

        Raises:
            ValueError: If a required module is missing
        """
        for name, module in self._modules.items():
            for dep in module.requires:
                if dep not in self._modules:
                    raise ValueError(
                        f"Module '{name}' requires '{dep}' but it is not registered"
                    )

    def resolve_order(self) -> list[BentoModule]:
        """Return modules in topological order (dependencies first).

        Uses cached result if available for performance.

        Returns:
            List of modules in initialization order

        Raises:
            ValueError: If circular dependency detected
        """
        # Return cached result if available
        if self._cached_order is not None:
            return self._cached_order

        self.validate()

        visited: set[str] = set()
        temp: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in temp:
                raise ValueError(f"Circular dependency detected at module: {name}")

            temp.add(name)
            for dep in self._modules[name].requires:
                visit(dep)
            temp.remove(name)
            visited.add(name)
            order.append(name)

        for name in self._modules:
            visit(name)

        # Cache the result
        self._cached_order = [self._modules[name] for name in order]
        return self._cached_order

    def names(self) -> list[str]:
        """Return all registered module names."""
        return list(self._modules.keys())

    def __len__(self) -> int:
        return len(self._modules)

    def __iter__(self):
        return iter(self._modules.values())
