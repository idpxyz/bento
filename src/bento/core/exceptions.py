"""Core exception system for Bento framework.

This module provides a structured exception hierarchy aligned with DDD layers,
with native support for Contracts-as-Code.

Example:
    ```python
    from bento.core.exceptions import DomainException

    # Simple - reason_code from contracts
    raise DomainException(reason_code="STATE_CONFLICT", shipment_id="123")

    # With custom message override
    raise DomainException("STATE_CONFLICT", message="Custom message")
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.contracts import ReasonCode


class ExceptionCategory(str, Enum):
    """Exception categories aligned with DDD layers."""

    DOMAIN = "domain"
    """Domain layer - business rule violations"""

    APPLICATION = "application"
    """Application layer - use case failures"""

    INFRASTRUCTURE = "infrastructure"
    """Infrastructure layer - technical failures (DB, cache, etc.)"""

    INTERFACE = "interface"
    """Interface layer - API/validation errors"""


# Global contract catalog reference
_global_catalog = None
_framework_catalog_loaded = False

# Global message renderer reference (optional i18n support)
_global_message_renderer = None


def _load_framework_catalog():
    """Load framework's built-in reason codes."""
    global _global_catalog, _framework_catalog_loaded
    if _framework_catalog_loaded:
        return

    try:
        import json
        from pathlib import Path

        # Load framework.json from bento/contracts/reason-codes/
        framework_json = (
            Path(__file__).parent.parent / "contracts" / "reason-codes" / "framework.json"
        )
        if framework_json.exists():
            from bento.contracts.catalogs import ReasonCodeCatalog

            doc = json.loads(framework_json.read_text(encoding="utf-8"))
            _global_catalog = ReasonCodeCatalog(doc)
            _framework_catalog_loaded = True
    except Exception:
        pass  # Silently fail if loading fails


def set_global_catalog(catalog) -> None:
    """Set the global reason code catalog.

    Called during application startup to enable contract-based exceptions.

    Args:
        catalog: ReasonCodeCatalog instance
    """
    global _global_catalog
    _global_catalog = catalog


def get_global_catalog():
    """Get the global reason code catalog."""
    return _global_catalog


def set_global_message_renderer(renderer) -> None:
    """Set the global message renderer for i18n support (Optional).

    Called during application startup to enable i18n support.
    If not set, exceptions will use default messages from contracts.

    Args:
        renderer: IMessageRenderer instance or None to clear

    Example:
        ```python
        from bento.core.i18n import set_global_message_renderer
        from myapp.i18n import MessageRenderer

        renderer = MessageRenderer(catalog)
        set_global_message_renderer(renderer)
        ```
    """
    global _global_message_renderer
    _global_message_renderer = renderer


def get_global_message_renderer():
    """Get the global message renderer.

    Returns:
        Registered IMessageRenderer instance or None
    """
    return _global_message_renderer


def _resolve_reason_code(code: str) -> ReasonCode | None:
    """Resolve a reason code from the global catalog."""
    # Auto-load framework catalog if not set
    if _global_catalog is None:
        _load_framework_catalog()
    if _global_catalog is None:
        return None
    return _global_catalog.get(code)


@dataclass
class BentoException(Exception):
    """Base exception for Bento framework.

    Supports two modes:
    1. Contract mode: Pass reason code string, metadata loaded from contracts
    2. Legacy mode: Pass explicit values for backward compatibility

    Example:
        ```python
        # Contract mode (recommended)
        raise BentoException(reason_code="UNKNOWN_ERROR", details={"info": "..."})

        # Legacy mode (backward compatible)
        raise BentoException(
            reason_code="CUSTOM_001",
            message="Custom error",
            http_status=500
        )
        ```
    """

    reason_code: str
    message: str = ""
    http_status: int = 500
    category: ExceptionCategory = ExceptionCategory.APPLICATION
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    cause: Exception | None = None

    def __post_init__(self):
        # Try to resolve from contracts
        rc = _resolve_reason_code(self.reason_code)
        contract_message = None
        if rc is not None:
            # Store contract message but don't set it yet
            contract_message = rc.message
            if self.http_status == 500:  # default value
                self.http_status = rc.http_status
            self.retryable = rc.retryable
            if hasattr(rc, "category") and rc.category:
                # Map category string to enum
                cat_map = {
                    "DOMAIN": ExceptionCategory.DOMAIN,
                    "APPLICATION": ExceptionCategory.APPLICATION,
                    "INFRASTRUCTURE": ExceptionCategory.INFRASTRUCTURE,
                    "INTERFACE": ExceptionCategory.INTERFACE,
                    "VALIDATION": ExceptionCategory.INTERFACE,
                    "CLIENT": ExceptionCategory.APPLICATION,
                }
                self.category = cat_map.get(rc.category, self.category)

        # Priority: explicit message > i18n renderer > contract message > reason_code
        if not self.message:
            # Try to render message with i18n (optional)
            if _global_message_renderer is not None:
                try:
                    # Import here to avoid circular dependency
                    from bento.core.i18n import LocaleContext

                    locale = LocaleContext.get()
                    fallback = contract_message or self.reason_code
                    self.message = _global_message_renderer.render(
                        self.reason_code, fallback, locale, **self.details
                    )
                except Exception as ex:
                    # Debug: log the exception
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"❌ BentoException i18n failed: {ex}", exc_info=True)
                    # Silently fall back if i18n rendering fails
                    pass

            # If i18n didn't work, use contract message or reason_code
            if not self.message:
                self.message = contract_message or self.reason_code

        # Set exception message
        super().__init__(self.message or self.reason_code)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "reason_code": self.reason_code,
            "message": self.message,
            "category": self.category.value,
            "details": self.details,
            "retryable": self.retryable,
        }


@dataclass
class DomainException(BentoException):
    """Domain layer exception - business rule violations.

    Example:
        ```python
        raise DomainException(reason_code="STATE_CONFLICT", current_state="DRAFT")
        ```
    """

    category: ExceptionCategory = field(default=ExceptionCategory.DOMAIN)


@dataclass
class ApplicationException(BentoException):
    """Application layer exception - use case failures.

    Example:
        ```python
        raise ApplicationException(reason_code="VALIDATION_FAILED", field="email")
        ```
    """

    category: ExceptionCategory = field(default=ExceptionCategory.APPLICATION)


@dataclass
class InfrastructureException(BentoException):
    """Infrastructure layer exception - technical failures.

    Example:
        ```python
        raise InfrastructureException(reason_code="DATABASE_ERROR", operation="query")
        ```
    """

    category: ExceptionCategory = field(default=ExceptionCategory.INFRASTRUCTURE)


@dataclass
class InterfaceException(BentoException):
    """Interface layer exception - API/validation errors.

    Example:
        ```python
        raise InterfaceException(reason_code="INVALID_PARAMS", missing_field="customer_id")
        ```
    """

    category: ExceptionCategory = field(default=ExceptionCategory.INTERFACE)
