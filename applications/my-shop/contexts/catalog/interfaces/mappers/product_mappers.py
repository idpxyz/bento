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
        # Calculate computed fields
        price_tier = "expensive" if product.price > 100 else "affordable"
        stock_status = "in_stock" if product.stock > 0 else "out_of_stock"
        formatted_price = f"${product.price:.2f}"
        availability = "available" if product.is_active and product.stock > 0 else "unavailable"

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
            price_tier=price_tier,
            stock_status=stock_status,
            formatted_price=formatted_price,
            availability=availability,
        )
        return _get_response_mapper().to_response(dto)
    else:
        return _get_response_mapper().to_response(product)


def list_products_to_response(products: list[ProductDTO]) -> list[ProductResponse]:
    """Convert list of ProductDTO to list of ProductResponse."""
    return [_get_response_mapper().to_response(product) for product in products]
