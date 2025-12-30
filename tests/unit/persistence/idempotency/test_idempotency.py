"""Tests for Idempotency Pattern implementation."""


from bento.persistence.idempotency import IdempotencyRecord, SqlAlchemyIdempotency
from bento.persistence.idempotency.record import IdempotencyConflictException


class TestIdempotencyRecord:
    """Tests for IdempotencyRecord model."""

    def test_create_idempotency_record(self):
        """Test creating an IdempotencyRecord."""
        record = IdempotencyRecord.create(
            idempotency_key="idem-123",
            operation="CreateOrder",
            tenant_id="tenant-1",
        )

        assert record.idempotency_key == "idem-123"
        assert record.operation == "CreateOrder"
        assert record.tenant_id == "tenant-1"
        assert record.state == "PENDING"

    def test_create_with_response(self):
        """Test creating IdempotencyRecord with response."""
        response = {"order_id": "order-456", "status": "created"}
        record = IdempotencyRecord.create(
            idempotency_key="idem-789",
            operation="CreateOrder",
            response=response,
            status_code=201,
            state="COMPLETED",
        )

        assert record.response == response
        assert record.status_code == 201
        assert record.state == "COMPLETED"

    def test_create_with_request_hash(self):
        """Test creating IdempotencyRecord with request hash."""
        record = IdempotencyRecord.create(
            idempotency_key="idem-abc",
            operation="UpdateOrder",
            request_hash="hash123456",
        )

        assert record.request_hash == "hash123456"


class TestIdempotencyRecordTableStructure:
    """Tests for IdempotencyRecord table structure."""

    def test_tablename(self):
        """Test that tablename is 'idempotency'."""
        assert IdempotencyRecord.__tablename__ == "idempotency"

    def test_primary_key_is_idempotency_key(self):
        """Test that idempotency_key is the primary key."""
        mapper = IdempotencyRecord.__mapper__
        pk_cols = [col.name for col in mapper.primary_key]
        assert "idempotency_key" in pk_cols

    def test_has_required_columns(self):
        """Test that all required columns exist."""
        columns = {col.name for col in IdempotencyRecord.__table__.columns}
        required = {
            "idempotency_key",
            "tenant_id",
            "operation",
            "response",
            "status_code",
            "state",
        }
        assert required.issubset(columns)

    def test_has_indexes(self):
        """Test that indexes are defined."""
        indexes = {idx.name for idx in IdempotencyRecord.__table__.indexes}
        assert any("tenant" in idx for idx in indexes)


class TestSqlAlchemyIdempotencyInterface:
    """Tests for SqlAlchemyIdempotency interface (no DB)."""

    def test_idempotency_has_required_methods(self):
        """Test that SqlAlchemyIdempotency has required methods."""
        assert hasattr(SqlAlchemyIdempotency, "get_response")
        assert hasattr(SqlAlchemyIdempotency, "is_processing")
        assert hasattr(SqlAlchemyIdempotency, "lock")
        assert hasattr(SqlAlchemyIdempotency, "store_response")
        assert hasattr(SqlAlchemyIdempotency, "mark_failed")
        assert hasattr(SqlAlchemyIdempotency, "cleanup_expired")

    def test_idempotency_methods_are_async(self):
        """Test that idempotency methods are async."""
        import inspect

        assert inspect.iscoroutinefunction(SqlAlchemyIdempotency.get_response)
        assert inspect.iscoroutinefunction(SqlAlchemyIdempotency.is_processing)
        assert inspect.iscoroutinefunction(SqlAlchemyIdempotency.lock)
        assert inspect.iscoroutinefunction(SqlAlchemyIdempotency.store_response)
        assert inspect.iscoroutinefunction(SqlAlchemyIdempotency.mark_failed)

    def test_default_ttl(self):
        """Test default TTL is 24 hours."""
        assert SqlAlchemyIdempotency.DEFAULT_TTL_SECONDS == 86400


class TestIdempotencyConflictException:
    """Tests for IdempotencyConflictException."""

    def test_conflict_error_creation(self):
        """Test creating IdempotencyConflictException."""
        error = IdempotencyConflictException(
            reason_code="IDEMPOTENCY_CONFLICT",
            idempotency_key="key-123",
        )
        assert error.idempotency_key == "key-123"
        assert error.reason_code == "IDEMPOTENCY_CONFLICT"
        assert "key-123" in str(error)

    def test_conflict_error_with_message(self):
        """Test IdempotencyConflictException with custom message."""
        error = IdempotencyConflictException(
            reason_code="IDEMPOTENCY_CONFLICT",
            idempotency_key="key-456",
            message="Custom conflict message",
        )
        assert "Custom conflict message" in str(error)


class TestIdempotencyProtocol:
    """Tests for IdempotencyStore protocol."""

    def test_idempotency_protocol_exists(self):
        """Test that IdempotencyStore protocol is defined."""
        from typing import Protocol

        from bento.messaging.idempotency import IdempotencyStore

        assert issubclass(IdempotencyStore, Protocol)

    def test_sqlalchemy_idempotency_implements_protocol(self):
        """Test that SqlAlchemyIdempotency has protocol methods."""

        assert hasattr(SqlAlchemyIdempotency, "get_response")
        assert hasattr(SqlAlchemyIdempotency, "lock")
        assert hasattr(SqlAlchemyIdempotency, "store_response")
