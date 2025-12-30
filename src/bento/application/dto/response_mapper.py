"""Response Mapper - Generic DTO to Response Model conversion.

This module provides a unified way to convert Application DTOs to Interface Response Models.
Uses Pydantic's model_validate for efficient, type-safe conversion.

This is the standard pattern for all Bento applications:
1. Domain → DTO (using AutoMapper in application layer)
2. DTO → Response (using ResponseMapper in interface layer)
"""

from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from bento.application.dto.base import BaseDTO

DTO = TypeVar("DTO", bound=BaseDTO)
Response = TypeVar("Response", bound=BaseModel)


class ResponseMapper(Protocol[DTO, Response]):
    """Protocol for DTO → Response conversion.

    Defines the contract for converting Application DTOs to Interface Response Models.
    """

    def to_response(self, dto: DTO) -> Response:
        """Convert DTO to Response model.

        Args:
            dto: Application layer DTO

        Returns:
            Interface layer Response model
        """
        ...

    def to_response_list(self, dtos: list[DTO]) -> list[Response]:
        """Convert list of DTOs to Response models.

        Args:
            dtos: List of Application layer DTOs

        Returns:
            List of Interface layer Response models
        """
        ...


class PydanticResponseMapper(Generic[DTO, Response]):
    """Generic Response Mapper using Pydantic's model_validate.

    Since both DTO and Response are Pydantic models with identical or compatible fields,
    we can use Pydantic's built-in conversion which is fast and type-safe.

    Usage:
        ```python
        # In interfaces/mappers/order_mappers.py
        from bento.application.dto.response_mapper import PydanticResponseMapper
        from contexts.ordering.application.dto import OrderDTO
        from contexts.ordering.interfaces.dto import OrderResponse

        class OrderResponseMapper(PydanticResponseMapper[OrderDTO, OrderResponse]):
            def __init__(self):
                super().__init__(OrderDTO, OrderResponse)

        # Use it
        mapper = OrderResponseMapper()
        response = mapper.to_response(dto)
        responses = mapper.to_response_list(dtos)
        ```
    """

    def __init__(self, dto_class: type[DTO], response_class: type[Response]):
        """Initialize mapper with DTO and Response classes.

        Args:
            dto_class: Application layer DTO class
            response_class: Interface layer Response class
        """
        self.dto_class = dto_class
        self.response_class = response_class

    def to_response(self, dto: DTO) -> Response:
        """Convert DTO to Response using Pydantic's model_validate.

        Args:
            dto: Application layer DTO

        Returns:
            Interface layer Response model
        """
        return self.response_class.model_validate(dto.model_dump())

    def to_response_list(self, dtos: list[DTO]) -> list[Response]:
        """Convert list of DTOs to Response models.

        Args:
            dtos: List of Application layer DTOs

        Returns:
            List of Interface layer Response models
        """
        return [self.to_response(dto) for dto in dtos]

    def to_response_optional(self, dto: DTO | None) -> Response | None:
        """Convert optional DTO to Response model.

        Args:
            dto: Optional Application layer DTO

        Returns:
            Response model if dto exists, None otherwise
        """
        return self.to_response(dto) if dto is not None else None


__all__ = [
    "ResponseMapper",
    "PydanticResponseMapper",
]
