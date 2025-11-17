"""Domain ports (interfaces) for Identity module.

Ports define the contracts that adapters must implement.
Following Hexagonal Architecture principles:
- Domain layer defines interfaces (ports)
- Infrastructure layer implements them (adapters)
- Application layer depends on interfaces, not implementations
"""

from contexts.identity.domain.ports.user_repository import IUserRepository

__all__ = [
    "IUserRepository",
]
