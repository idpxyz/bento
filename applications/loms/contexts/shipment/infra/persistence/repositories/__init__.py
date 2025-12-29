"""Shipment repositories - auto-import to trigger @repository_for decorators."""
from loms.contexts.shipment.infra.persistence.repositories.shipment_repo import ShipmentRepository

__all__ = ["ShipmentRepository"]
