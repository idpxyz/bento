"""Catalog context - Interface adapters (API layer)."""

from fastapi import APIRouter

from contexts.catalog.interfaces.product_api import router


def register_routes(parent_router: APIRouter) -> None:
    """Register catalog routes to parent router.

    This function is called by the router registry to register
    all catalog-related API endpoints.

    Args:
        parent_router: The parent APIRouter to register routes to
    """
    from contexts.catalog.interfaces.category_api import router as categories_router
    from contexts.catalog.interfaces.product_api import router as products_router

    parent_router.include_router(
        categories_router,
        prefix="/categories",
        tags=["categories"],
    )
    parent_router.include_router(
        products_router,
        prefix="/products",
        tags=["products"],
    )
