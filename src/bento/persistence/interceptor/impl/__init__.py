"""Standard interceptor implementations.

This module provides ready-to-use interceptors for common cross-cutting concerns:
- Audit: Automatic timestamp and user tracking
- Soft Delete: Logical deletion instead of physical deletion
- Optimistic Lock: Concurrency control via version numbers
"""

from .audit import AuditInterceptor
from .cache import CacheInterceptor
from .optimistic_lock import OptimisticLockException, OptimisticLockInterceptor
from .soft_delete import SoftDeleteInterceptor

__all__ = [
    # Audit
    "AuditInterceptor",
    # Soft Delete
    "SoftDeleteInterceptor",
    # Optimistic Lock
    "OptimisticLockInterceptor",
    "OptimisticLockException",
    # Cache
    "CacheInterceptor",
]
