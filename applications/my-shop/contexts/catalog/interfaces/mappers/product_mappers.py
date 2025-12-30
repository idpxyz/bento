"""Product mappers for DTO → Response conversion."""

from functools import lru_cache

from bento.application.dto import PydanticResponseMapper

from contexts.catalog.application.dto.product_dto import ProductDTO
from contexts.catalog.domain.models.product import Product
from contexts.catalog.interfaces.dto.product_responses import ProductResponse


@lru_cache(maxsize=1)
def _get_response_mapper() -> PydanticResponseMapper[ProductDTO, ProductResponse]:
    """Get or create ProductResponseMapper singleton."""
    return PydanticResponseMapper(ProductDTO, ProductResponse)


def product_to_response(product: Product | ProductDTO) -> ProductResponse:
    """Convert Product (domain or DTO) to ProductResponse."""
    if isinstance(product, Product):
        dto = ProductDTO(
            id=str(product.id),
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock,
            sku=product.sku,
            brand=product.brand,
            is_active=product.is_active,
            sales_count=product.sales_count,
            category_id=str(product.category_id) if product.category_id else None,
            is_categorized=product.is_categorized(),
        )
        return _get_response_mapper().to_response(dto)
    else:
        return _get_response_mapper().to_response(product)
