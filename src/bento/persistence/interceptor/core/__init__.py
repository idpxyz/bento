"""Interceptor core components.

This module provides the foundation for the interceptor pattern:
- Base interceptor class
- Interceptor chain for execution management
- Type definitions
- Metadata registry
"""

from .base import Interceptor, InterceptorChain
from .metadata import EntityMetadataRegistry
from .types import InterceptorContext, InterceptorPriority, OperationType

__all__ = [
    # Base classes
    "Interceptor",
    "InterceptorChain",
    # Types
    "InterceptorContext",
    "InterceptorPriority",
    "OperationType",
    # Metadata
    "EntityMetadataRegistry",
]

