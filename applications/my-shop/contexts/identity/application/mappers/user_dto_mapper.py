"""User DTO Mapper - Smart Automation! 🤖

Uses Bento's AutoMapper with minimal configuration:
- ✅ id: ID → str (automatic)
- ✅ name, email: direct mapping (automatic)

Compare:
Before: 15+ lines of manual mapping + error-prone field iteration
After:  4 lines total! 🎊
"""

from bento.application.dto.auto_mapper import AutoMapper

from contexts.identity.application.dto.user_dto import UserDTO
from contexts.identity.domain.models.user import User


class UserDTOMapper(AutoMapper[User, UserDTO]):
    """User DTO Mapper - Smart Automation! 🤖"""

    def __init__(self):
        super().__init__(User, UserDTO)
        # No custom mappings needed - all fields map directly!
