"""Ordering context - Interface adapters (API layer)."""

from fastapi import APIRouter


def register_routes(parent_router: APIRouter) -> None:
    """Register ordering routes to parent router.

    This function is called by the router registry to register
    all ordering-related API endpoints.

    Args:
        parent_router: The parent APIRouter to register routes to
    """
    from contexts.ordering.interfaces.order_api import router as orders_router

    parent_router.include_router(
        orders_router,
        prefix="/orders",
        tags=["orders"],
    )


__all__ = ["register_routes"]
