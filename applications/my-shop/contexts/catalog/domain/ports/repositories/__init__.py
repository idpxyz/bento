"""Catalog Repository Ports - Secondary Ports

Repository interfaces for Catalog bounded context.
"""

from contexts.catalog.domain.ports.repositories.i_category_repository import ICategoryRepository
from contexts.catalog.domain.ports.repositories.i_product_repository import IProductRepository

__all__ = [
    "ICategoryRepository",
    "IProductRepository",
]
