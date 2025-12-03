"""Tests for CQRS decorators."""

from dataclasses import dataclass

import pytest

from bento.application import CommandHandler, QueryHandler, command_handler, query_handler
from bento.application.decorators import (
    get_handler_type,
    get_registered_handlers,
    is_handler,
)
from bento.application.ports.uow import UnitOfWork


# Test fixtures
@dataclass
class TestCommand:
    """Test command."""

    value: str


@dataclass
class TestQuery:
    """Test query."""

    value: str


# Test handlers
@command_handler
class TestCommandHandler(CommandHandler[TestCommand, str]):
    """Test command handler."""

    async def handle(self, command: TestCommand) -> str:
        """Handle test command."""
        return f"command:{command.value}"


@query_handler
class TestQueryHandler(QueryHandler[TestQuery, str]):
    """Test query handler."""

    async def handle(self, query: TestQuery) -> str:
        """Handle test query."""
        return f"query:{query.value}"


# Non-decorated handler for comparison
class NonDecoratedHandler(CommandHandler[TestCommand, str]):
    """Non-decorated handler."""

    async def handle(self, command: TestCommand) -> str:
        """Handle test command."""
        return "non-decorated"


class TestCommandHandlerDecorator:
    """Tests for @command_handler decorator."""

    def test_decorator_adds_metadata(self):
        """Test that decorator adds handler metadata."""
        assert hasattr(TestCommandHandler, "__handler_type__")
        assert hasattr(TestCommandHandler, "__is_handler__")
        assert TestCommandHandler.__handler_type__ == "command"
        assert TestCommandHandler.__is_handler__ is True

    def test_decorator_validates_inheritance(self):
        """Test that decorator validates CommandHandler inheritance."""
        with pytest.raises(TypeError, match="must inherit from CommandHandler"):

            @command_handler
            class BadHandler:
                """Not a CommandHandler."""

                pass

    def test_handler_registration(self):
        """Test that decorator registers handler."""
        handlers = get_registered_handlers()
        assert "TestCommandHandler" in handlers["commands"]
        assert handlers["commands"]["TestCommandHandler"] is TestCommandHandler

    def test_is_handler_function(self):
        """Test is_handler() helper function."""
        assert is_handler(TestCommandHandler) is True
        assert is_handler(NonDecoratedHandler) is False

    def test_get_handler_type_function(self):
        """Test get_handler_type() helper function."""
        assert get_handler_type(TestCommandHandler) == "command"
        assert get_handler_type(NonDecoratedHandler) is None


class TestQueryHandlerDecorator:
    """Tests for @query_handler decorator."""

    def test_decorator_adds_metadata(self):
        """Test that decorator adds handler metadata."""
        assert hasattr(TestQueryHandler, "__handler_type__")
        assert hasattr(TestQueryHandler, "__is_handler__")
        assert TestQueryHandler.__handler_type__ == "query"
        assert TestQueryHandler.__is_handler__ is True

    def test_decorator_validates_inheritance(self):
        """Test that decorator validates QueryHandler inheritance."""
        with pytest.raises(TypeError, match="must inherit from QueryHandler"):

            @query_handler
            class BadHandler:
                """Not a QueryHandler."""

                pass

    def test_handler_registration(self):
        """Test that decorator registers handler."""
        handlers = get_registered_handlers()
        assert "TestQueryHandler" in handlers["queries"]
        assert handlers["queries"]["TestQueryHandler"] is TestQueryHandler

    def test_is_handler_function(self):
        """Test is_handler() helper function."""
        assert is_handler(TestQueryHandler) is True

    def test_get_handler_type_function(self):
        """Test get_handler_type() helper function."""
        assert get_handler_type(TestQueryHandler) == "query"


class TestHandlerRegistry:
    """Tests for handler registry functions."""

    def test_get_registered_handlers_returns_both_types(self):
        """Test that get_registered_handlers returns both commands and queries."""
        handlers = get_registered_handlers()

        assert "commands" in handlers
        assert "queries" in handlers
        assert isinstance(handlers["commands"], dict)
        assert isinstance(handlers["queries"], dict)

    def test_registry_is_isolated(self):
        """Test that registry returns a copy, not the original."""
        handlers1 = get_registered_handlers()
        handlers2 = get_registered_handlers()

        # Should be equal but not the same object
        assert handlers1 == handlers2
        assert handlers1 is not handlers2
        assert handlers1["commands"] is not handlers2["commands"]
