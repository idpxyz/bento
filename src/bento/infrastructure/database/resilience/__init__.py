"""Database resilience features.

This package contains error handling, retry mechanisms, and fault tolerance
for database operations.
"""

from bento.infrastructure.database.resilience.errors import (
    DatabaseErrorClassifier,
    ErrorCategory,
    is_database_error_retryable,
)
from bento.infrastructure.database.resilience.retry import (
    DEFAULT_RETRY_CONFIG,
    RetryableOperation,
    RetryConfig,
    retry_on_db_error,
)

__all__ = [
    # Error classification
    "DatabaseErrorClassifier",
    "ErrorCategory",
    "is_database_error_retryable",
    # Retry mechanisms
    "RetryConfig",
    "RetryableOperation",
    "retry_on_db_error",
    "DEFAULT_RETRY_CONFIG",
]
