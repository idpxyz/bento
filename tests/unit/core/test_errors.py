"""Unit tests for error handling system."""

import pytest

from bento.core.errors import (
    ApplicationException,
    BentoException,
    DomainException,
    ErrorCategory,
    ErrorCode,
    InfrastructureException,
    InterfaceException,
)


class TestErrorCode:
    """Test suite for ErrorCode."""

    def test_error_code_creation(self):
        """Test creating an error code."""
        error = ErrorCode(
            code="TEST_001",
            message="Test error message",
            http_status=404,
        )

        assert error.code == "TEST_001"
        assert error.message == "Test error message"
        assert error.http_status == 404

    def test_error_code_default_http_status(self):
        """Test error code with default HTTP status."""
        error = ErrorCode(
            code="TEST_002",
            message="Server error",
        )

        assert error.http_status == 500

    def test_error_code_immutability(self):
        """Test that error codes are immutable."""
        error = ErrorCode(code="TEST_003", message="Test")

        # dataclass(frozen=True) raises FrozenInstanceError on mutation
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            error.code = "NEW_CODE"


class TestErrorCategory:
    """Test suite for ErrorCategory."""

    def test_error_categories_exist(self):
        """Test that all expected categories exist."""
        assert ErrorCategory.DOMAIN == "domain"
        assert ErrorCategory.APPLICATION == "application"
        assert ErrorCategory.INFRASTRUCTURE == "infrastructure"
        assert ErrorCategory.INTERFACE == "interface"

    def test_error_category_is_enum(self):
        """Test that ErrorCategory is an Enum."""
        from enum import Enum

        assert issubclass(ErrorCategory, Enum)


class TestBentoException:
    """Test suite for BentoException."""

    def test_exception_creation(self):
        """Test creating a BentoException."""
        error_code = ErrorCode(code="TEST_001", message="Test error")
        exc = BentoException(
            error_code=error_code,
            category=ErrorCategory.DOMAIN,
            details={"key": "value"},
        )

        assert exc.error_code == error_code
        assert exc.category == ErrorCategory.DOMAIN
        assert exc.details == {"key": "value"}
        assert str(exc) == "Test error"

    def test_exception_with_cause(self):
        """Test exception chaining with cause."""
        original_error = ValueError("Original error")
        error_code = ErrorCode(code="TEST_002", message="Wrapped error")

        exc = BentoException(
            error_code=error_code,
            category=ErrorCategory.INFRASTRUCTURE,
            cause=original_error,
        )

        assert exc.__cause__ == original_error

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error_code = ErrorCode(
            code="TEST_003",
            message="Test error",
            http_status=400,
        )
        exc = BentoException(
            error_code=error_code,
            category=ErrorCategory.DOMAIN,
            details={"field": "email", "reason": "invalid"},
        )

        result = exc.to_dict()

        assert result == {
            "code": "TEST_003",
            "message": "Test error",
            "category": "domain",
            "details": {"field": "email", "reason": "invalid"},
        }

    def test_exception_without_details(self):
        """Test exception without details defaults to empty dict."""
        error_code = ErrorCode(code="TEST_004", message="Test")
        exc = BentoException(
            error_code=error_code,
            category=ErrorCategory.APPLICATION,
        )

        assert exc.details == {}

    def test_exception_can_be_raised(self):
        """Test that exception can be raised and caught."""
        error_code = ErrorCode(code="TEST_005", message="Raised error")

        with pytest.raises(BentoException) as exc_info:
            raise BentoException(
                error_code=error_code,
                category=ErrorCategory.DOMAIN,
            )

        assert exc_info.value.error_code == error_code


class TestDomainException:
    """Test suite for DomainException."""

    def test_domain_exception_creation(self):
        """Test creating a domain exception."""
        error_code = ErrorCode(code="DOMAIN_001", message="Domain rule violated")
        exc = DomainException(
            error_code=error_code,
            details={"aggregate": "Order"},
        )

        assert isinstance(exc, BentoException)
        assert exc.category == ErrorCategory.DOMAIN
        assert exc.error_code == error_code
        assert exc.details == {"aggregate": "Order"}

    def test_domain_exception_auto_category(self):
        """Test that domain exception automatically sets domain category."""
        error_code = ErrorCode(code="DOMAIN_002", message="Test")
        exc = DomainException(error_code=error_code)

        assert exc.category == ErrorCategory.DOMAIN

    def test_domain_exception_inheritance(self):
        """Test that DomainException is a BentoException."""
        error_code = ErrorCode(code="DOMAIN_003", message="Test")
        exc = DomainException(error_code=error_code)

        assert isinstance(exc, BentoException)


class TestApplicationException:
    """Test suite for ApplicationException."""

    def test_application_exception_creation(self):
        """Test creating an application exception."""
        error_code = ErrorCode(code="APP_001", message="Use case failed")
        exc = ApplicationException(
            error_code=error_code,
            details={"use_case": "CreateOrder"},
        )

        assert exc.category == ErrorCategory.APPLICATION
        assert exc.error_code == error_code

    def test_application_exception_auto_category(self):
        """Test that application exception automatically sets application category."""
        error_code = ErrorCode(code="APP_002", message="Test")
        exc = ApplicationException(error_code=error_code)

        assert exc.category == ErrorCategory.APPLICATION


class TestInfrastructureException:
    """Test suite for InfrastructureException."""

    def test_infrastructure_exception_creation(self):
        """Test creating an infrastructure exception."""
        error_code = ErrorCode(code="INFRA_001", message="Database error")
        original = ValueError("Connection lost")

        exc = InfrastructureException(
            error_code=error_code,
            details={"database": "postgres"},
            cause=original,
        )

        assert exc.category == ErrorCategory.INFRASTRUCTURE
        assert exc.__cause__ == original

    def test_infrastructure_exception_auto_category(self):
        """Test that infrastructure exception automatically sets infrastructure category."""
        error_code = ErrorCode(code="INFRA_002", message="Test")
        exc = InfrastructureException(error_code=error_code)

        assert exc.category == ErrorCategory.INFRASTRUCTURE


class TestInterfaceException:
    """Test suite for InterfaceException."""

    def test_interface_exception_creation(self):
        """Test creating an interface exception."""
        error_code = ErrorCode(code="API_001", message="Invalid request")
        exc = InterfaceException(
            error_code=error_code,
            details={"missing_field": "email"},
        )

        assert exc.category == ErrorCategory.INTERFACE
        assert exc.error_code == error_code

    def test_interface_exception_auto_category(self):
        """Test that interface exception automatically sets interface category."""
        error_code = ErrorCode(code="API_002", message="Test")
        exc = InterfaceException(error_code=error_code)

        assert exc.category == ErrorCategory.INTERFACE


class TestExceptionHierarchy:
    """Test suite for exception hierarchy."""

    def test_all_exceptions_inherit_from_bento(self):
        """Test that all exceptions inherit from BentoException."""
        error_code = ErrorCode(code="TEST", message="Test")

        exceptions = [
            DomainException(error_code=error_code),
            ApplicationException(error_code=error_code),
            InfrastructureException(error_code=error_code),
            InterfaceException(error_code=error_code),
        ]

        for exc in exceptions:
            assert isinstance(exc, BentoException)
            assert isinstance(exc, Exception)

    def test_category_assignment(self):
        """Test that each exception type has the correct category."""
        error_code = ErrorCode(code="TEST", message="Test")

        assert DomainException(error_code=error_code).category == ErrorCategory.DOMAIN
        assert ApplicationException(error_code=error_code).category == ErrorCategory.APPLICATION
        assert (
            InfrastructureException(error_code=error_code).category == ErrorCategory.INFRASTRUCTURE
        )
        assert InterfaceException(error_code=error_code).category == ErrorCategory.INTERFACE
