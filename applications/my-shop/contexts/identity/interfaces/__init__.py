"""Identity context - Interface adapters (API layer)."""

from fastapi import APIRouter


def register_routes(parent_router: APIRouter) -> None:
    """Register identity routes to parent router.

    This function is called by the router registry to register
    all identity-related API endpoints.

    Args:
        parent_router: The parent APIRouter to register routes to
    """
    from contexts.identity.interfaces.user_api import router as users_router

    parent_router.include_router(
        users_router,
        prefix="/users",
        tags=["users"],
    )
