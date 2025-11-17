"""User API Endpoints"""

from bento.core.ids import ID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas.user import UserCreate, UserList, UserResponse, UserUpdate
from contexts.identity.domain.models.user import User
from contexts.identity.infrastructure.repositories.user_repository_impl import UserRepository

router = APIRouter()


@router.get("/", response_model=UserList)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all users with pagination.

    Returns a paginated list of users.
    """
    repo = UserRepository(session)

    # Calculate offset
    offset = (page - 1) * page_size

    # Get users with database-level pagination
    users = await repo.list_paginated(limit=page_size, offset=offset)

    # Get total count
    total = await repo.total_count()

    return UserList(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new user.

    Creates a user and returns the created user data.
    Email must be unique.
    """
    repo = UserRepository(session)

    # Check if email already exists
    if await repo.email_exists(data.email):
        raise HTTPException(status_code=409, detail=f"User with email {data.email} already exists")

    # Create domain object
    user = User(
        id=str(ID.generate()),
        name=data.name,
        email=data.email,
    )

    # Save
    await repo.save(user)
    await session.commit()

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a user by ID.

    Returns user details or 404 if not found.
    """
    repo = UserRepository(session)
    user = await repo.find_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(
    email: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a user by email address.

    Returns user details or 404 if not found.
    """
    repo = UserRepository(session)
    user = await repo.find_by_email(email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update a user.

    Updates user fields and returns updated data.
    Email must be unique if changed.
    """
    repo = UserRepository(session)
    user = await repo.find_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check email uniqueness if changing
    if data.email and data.email != user.email:
        if await repo.email_exists(data.email):
            raise HTTPException(
                status_code=409, detail=f"User with email {data.email} already exists"
            )

    # Update fields
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email

    await repo.save(user)
    await session.commit()

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a user.

    Removes a user from the system.
    """
    repo = UserRepository(session)
    user = await repo.find_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await repo.delete(user)
    await session.commit()

    return None
