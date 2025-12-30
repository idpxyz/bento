"""User mappers for DTO → Response conversion.

Uses Bento's PydanticResponseMapper for automatic conversion.
"""

from functools import lru_cache

from bento.application.dto import PydanticResponseMapper

from contexts.identity.application.dto.user_dto import UserDTO
from contexts.identity.domain.models.user import User
from contexts.identity.interfaces.dto.user_responses import UserResponse


@lru_cache(maxsize=1)
def _get_response_mapper() -> PydanticResponseMapper[UserDTO, UserResponse]:
    """Get or create UserResponseMapper singleton."""
    return PydanticResponseMapper(UserDTO, UserResponse)


def user_to_response(user: User | UserDTO) -> UserResponse:
    """Convert User (domain or DTO) to UserResponse.

    Handles both domain objects and DTOs automatically.
    Uses lazy-initialized singleton mapper for performance.

    Args:
        user: Either a domain User or UserDTO

    Returns:
        Interface layer UserResponse
    """
    if isinstance(user, User):
        # Domain → DTO → Response
        dto = UserDTO(
            id=str(user.id),
            name=user.name,
            email=user.email,
        )
        return _get_response_mapper().to_response(dto)
    else:
        # DTO → Response
        return _get_response_mapper().to_response(user)
