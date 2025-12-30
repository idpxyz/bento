"""Category mappers for DTO → Response conversion."""

from functools import lru_cache

from bento.application.dto import PydanticResponseMapper

from contexts.catalog.application.dto.category_dto import CategoryDTO
from contexts.catalog.domain.models.category import Category
from contexts.catalog.interfaces.dto.category_responses import CategoryResponse


@lru_cache(maxsize=1)
def _get_response_mapper() -> PydanticResponseMapper[CategoryDTO, CategoryResponse]:
    """Get or create CategoryResponseMapper singleton."""
    return PydanticResponseMapper(CategoryDTO, CategoryResponse)


def category_to_response(category: Category | CategoryDTO) -> CategoryResponse:
    """Convert Category (domain or DTO) to CategoryResponse."""
    if isinstance(category, Category):
        dto = CategoryDTO(
            id=str(category.id),
            name=category.name,
            description=category.description,
            parent_id=str(category.parent_id) if category.parent_id else None,
            is_root=category.is_root(),
        )
        return _get_response_mapper().to_response(dto)
    else:
        return _get_response_mapper().to_response(category)
