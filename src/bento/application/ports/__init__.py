"""Application layer ports (interfaces).

This module defines the ports (contracts) that the application layer depends on.
All ports should be defined as Protocol classes to maintain dependency inversion.
"""

from bento.application.ports.cache import Cache
from bento.application.ports.mapper import Mapper
from bento.application.ports.message_bus import MessageBus
from bento.application.ports.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
    ServiceNotFoundError,
)
from bento.application.ports.uow import UnitOfWork

# Alias for backward compatibility
IUnitOfWork = UnitOfWork

__all__ = [
    "Cache",
    "Mapper",
    "MessageBus",
    "ServiceDiscovery",
    "ServiceInstance",
    "ServiceNotFoundError",
    "UnitOfWork",
    "IUnitOfWork",
]
