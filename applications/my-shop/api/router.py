"""API Router - Aggregate all routes here"""

from fastapi import APIRouter

from api.orders import router as orders_router
from api.products import router as products_router
from api.users import router as users_router

# Create main API router
api_router = APIRouter()


@api_router.get("/ping")
async def ping():
    """Ping endpoint for testing"""
    return {"message": "pong"}


@api_router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "my-shop"}


# Include domain-specific routers
api_router.include_router(
    products_router,
    prefix="/products",
    tags=["products"],
)
api_router.include_router(
    orders_router,
    prefix="/orders",
    tags=["orders"],
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
)
