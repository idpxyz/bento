"""Data Transfer Objects for Application Layer.

This module provides base classes and utilities for DTOs used in the Application layer.

Key Features:
- BaseDTO: Standard base class with JSON serialization and validation
- ListDTO: Standard list response with pagination support
- ErrorDTO: Consistent error response format
- AutoMapper: Intelligent automatic mapping from Domain to DTO
- PydanticResponseMapper: Generic DTO to Response Model conversion
"""

from bento.application.dto.auto_mapper import AutoMapper, auto_mapper
from bento.application.dto.base import (
    BaseDTO,
    CreatedDTO,
    DeletedDTO,
    ErrorDTO,
    ListDTO,
    UpdatedDTO,
)
from bento.application.dto.mapper import BaseDTOMapper, DTOMapper
from bento.application.dto.response_mapper import (
    PydanticResponseMapper,
    ResponseMapper,
)

__all__ = [
    # Base DTOs
    "BaseDTO",
    "ListDTO",
    "ErrorDTO",
    "CreatedDTO",
    "UpdatedDTO",
    "DeletedDTO",
    # Mappers
    "DTOMapper",
    "BaseDTOMapper",
    "AutoMapper",
    "auto_mapper",
    "ResponseMapper",
    "PydanticResponseMapper",
]
