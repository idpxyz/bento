"""
Shipment Bounded Context Module.

Registers:
- Shipment repositories
- Shipment command/query handlers
- Shipment HTTP routers
"""

from collections.abc import Sequence

from loms.bootstrap.registry import Container, Module


class ShipmentModule:
    """Shipment bounded context module implementing the Module protocol."""

    @property
    def name(self) -> str:
        return "shipment"

    @property
    def requires(self) -> Sequence[str]:
        return ("infra",)

    def register(self, container: Container) -> None:
        """Register shipment context components into the container."""
        # Repository implementations
        from loms.contexts.shipment.infra.persistence.repositories.shipment_repo import (
            ShipmentRepositoryImpl,
        )
        container.set("shipment.repository_class", ShipmentRepositoryImpl)

        # HTTP routers
        from loms.contexts.shipment.interfaces.http.v1.shipments import router
        container.set("shipment.router", router)
