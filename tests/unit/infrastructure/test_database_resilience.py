"""Unit tests for database resilience (error classification and retry)."""

import asyncio

import pytest
from sqlalchemy.exc import (
    DatabaseError,
    DisconnectionError,
    IntegrityError,
    OperationalError,
)
from sqlalchemy.exc import (
    TimeoutError as SQLAlchemyTimeoutError,
)

from bento.infrastructure.database.resilience import (
    DEFAULT_RETRY_CONFIG,
    DatabaseErrorClassifier,
    ErrorCategory,
    RetryConfig,
    is_database_error_retryable,
    retry_on_db_error,
)


class TestDatabaseErrorClassifier:
    """Test error classification."""

    def test_classify_timeout_error(self):
        """Test timeout error classification."""
        error = SQLAlchemyTimeoutError()
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.TIMEOUT
        assert DatabaseErrorClassifier.is_retryable(error) is True

    def test_classify_disconnection_error(self):
        """Test disconnection error classification."""
        error = DisconnectionError()
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.CONNECTION
        assert DatabaseErrorClassifier.is_retryable(error) is True

    def test_classify_integrity_error(self):
        """Test integrity error classification."""
        error = IntegrityError("statement", "params", Exception("constraint"))
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.INTEGRITY
        assert DatabaseErrorClassifier.is_retryable(error) is False

    def test_classify_transient_operational_error(self):
        """Test transient operational error."""
        error = OperationalError("statement", "params", Exception("connection timeout"))
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.TRANSIENT
        assert DatabaseErrorClassifier.is_retryable(error) is True

    def test_classify_permanent_operational_error(self):
        """Test permanent operational error."""
        error = OperationalError("statement", "params", Exception("permission denied"))
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.PERMANENT
        assert DatabaseErrorClassifier.is_retryable(error) is False

    def test_classify_deadlock(self):
        """Test deadlock classification."""
        error = OperationalError("statement", "params", Exception("deadlock detected"))
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.TRANSIENT
        assert DatabaseErrorClassifier.is_retryable(error) is True

    def test_classify_syntax_error(self):
        """Test syntax error classification."""
        error = DatabaseError("statement", "params", Exception("syntax error"))
        category = DatabaseErrorClassifier.classify(error)

        assert category == ErrorCategory.PERMANENT
        assert DatabaseErrorClassifier.is_retryable(error) is False

    def test_is_retryable_convenience_function(self):
        """Test convenience function for retryability check."""
        # Retryable
        assert is_database_error_retryable(SQLAlchemyTimeoutError()) is True
        assert is_database_error_retryable(DisconnectionError()) is True

        # Not retryable
        assert is_database_error_retryable(IntegrityError("stmt", "params", Exception())) is False

    def test_should_reconnect(self):
        """Test reconnection decision."""
        # Should reconnect
        assert DatabaseErrorClassifier.should_reconnect(DisconnectionError()) is True
        assert (
            DatabaseErrorClassifier.should_reconnect(
                OperationalError("stmt", "params", Exception("connection reset"))
            )
            is True
        )

        # Should not reconnect
        assert (
            DatabaseErrorClassifier.should_reconnect(IntegrityError("stmt", "params", Exception()))
            is False
        )


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 0.1
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_calculate_delay_without_jitter(self):
        """Test delay calculation without jitter."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=100.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Attempt 0: 1.0 * 2^0 = 1.0
        assert config.calculate_delay(0) == 1.0

        # Attempt 1: 1.0 * 2^1 = 2.0
        assert config.calculate_delay(1) == 2.0

        # Attempt 2: 1.0 * 2^2 = 4.0
        assert config.calculate_delay(2) == 4.0

        # Attempt 3: 1.0 * 2^3 = 8.0
        assert config.calculate_delay(3) == 8.0

    def test_calculate_delay_with_max(self):
        """Test delay calculation with max limit."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Should cap at max_delay
        assert config.calculate_delay(10) == 5.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=100.0,
            exponential_base=2.0,
            jitter=True,
        )

        # With jitter, delay should be between 0.5 * base and 1.5 * base
        for attempt in range(5):
            delay = config.calculate_delay(attempt)
            expected_base = min(1.0 * (2.0**attempt), 100.0)
            assert delay >= expected_base * 0.5
            assert delay <= expected_base * 1.5

    def test_default_retry_config(self):
        """Test default retry config constant."""
        assert DEFAULT_RETRY_CONFIG.max_attempts == 3
        assert DEFAULT_RETRY_CONFIG.base_delay == 0.1
        assert DEFAULT_RETRY_CONFIG.max_delay == 10.0
        assert DEFAULT_RETRY_CONFIG.exponential_base == 2.0
        assert DEFAULT_RETRY_CONFIG.jitter is True


class TestRetryOnDbError:
    """Test retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful operation on first attempt."""
        call_count = 0

        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_on_db_error(successful_operation)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful operation after transient failures."""
        call_count = 0

        async def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise SQLAlchemyTimeoutError()
            return "success"

        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = await retry_on_db_error(failing_then_succeeding, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_permanent_error_fails_immediately(self):
        """Test permanent error fails immediately."""
        call_count = 0

        async def permanent_error():
            nonlocal call_count
            call_count += 1
            raise IntegrityError("statement", "params", Exception("constraint violation"))

        config = RetryConfig(max_attempts=3)

        with pytest.raises(IntegrityError):
            await retry_on_db_error(permanent_error, config=config)

        # Should only be called once (no retry)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry exhausted after max attempts."""
        call_count = 0

        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise SQLAlchemyTimeoutError()

        config = RetryConfig(max_attempts=3, base_delay=0.01)

        with pytest.raises(SQLAlchemyTimeoutError):
            await retry_on_db_error(always_failing, config=config)

        # Should be called max_attempts times
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_callback(self):
        """Test retry with callback."""
        call_count = 0
        retry_attempts = []

        def on_retry(error, attempt):
            retry_attempts.append((str(error), attempt))

        async def failing_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise SQLAlchemyTimeoutError()
            return "success"

        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = await retry_on_db_error(
            failing_twice,
            config=config,
            on_retry=on_retry,
        )

        assert result == "success"
        assert len(retry_attempts) == 2
        assert retry_attempts[0][1] == 1
        assert retry_attempts[1][1] == 2

    @pytest.mark.asyncio
    async def test_retry_delay_increases(self):
        """Test retry delay increases exponentially."""
        call_times = []

        async def failing_operation():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise SQLAlchemyTimeoutError()
            return "success"

        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )

        result = await retry_on_db_error(failing_operation, config=config)

        assert result == "success"
        assert len(call_times) == 3

        # Check delays
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be ~0.1s
        assert 0.08 < delay1 < 0.15

        # Second delay should be ~0.2s (2x first delay)
        assert 0.18 < delay2 < 0.25
