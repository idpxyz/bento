"""Data Transfer Objects for Application Layer.

This module provides base classes and utilities for DTOs used in the Application layer.

Key Features:
- BaseDTO: Standard base class with JSON serialization and validation
- ListDTO: Standard list response with pagination support
- ErrorDTO: Consistent error response format
"""

from bento.application.dto.base import (
    BaseDTO,
    CreatedDTO,
    DeletedDTO,
    ErrorDTO,
    ListDTO,
    UpdatedDTO,
)
from bento.application.dto.mapper import BaseDTOMapper, DTOMapper

__all__ = [
    "BaseDTO",  # Base class for all DTOs
    "ListDTO",  # Standard list response DTO
    "ErrorDTO",  # Standard error response DTO
    "CreatedDTO",
    "UpdatedDTO",
    "DeletedDTO",
    "DTOMapper",
    "BaseDTOMapper",
]
