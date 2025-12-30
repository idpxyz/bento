"""Container module with DI container and lifetime support.

Provides dependency injection container with service lifetime management.
"""

from bento.runtime.container.base import BentoContainer
from bento.runtime.container.lifetime import ServiceLifetime
from bento.runtime.container.scope import ContainerScope

__all__ = ["BentoContainer", "ServiceLifetime", "ContainerScope"]
