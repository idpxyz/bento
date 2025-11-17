from __future__ import annotations

from sqlalchemy.exc import DatabaseError, OperationalError

from bento.infrastructure.database.resilience.errors import (
    DatabaseErrorClassifier,
    ErrorCategory,
    is_database_error_retryable,
)


class FakeDbError(DatabaseError):
    def __init__(self, msg: str):
        super().__init__(msg, None, None)


class FakeOpError(OperationalError):
    def __init__(self, msg: str):
        super().__init__(msg, None, None)


def test_classify_by_message_transient_and_permanent():
    tr = DatabaseErrorClassifier.classify(FakeDbError("connection reset by peer"))
    assert tr == ErrorCategory.TRANSIENT

    pm = DatabaseErrorClassifier.classify(FakeDbError("permission denied"))
    assert pm == ErrorCategory.PERMANENT


def test_is_retryable_operational_default_transient():
    # OperationalError without known permanent patterns defaults to TRANSIENT
    err = FakeOpError("some operational condition")
    assert is_database_error_retryable(err) is True
