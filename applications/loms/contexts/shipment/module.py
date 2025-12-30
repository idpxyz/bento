"""
Shipment Bounded Context Module.

Registers:
- Shipment repositories (via Bento's @repository_for decorator pattern)
- Shipment command/query handlers
- Shipment HTTP routers
"""

from bento.runtime import BentoModule


class ShipmentModule(BentoModule):
    """Shipment bounded context module using BentoModule."""

    name = "shipment"
    requires = ("infra",)
    # Scan packages to trigger @repository_for decorators
    scan_packages = ("loms.contexts.shipment.infra.persistence.repositories",)

    async def on_register(self, container) -> None:
        """Register shipment context components into the container.

        Note: ShipmentRepository is auto-registered via @repository_for decorator
        when scan_packages imports the module.
        """

    def get_routers(self):
        """Return shipment API routers."""
        from loms.contexts.shipment.interfaces.http.v1.shipments import router

        return [router]
