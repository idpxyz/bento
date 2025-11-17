"""API Router - Aggregate all routes here"""
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()


@api_router.get("/ping")
async def ping():
    """Ping endpoint for testing"""
    return {"message": "pong"}


# TODO: Include module-specific routers
# Example:
# from api.users import router as users_router
# api_router.include_router(users_router, prefix="/users", tags=["users"])
#
# from api.products import router as products_router
# api_router.include_router(products_router, prefix="/products", tags=["products"])