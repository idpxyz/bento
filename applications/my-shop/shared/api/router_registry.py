"""Router Registry - Auto-discover and register all context routers.

This module implements the plugin pattern for route registration,
allowing each bounded context to register its own routes independently.
"""

from fastapi import APIRouter


def create_api_router() -> APIRouter:
    """Create API router with all context routes.

    Each context registers its routes through its interfaces module.
    This keeps main.py clean and allows contexts to be self-contained.

    Returns:
        APIRouter: Configured API router with all context routes
    """
    api_router = APIRouter()

    # Import and register routes from each context
    # Each context's interfaces module provides a register_routes() function
    from contexts.catalog.interfaces import register_routes as register_catalog
    from contexts.identity.interfaces import register_routes as register_identity
    from contexts.ordering.interfaces import register_routes as register_ordering

    # Register all context routes
    register_catalog(api_router)
    register_ordering(api_router)
    register_identity(api_router)

    return api_router
