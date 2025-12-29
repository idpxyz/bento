"""Service lifetime management for dependency injection.

Defines different service lifetimes: singleton, transient, and scoped.
"""

from enum import Enum


class ServiceLifetime(Enum):
    """Service lifetime enumeration.

    - SINGLETON: Single instance shared across entire application
    - TRANSIENT: New instance created each time
    - SCOPED: Single instance per scope (e.g., per request)
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"
