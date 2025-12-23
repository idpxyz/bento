"""
Leg Bounded Context Module.

Registers:
- Leg repositories
- Leg command/query handlers
- Leg HTTP routers
"""

from collections.abc import Sequence

from loms.bootstrap.registry import Container, Module


class LegModule:
    """Leg bounded context module implementing the Module protocol."""

    @property
    def name(self) -> str:
        return "leg"

    @property
    def requires(self) -> Sequence[str]:
        return ("infra",)

    def register(self, container: Container) -> None:
        """Register leg context components into the container."""
        # HTTP routers
        from loms.contexts.leg.interfaces.http.v1.router import router
        container.set("leg.router", router)
