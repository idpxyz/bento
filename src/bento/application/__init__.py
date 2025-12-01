"""Bento Framework Application Layer.

This layer contains application services, DTOs, ports (interfaces),
and various patterns used in the application layer.

Organized by functionality:
- services/: Application services (ApplicationService, QueryService, BatchService)
- dto/: Data Transfer Objects
- ports/: Interfaces and protocols (UoW, MessageBus, etc.)
- mappers/: Data mapping utilities
- patterns/: Cross-cutting patterns (idempotency, saga, etc.)
"""

# Main exports for the application layer
from .services import (
    ApplicationService,
    ApplicationServiceResult,
    BatchService,
    QueryService,
    create_service_factory,
    validate_service_compliance,
)

__all__ = [
    "ApplicationService",
    "ApplicationServiceResult",
    "QueryService",
    "BatchService",
    "create_service_factory",
    "validate_service_compliance",
]
