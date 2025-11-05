"""Database error classification and handling.

This module provides utilities to classify database errors and determine
if they are retryable or require immediate failure.
"""

import logging
from enum import Enum

from sqlalchemy.exc import (
    DatabaseError,
    DisconnectionError,
    IntegrityError,
    OperationalError,
    TimeoutError,
)

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of database errors."""

    TRANSIENT = "transient"  # Temporary errors that can be retried
    PERMANENT = "permanent"  # Permanent errors that shouldn't be retried
    TIMEOUT = "timeout"  # Timeout errors
    CONNECTION = "connection"  # Connection errors
    INTEGRITY = "integrity"  # Data integrity errors
    UNKNOWN = "unknown"  # Unknown error category


class DatabaseErrorClassifier:
    """Classifier for database errors.

    Analyzes exceptions to determine their category and whether
    they should be retried.
    """

    # Error messages that indicate transient errors
    TRANSIENT_PATTERNS = [
        "connection reset",
        "connection refused",
        "connection timeout",
        "connection timed out",
        "server closed the connection",
        "server has gone away",
        "lost connection",
        "broken pipe",
        "can't connect",
        "connection pool",
        "too many connections",
        "deadlock detected",
        "lock timeout",
        "could not serialize",
        "serialization failure",
        "connection already closed",
    ]

    # Error messages that indicate permanent errors
    PERMANENT_PATTERNS = [
        "permission denied",
        "access denied",
        "authentication failed",
        "unknown database",
        "syntax error",
        "column does not exist",
        "table does not exist",
        "relation does not exist",
        "constraint violation",
    ]

    @classmethod
    def classify(cls, error: Exception) -> ErrorCategory:
        """Classify a database error.

        Args:
            error: Exception to classify

        Returns:
            ErrorCategory indicating the type of error
        """
        # Check specific exception types
        if isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT

        if isinstance(error, DisconnectionError):
            return ErrorCategory.CONNECTION

        if isinstance(error, IntegrityError):
            return ErrorCategory.INTEGRITY

        if isinstance(error, OperationalError):
            # Operational errors can be either transient or permanent
            return cls._classify_operational_error(error)

        if isinstance(error, DatabaseError):
            # Generic database errors need message inspection
            return cls._classify_by_message(error)

        # Unknown error type
        return ErrorCategory.UNKNOWN

    @classmethod
    def _classify_operational_error(cls, error: OperationalError) -> ErrorCategory:
        """Classify an operational error.

        Args:
            error: OperationalError to classify

        Returns:
            ErrorCategory for the error
        """
        error_msg = str(error).lower()

        # Check for transient patterns
        for pattern in cls.TRANSIENT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.TRANSIENT

        # Check for permanent patterns
        for pattern in cls.PERMANENT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.PERMANENT

        # Default to transient for operational errors
        # (safer to retry than to fail immediately)
        return ErrorCategory.TRANSIENT

    @classmethod
    def _classify_by_message(cls, error: Exception) -> ErrorCategory:
        """Classify error by its message.

        Args:
            error: Exception to classify

        Returns:
            ErrorCategory for the error
        """
        error_msg = str(error).lower()

        # Check for transient patterns
        for pattern in cls.TRANSIENT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.TRANSIENT

        # Check for permanent patterns
        for pattern in cls.PERMANENT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.PERMANENT

        return ErrorCategory.UNKNOWN

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """Check if an error is retryable.

        Args:
            error: Exception to check

        Returns:
            True if the error can be retried
        """
        category = cls.classify(error)

        # Only retry transient, timeout, and connection errors
        retryable = category in {
            ErrorCategory.TRANSIENT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.CONNECTION,
        }

        if retryable:
            logger.warning(
                f"Retryable database error detected: {category.value} - {type(error).__name__}: {error}"
            )
        else:
            logger.error(
                f"Non-retryable database error: {category.value} - {type(error).__name__}: {error}"
            )

        return retryable

    @classmethod
    def should_reconnect(cls, error: Exception) -> bool:
        """Check if error requires connection reset.

        Args:
            error: Exception to check

        Returns:
            True if connection should be reset
        """
        category = cls.classify(error)
        return category in {ErrorCategory.CONNECTION, ErrorCategory.TRANSIENT}


def is_database_error_retryable(error: Exception) -> bool:
    """Convenience function to check if error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if error can be retried

    Example:
        ```python
        try:
            await session.execute(query)
        except Exception as e:
            if is_database_error_retryable(e):
                # Retry the operation
                pass
            else:
                # Fail immediately
                raise
        ```
    """
    return DatabaseErrorClassifier.is_retryable(error)
