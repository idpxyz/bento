"""Database retry mechanisms.

This module provides utilities for retrying database operations
with exponential backoff and jitter.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from bento.infrastructure.database.resilience.errors import is_database_error_retryable

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        # Add jitter to avoid thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay


async def retry_on_db_error[T](
    func: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
    on_retry: Callable[[Exception, int], None] | None = None,
) -> T:
    """Retry an async function on database errors.

    Args:
        func: Async function to retry
        config: Retry configuration (uses default if None)
        on_retry: Optional callback called on each retry (error, attempt)

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail

    Example:
        ```python
        async def query_database():
            async with session.begin():
                result = await session.execute(select(User))
                return result.scalars().all()

        users = await retry_on_db_error(query_database)
        ```
    """
    if config is None:
        config = RetryConfig()

    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            return await func()

        except Exception as e:
            last_exception = e

            # Check if error is retryable
            if not is_database_error_retryable(e):
                logger.error(
                    f"Non-retryable database error on attempt {attempt + 1}/{config.max_attempts}: {e}"
                )
                raise

            # Check if we've exhausted retries
            if attempt >= config.max_attempts - 1:
                logger.error(
                    f"Max retry attempts ({config.max_attempts}) reached for database operation"
                )
                raise

            # Calculate delay
            delay = config.calculate_delay(attempt)

            logger.warning(
                f"Database error on attempt {attempt + 1}/{config.max_attempts}, "
                f"retrying in {delay:.2f}s: {type(e).__name__}: {e}"
            )

            # Call retry callback if provided
            if on_retry:
                on_retry(e, attempt + 1)

            # Wait before retrying
            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry loop completed without result or exception")


class RetryableOperation:
    """Context manager for retryable database operations.

    Example:
        ```python
        async with RetryableOperation(max_attempts=5) as retry:
            async with session.begin():
                result = await session.execute(query)
                return result
        ```
    """

    def __init__(self, config: RetryConfig | None = None):
        """Initialize retryable operation.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self._attempt = 0

    async def __aenter__(self):
        """Enter context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and handle retries."""
        if exc_type is None:
            # No error, operation successful
            return False

        # Check if error is retryable
        if not is_database_error_retryable(exc_val):
            # Non-retryable error, propagate
            return False

        # Check if we've exhausted retries
        if self._attempt >= self.config.max_attempts - 1:
            logger.error(f"Max retry attempts ({self.config.max_attempts}) reached")
            return False

        # Calculate delay and retry
        delay = self.config.calculate_delay(self._attempt)
        logger.warning(
            f"Retrying operation in {delay:.2f}s (attempt {self._attempt + 1}/{self.config.max_attempts})"
        )

        await asyncio.sleep(delay)
        self._attempt += 1

        # Suppress exception to retry
        return True


# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
)
