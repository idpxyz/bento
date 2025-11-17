"""Product API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas.product import ProductCreate, ProductList, ProductResponse, ProductUpdate
from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.repositories.product_repository import ProductRepository

router = APIRouter()


@router.get("/", response_model=ProductList)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all products with pagination.

    Returns a paginated list of products.
    """
    repo = ProductRepository(session)

    # Calculate offset
    offset = (page - 1) * page_size

    # Get products (you'll need to add pagination support to repository)
    # For now, simple implementation
    products = await repo.list()  # Assuming list() method exists

    # Apply pagination in memory (should be done in repository/database)
    total = len(products)
    paginated_products = products[offset : offset + page_size]

    return ProductList(
        items=[ProductResponse.model_validate(p) for p in paginated_products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new product.

    Creates a product and returns the created product data.
    """
    repo = ProductRepository(session)

    # Create domain object
    product = Product(
        id=None,  # Will be generated
        name=data.name,
        description=data.description,
        price=data.price,
        stock=data.stock,
        category_id=data.category_id,
    )

    # Save
    await repo.save(product)
    await session.commit()

    return ProductResponse.model_validate(product)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a product by ID.

    Returns product details or 404 if not found.
    """
    repo = ProductRepository(session)
    product = await repo.find_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update a product.

    Updates product fields and returns updated data.
    """
    repo = ProductRepository(session)
    product = await repo.find_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update fields
    if data.name is not None:
        product.name = data.name
    if data.description is not None:
        product.description = data.description
    if data.price is not None:
        product.price = data.price
    if data.stock is not None:
        product.stock = data.stock
    if data.category_id is not None:
        product.category_id = data.category_id

    await repo.save(product)
    await session.commit()

    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a product.

    Removes a product from the system.
    """
    repo = ProductRepository(session)
    product = await repo.find_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await repo.delete(product)
    await session.commit()

    return None
