"""Category DTO Mapper - Using Bento AutoMapper! 🎉"""

from bento.application.dto.auto_mapper import AutoMapper

from contexts.catalog.application.dto import CategoryDTO
from contexts.catalog.domain.models.category import Category


class CategoryDTOMapper(AutoMapper[Category, CategoryDTO]):
    """Category DTO Mapper - Smart Automation! 🤖

    Uses Bento's AutoMapper with custom logic only where needed:
    - ✅ id, parent_id: ID → str (automatic)
    - ✅ name, description: direct mapping (automatic)
    - ✅ is_root: method call (custom override)

    Compare:
    Before: 25+ lines of manual mapping + error-prone field iteration
    After:  6 lines total! 🎊
    """

    def __init__(self):
        super().__init__(Category, CategoryDTO)
        # Custom mapping only for method calls
        self.field_mappings = {
            "is_root": lambda category: category.is_root()  # Method → bool
        }
