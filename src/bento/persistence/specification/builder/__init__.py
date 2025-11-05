"""Specification builders for fluent query construction.

This module provides builder classes for constructing specifications
with a clean, fluent API.
"""

from .aggregate import AggregateSpecificationBuilder
from .base import SpecificationBuilder
from .entity import EntitySpecificationBuilder

__all__ = [
    "SpecificationBuilder",
    "EntitySpecificationBuilder",
    "AggregateSpecificationBuilder",
]
