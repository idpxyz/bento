"""Unit tests for ApplicationService."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from bento.application.services.application_service import (
    ApplicationService,
    ApplicationServiceResult,
)


@dataclass
class MockCommand:
    """Mock command for testing."""

    name: str
    value: int = 0


@dataclass
class MockResult:
    """Mock result for testing."""

    id: str
    name: str
    success: bool = True


class MockApplicationService(ApplicationService[MockCommand, MockResult]):
    """Mock application service for testing."""

    def __init__(self, uow):
        super().__init__(uow)
        self.handle_called = False
        self.handle_result = MockResult("test-id", "test-result")
        self.should_raise = False

    async def handle(self, command: MockCommand) -> MockResult:
        """Mock handle implementation."""
        self.handle_called = True
        if self.should_raise:
            raise ValueError("Test error")
        return self.handle_result


class TestApplicationService:
    """Test suite for ApplicationService."""

    @pytest.fixture
    def mock_uow(self):
        """Create mock UoW."""
        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def service(self, mock_uow):
        """Create test service."""
        return MockApplicationService(mock_uow)

    @pytest.mark.asyncio
    async def test_execute_success(self, service):
        """Test successful execution."""
        command = MockCommand("test", 42)

        result = await service.execute(command)

        print(f"DEBUG: result = {result}")
        print(f"DEBUG: result.is_success = {result.is_success}")
        print(f"DEBUG: result.data = {result.data}")
        print(f"DEBUG: result.error = {result.error}")
        print(f"DEBUG: service.handle_called = {service.handle_called}")

        assert isinstance(result, ApplicationServiceResult)
        assert result.is_success is True
        assert result.data is not None
        assert result.data.name == "test-result"
        assert result.error is None
        assert service.handle_called is True

    @pytest.mark.asyncio
    async def test_execute_with_error(self, service):
        """Test execution with error."""
        service.should_raise = True
        command = MockCommand("test", 42)

        result = await service.execute(command)

        assert isinstance(result, ApplicationServiceResult)
        assert result.is_success is False
        assert result.data is None
        assert result.error is not None
        assert "Test error" in str(result.error)

    @pytest.mark.asyncio
    async def test_uow_transaction_success(self, service, mock_uow):
        """Test UoW transaction is used correctly."""
        command = MockCommand("test", 42)

        await service.execute(command)

        # Verify UoW context manager was used
        mock_uow.__aenter__.assert_called_once()
        mock_uow.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_uow_transaction_with_error(self, service, mock_uow):
        """Test UoW transaction handles errors correctly."""
        service.should_raise = True
        command = MockCommand("test", 42)

        await service.execute(command)

        # Verify UoW context manager was used even with error
        mock_uow.__aenter__.assert_called_once()
        mock_uow.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_called(self, service):
        """Test that validation is called."""
        # Override validate method to track calls
        validate_called = False

        async def mock_validate(cmd):
            nonlocal validate_called
            validate_called = True

        service.validate = mock_validate
        command = MockCommand("test", 42)

        await service.execute(command)

        assert validate_called is True

    @pytest.mark.asyncio
    async def test_command_none_validation(self, service):
        """Test validation fails with None command."""
        result = await service.execute(None)
        assert result.is_success is False
        assert "Command cannot be None" in result.error

    @pytest.mark.asyncio
    async def test_result_structure(self, service):
        """Test ApplicationServiceResult structure."""
        command = MockCommand("test", 42)
        result = await service.execute(command)

        # Test success result structure
        assert hasattr(result, "is_success")
        assert hasattr(result, "data")
        assert hasattr(result, "error")
        assert result.is_success is True
        assert result.data.id == "test-id"

        # Test error result structure
        service.should_raise = True
        error_result = await service.execute(command)
        assert error_result.is_success is False
        assert error_result.data is None
        assert error_result.error is not None


class TestApplicationServiceResult:
    """Test suite for ApplicationServiceResult."""

    def test_success_result(self):
        """Test creating success result."""
        data = MockResult("123", "success")
        result = ApplicationServiceResult.success(data)

        assert result.is_success is True
        assert result.data == data
        assert result.error is None

    def test_error_result(self):
        """Test creating error result."""
        error_msg = "Test error"
        result = ApplicationServiceResult.failure(error_msg)

        assert result.is_success is False
        assert result.data is None
        assert result.error == error_msg

    def test_result_equality(self):
        """Test result equality."""
        data = MockResult("123", "test")
        result1 = ApplicationServiceResult.success(data)
        result2 = ApplicationServiceResult.success(data)

        assert result1.is_success == result2.is_success
        assert result1.data == result2.data

    def test_result_string_representation(self):
        """Test result string representation."""
        data = MockResult("123", "test")
        success_result = ApplicationServiceResult.success(data)
        error_result = ApplicationServiceResult.failure("Error message")

        success_str = str(success_result)
        error_str = str(error_result)

        assert "ApplicationServiceResult" in success_str
        assert "ApplicationServiceResult" in error_str
