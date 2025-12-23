"""
LOMS vNext - Runtime Module Registry

Responsibility:
- Declare which modules (bounded contexts + shared infrastructure modules) are enabled.
- Provide a deterministic registration order and basic dependency checks.

Design rules:
- runtime/* may import contexts/* and shared/*
- contexts/* MUST NOT import runtime/*
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol
from dataclasses import dataclass, field

# ----- Runtime primitives (kept lightweight; can be moved to shared/platform later) -----


class Container(Protocol):
    """
    Minimal DI container protocol.

    Your actual container can be:
    - a simple dict-like registry
    - dependency_injector
    - punq
    - dishka
    - custom Bento container
    """

    def set(self, key: str, value: object) -> None: ...
    def get(self, key: str) -> object: ...


class Module(Protocol):
    """
    Runtime module contract.

    A module may register:
    - configuration (Settings)
    - ports/adapters (EventBus, DB sessions, clients)
    - handlers (command/query/event handlers)
    - API routers (FastAPI routers)
    """

    @property
    def name(self) -> str: ...

    @property
    def requires(self) -> Sequence[str]: ...

    def register(self, container: Container) -> None: ...


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    factory: Callable[[], Module]
    requires: Sequence[str] = field(default_factory=tuple)


class ModuleRegistry:
    """
    Holds enabled modules and produces them in a correct order.
    """

    def __init__(self, specs: Iterable[ModuleSpec]) -> None:
        self._specs: dict[str, ModuleSpec] = {s.name: s for s in specs}
        self._validate_specs()

    def _validate_specs(self) -> None:
        # Ensure unique names and that requires references exist (unless external)
        for name, spec in self._specs.items():
            for dep in spec.requires:
                if dep not in self._specs:
                    raise ValueError(
                        f"Module '{name}' requires '{dep}' but '{dep}' is not registered."
                    )

    def resolve_order(self) -> list[str]:
        """
        Topological sort of modules based on requires.
        """
        visited: set[str] = set()
        temp: set[str] = set()
        order: list[str] = []

        def visit(n: str) -> None:
            if n in visited:
                return
            if n in temp:
                raise ValueError(f"Cyclic module dependency detected at '{n}'.")
            temp.add(n)
            for d in self._specs[n].requires:
                visit(d)
            temp.remove(n)
            visited.add(n)
            order.append(n)

        for name in list(self._specs.keys()):
            visit(name)

        return order

    def build_modules_in_order(self) -> list[Module]:
        order = self.resolve_order()
        return [self._specs[n].factory() for n in order]

    def specs(self) -> Mapping[str, ModuleSpec]:
        return dict(self._specs)


# ----- Concrete module registration for LOMS -----


def build_default_registry() -> ModuleRegistry:
    """
    Register modules for the LOMS service.

    Notes:
    - Keep infra/platform modules early (DB, event bus, outbox/inbox, tracing).
    - Then register contexts (shipment, leg, ...).
    - If you later split "providers", "documents", etc., add them here.
    """

    # Import factories locally to avoid import-time side effects.
    # Each factory should return a module object implementing Module.
    from loms.contexts.leg.module import LegModule
    from loms.contexts.shipment.module import ShipmentModule
    from loms.shared.infra.module import InfraModule

    specs: list[ModuleSpec] = [
        ModuleSpec(
            name="infra",
            factory=lambda: InfraModule(),
            requires=(),
        ),
        ModuleSpec(
            name="shipment",
            factory=lambda: ShipmentModule(),
            requires=("infra",),
        ),
        ModuleSpec(
            name="leg",
            factory=lambda: LegModule(),
            requires=("infra",),
        ),
        # Example:
        # ModuleSpec(
        #     name="documents",
        #     factory=lambda: DocumentsModule(),
        #     requires=("infra",),
        # ),
    ]

    return ModuleRegistry(specs=specs)
