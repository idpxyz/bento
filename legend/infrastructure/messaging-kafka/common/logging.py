import logging
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor

from idp.framework.infrastructure.messaging.config.settings import get_settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    """
    settings = get_settings()

    # Set log level
    log_level = getattr(logging, settings.app.log_level.upper())

    # Configure processors based on environment
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Add environment-specific processors
    if settings.app.environment.lower() in ("development", "local"):
        # Pretty printing for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON for production
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger with the given name.

    Args:
        name (str): Logger name

    Returns:
        structlog.stdlib.BoundLogger: Structured logger
    """
    return structlog.get_logger(name)


class LoggerContext:
    """
    Context manager for adding context to logs.
    """

    def __init__(self, **context: Any) -> None:
        self.context = context
        self.token = None

    def __enter__(self) -> "LoggerContext":
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, *args: Any) -> None:
        if self.token:
            structlog.contextvars.unbind_contextvars(self.token)


def with_context(func: Any) -> Any:
    """
    Decorator to add function arguments as context to logs.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract function arguments
        context: Dict[str, Any] = {}

        # Add kwargs to context
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                context[key] = value

        # Execute function with context
        with LoggerContext(**context):
            return func(*args, **kwargs)

    return wrapper
