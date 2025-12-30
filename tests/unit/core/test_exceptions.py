"""
Unit tests for Bento Exception system with Contracts-as-Code.
"""
import pytest
from bento.core.exceptions import (
    BentoException,
    DomainException,
    ApplicationException,
    InfrastructureException,
    InterfaceException,
    ExceptionCategory,
    set_global_catalog,
    get_global_catalog,
)
from bento.contracts import ReasonCodeCatalog


class TestBentoExceptionWithContracts:
    """Tests for contract-based exceptions."""

    @pytest.fixture
    def catalog(self):
        """Create a test catalog."""
        doc = {
            "reason_codes": [
                {
                    "reason_code": "STATE_CONFLICT",
                    "message": "Operation not allowed in current state",
                    "http_status": 409,
                    "category": "DOMAIN",
                    "retryable": False,
                },
                {
                    "reason_code": "VALIDATION_FAILED",
                    "message": "Validation failed",
                    "http_status": 400,
                    "category": "VALIDATION",
                    "retryable": False,
                },
                {
                    "reason_code": "DATABASE_ERROR",
                    "message": "Database operation failed",
                    "http_status": 500,
                    "category": "INFRASTRUCTURE",
                    "retryable": True,
                },
            ]
        }
        return ReasonCodeCatalog(doc)

    @pytest.fixture(autouse=True)
    def setup_catalog(self, catalog):
        """Setup and teardown global catalog."""
        set_global_catalog(catalog)
        yield
        set_global_catalog(None)

    def test_domain_exception_from_contract(self):
        """Should create exception with metadata from contract."""
        exc = DomainException(reason_code="STATE_CONFLICT")

        assert exc.reason_code == "STATE_CONFLICT"
        assert exc.message == "Operation not allowed in current state"
        assert exc.http_status == 409
        assert exc.retryable is False
        assert exc.category == ExceptionCategory.DOMAIN

    def test_exception_with_details(self):
        """Should include custom details."""
        exc = DomainException(
            reason_code="STATE_CONFLICT",
            details={"order_id": "123", "current_state": "DRAFT"}
        )

        assert exc.details["order_id"] == "123"
        assert exc.details["current_state"] == "DRAFT"

    def test_exception_message_override(self):
        """Should allow message override."""
        exc = DomainException(reason_code="STATE_CONFLICT", message="Custom message")

        assert exc.message == "Custom message"
        assert exc.http_status == 409  # Still from contract

    def test_application_exception(self):
        """Should create application exception."""
        exc = ApplicationException(reason_code="VALIDATION_FAILED")

        assert exc.reason_code == "VALIDATION_FAILED"
        assert exc.category == ExceptionCategory.INTERFACE  # Mapped from VALIDATION

    def test_infrastructure_exception(self):
        """Should create infrastructure exception."""
        exc = InfrastructureException(reason_code="DATABASE_ERROR")

        assert exc.reason_code == "DATABASE_ERROR"
        assert exc.retryable is True
        assert exc.category == ExceptionCategory.INFRASTRUCTURE

    def test_interface_exception(self):
        """Should create interface exception."""
        exc = InterfaceException(
            reason_code="INVALID_PARAMS",
            message="Missing required field",
            http_status=400,
        )

        assert exc.reason_code == "INVALID_PARAMS"
        assert exc.message == "Missing required field"
        assert exc.http_status == 400
        assert exc.category == ExceptionCategory.INTERFACE

    def test_base_bento_exception(self):
        """Should create base exception with explicit values."""
        exc = BentoException(
            reason_code="CUSTOM_CODE",
            message="Custom message",
            http_status=418,
            details={"key": "value"},
        )

        assert exc.reason_code == "CUSTOM_CODE"
        assert exc.message == "Custom message"
        assert exc.http_status == 418
        assert exc.details["key"] == "value"
        assert exc.category == ExceptionCategory.APPLICATION  # default

    def test_exception_with_cause(self):
        """Should capture cause exception."""
        original = ValueError("original error")
        exc = InfrastructureException(
            reason_code="DATABASE_ERROR",
            cause=original,
        )

        assert exc.cause is original

    def test_to_dict(self):
        """Should convert to dictionary."""
        exc = DomainException(
            reason_code="STATE_CONFLICT",
            details={"order_id": "123"}
        )

        result = exc.to_dict()

        assert result["reason_code"] == "STATE_CONFLICT"
        assert result["message"] == "Operation not allowed in current state"
        assert result["category"] == "domain"
        assert result["details"]["order_id"] == "123"
        assert result["retryable"] is False

    def test_exception_without_catalog(self):
        """Should work without catalog (fallback mode)."""
        set_global_catalog(None)

        exc = DomainException(
            reason_code="CUSTOM_ERROR",
            message="Custom error message",
            http_status=422,
        )

        assert exc.reason_code == "CUSTOM_ERROR"
        assert exc.message == "Custom error message"
        assert exc.http_status == 422

    def test_get_global_catalog(self, catalog):
        """Should return the global catalog."""
        result = get_global_catalog()

        assert result is not None
        assert result is catalog
        assert result.get("STATE_CONFLICT") is not None

    def test_get_global_catalog_when_not_set(self):
        """Should return None when catalog not set."""
        set_global_catalog(None)

        result = get_global_catalog()

        assert result is None
