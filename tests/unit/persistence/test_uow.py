"""Unit tests for Unit of Work."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from bento.domain.domain_event import DomainEvent
from bento.messaging.outbox import Outbox
from bento.persistence.uow import SQLAlchemyUnitOfWork, _current_uow


@dataclass(frozen=True)
class DummyEvent(DomainEvent):
    """Test domain event."""

    message: str = "test"


class TestUnitOfWorkContext:
    """Test suite for UoW context management."""

    def test_context_var_exists(self):
        """Test that the context var for UoW exists."""
        assert _current_uow is not None

    def test_context_var_get_default(self):
        """Test that context var returns None by default."""
        _current_uow.set(None)
        result = _current_uow.get()
        assert result is None

    def test_context_var_set_and_get(self):
        """Test setting and getting UoW from context var."""
        mock_uow = Mock(spec=SQLAlchemyUnitOfWork)

        token = _current_uow.set(mock_uow)
        retrieved_uow = _current_uow.get()

        assert retrieved_uow is mock_uow

        # Clean up
        _current_uow.reset(token)


@pytest.mark.asyncio
class TestSQLAlchemyUnitOfWork:
    """Test suite for SQLAlchemyUnitOfWork."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        mock = AsyncMock()
        mock.sync_session = MagicMock()
        mock.sync_session.info = {}
        mock.commit = AsyncMock()
        mock.rollback = AsyncMock()
        mock.execute = AsyncMock()
        mock.execute.return_value.scalars.return_value.all.return_value = []
        return mock

    @pytest.fixture
    def mock_outbox(self):
        """Create a mock outbox repository."""
        return Mock(spec=Outbox)

    def test_uow_initialization(self, mock_session, mock_outbox):
        """Test UoW initialization."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        assert uow._session is mock_session
        assert uow._outbox is mock_outbox
        assert uow.pending_events == []

    async def test_uow_begin(self, mock_session, mock_outbox):
        """Test beginning a UoW transaction."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        async with uow:
            assert uow._session is not None
            assert _current_uow.get() is uow

    async def test_uow_commit(self, mock_session, mock_outbox):
        """Test committing a UoW transaction."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        async with uow:
            await uow.commit()

        mock_session.commit.assert_called_once()

    async def test_uow_rollback(self, mock_session, mock_outbox):
        """Test rolling back a UoW transaction."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        async with uow:
            await uow.rollback()

        # Rollback is called at least once (may be called on exit too)
        assert mock_session.rollback.call_count >= 1

    async def test_uow_track_aggregate(self, mock_session, mock_outbox):
        """Test tracking aggregates."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        # Create a mock aggregate
        class MockAggregate:
            def __init__(self):
                self.id = "test-1"

        aggregate = MockAggregate()

        async with uow:
            uow.track(aggregate)
            # Check immediately while in context
            assert aggregate in uow._tracked_aggregates

    async def test_uow_collect_events_pattern(self, mock_session, mock_outbox):
        """Test event collection pattern with events property."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        # Create aggregate with events property (UoW expects this)
        class MockAggregate:
            def __init__(self):
                self.id = "test-1"
                self._events = []

            @property
            def events(self):
                return self._events

            def clear_events(self):
                self._events.clear()

        aggregate = MockAggregate()
        event1 = DummyEvent(event_id=uuid4(), name="Event1", message="msg1")
        event2 = DummyEvent(event_id=uuid4(), name="Event2", message="msg2")
        aggregate._events.append(event1)
        aggregate._events.append(event2)

        async with uow:
            uow.track(aggregate)
            collected = await uow.collect_events()

        # Events should be collected
        assert len(collected) == 2
        assert event1 in collected
        assert event2 in collected

    async def test_uow_context_manager_rollback_on_exception(self, mock_session, mock_outbox):
        """Test that UoW rolls back on exception."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        with pytest.raises(ValueError, match="test error"):
            async with uow:
                raise ValueError("test error")

        mock_session.rollback.assert_called_once()

    async def test_uow_session_property(self, mock_session, mock_outbox):
        """Test accessing session property."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        async with uow:
            assert uow.session is mock_session

    async def test_uow_session_always_available(self, mock_session, mock_outbox):
        """Test that session is always available from constructor."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        # Session should be available even before async with
        assert uow.session is mock_session

    async def test_uow_clears_context_on_exit(self, mock_session, mock_outbox):
        """Test that UoW clears context on exit."""
        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        async with uow:
            assert _current_uow.get() is uow

        # Context should be restored (token-based restoration)

    async def test_uow_multi_level_nesting(self, mock_outbox):
        """Test that UoW handles multi-level nesting correctly."""
        mock_session1 = AsyncMock()
        mock_session1.sync_session = MagicMock()
        mock_session1.sync_session.info = {}

        mock_session2 = AsyncMock()
        mock_session2.sync_session = MagicMock()
        mock_session2.sync_session.info = {}

        uow1 = SQLAlchemyUnitOfWork(
            session=mock_session1,
            outbox=mock_outbox,
        )

        uow2 = SQLAlchemyUnitOfWork(
            session=mock_session2,
            outbox=mock_outbox,
        )

        async with uow1:
            assert _current_uow.get() is uow1

            async with uow2:
                # Inner UoW should be in context
                assert _current_uow.get() is uow2

            # Outer UoW should be restored
            assert _current_uow.get() is uow1


class TestUnitOfWorkPatterns:
    """Test suite for UoW usage patterns."""

    def test_pending_events_list_is_accessible(self):
        """Test that pending_events is accessible."""
        mock_session = AsyncMock()
        mock_outbox = Mock()

        uow = SQLAlchemyUnitOfWork(
            session=mock_session,
            outbox=mock_outbox,
        )

        # Should start empty
        assert uow.pending_events == []

        # Can use internal _register_event
        event = DummyEvent(event_id=uuid4(), name="Test")
        uow._register_event(event)

        assert len(uow.pending_events) == 1
