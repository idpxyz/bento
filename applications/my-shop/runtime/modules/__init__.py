"""my-shop application modules using BentoRuntime.

Each module represents a bounded context or infrastructure concern.
"""

from runtime.modules.infra import InfraModule
from runtime.modules.catalog import CatalogModule
from runtime.modules.identity import IdentityModule
from runtime.modules.ordering import OrderingModule

__all__ = [
    "InfraModule",
    "CatalogModule",
    "IdentityModule",
    "OrderingModule",
]
