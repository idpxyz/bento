"""Tests for Inbox Pattern implementation."""

import pytest
from datetime import datetime, UTC

from bento.persistence.inbox import InboxRecord, SqlAlchemyInbox


class TestInboxRecord:
    """Tests for InboxRecord model."""

    def test_create_inbox_record(self):
        """Test creating an InboxRecord."""
        record = InboxRecord.create(
            message_id="msg-123",
            event_type="OrderCreated",
            tenant_id="tenant-1",
            source="order-service",
        )

        assert record.message_id == "msg-123"
        assert record.event_type == "OrderCreated"
        assert record.tenant_id == "tenant-1"
        assert record.source == "order-service"

    def test_create_with_extra_data(self):
        """Test creating InboxRecord with extra_data."""
        extra_data = {"processed_by": "worker-1", "attempt": 1}
        record = InboxRecord.create(
            message_id="msg-456",
            event_type="PaymentReceived",
            extra_data=extra_data,
        )

        assert record.extra_data == extra_data

    def test_create_with_payload_hash(self):
        """Test creating InboxRecord with payload hash."""
        record = InboxRecord.create(
            message_id="msg-789",
            event_type="ShipmentCreated",
            payload_hash="abc123def456",
        )

        assert record.payload_hash == "abc123def456"


class TestInboxRecordTableStructure:
    """Tests for InboxRecord table structure."""

    def test_tablename(self):
        """Test that tablename is 'inbox'."""
        assert InboxRecord.__tablename__ == "inbox"

    def test_primary_key_is_message_id(self):
        """Test that message_id is the primary key."""
        # Check that message_id column is primary key
        mapper = InboxRecord.__mapper__
        pk_cols = [col.name for col in mapper.primary_key]
        assert "message_id" in pk_cols

    def test_has_required_columns(self):
        """Test that all required columns exist."""
        columns = {col.name for col in InboxRecord.__table__.columns}
        required = {"message_id", "tenant_id", "event_type", "processed_at"}
        assert required.issubset(columns)

    def test_has_indexes(self):
        """Test that indexes are defined."""
        indexes = {idx.name for idx in InboxRecord.__table__.indexes}
        # Should have at least tenant_id index
        assert any("tenant" in idx for idx in indexes)


class TestSqlAlchemyInboxInterface:
    """Tests for SqlAlchemyInbox interface (no DB)."""

    def test_inbox_has_required_methods(self):
        """Test that SqlAlchemyInbox has required methods."""
        # Check interface without instantiation
        assert hasattr(SqlAlchemyInbox, "is_processed")
        assert hasattr(SqlAlchemyInbox, "mark_processed")
        assert hasattr(SqlAlchemyInbox, "get_record")
        assert hasattr(SqlAlchemyInbox, "cleanup_old_records")

    def test_inbox_methods_are_async(self):
        """Test that inbox methods are async."""
        import inspect

        assert inspect.iscoroutinefunction(SqlAlchemyInbox.is_processed)
        assert inspect.iscoroutinefunction(SqlAlchemyInbox.mark_processed)
        assert inspect.iscoroutinefunction(SqlAlchemyInbox.get_record)
        assert inspect.iscoroutinefunction(SqlAlchemyInbox.cleanup_old_records)


class TestInboxProtocol:
    """Tests for Inbox protocol."""

    def test_inbox_protocol_exists(self):
        """Test that Inbox protocol is defined."""
        from bento.messaging.inbox import Inbox
        from typing import Protocol

        # Inbox should be a Protocol
        assert issubclass(Inbox, Protocol)

    def test_sqlalchemy_inbox_implements_protocol(self):
        """Test that SqlAlchemyInbox implements Inbox protocol."""
        from bento.messaging.inbox import Inbox

        # SqlAlchemyInbox should have all Inbox protocol methods
        assert hasattr(SqlAlchemyInbox, "is_processed")
        assert hasattr(SqlAlchemyInbox, "mark_processed")
