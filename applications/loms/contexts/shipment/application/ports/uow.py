"""Re-export Bento's UnitOfWork protocol for Shipment context."""

from bento.application.ports.uow import UnitOfWork

__all__ = ["UnitOfWork"]
