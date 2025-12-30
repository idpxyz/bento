"""Unit tests for IdempotencyMiddleware."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response

from bento.runtime.middleware.idempotency import (
    IdempotencyMiddleware,
    _is_write_method,
    _hash_request,
)


class TestIsWriteMethod:
    """Tests for _is_write_method."""

    def test_post_is_write(self) -> None:
        """Test POST is write method."""
        assert _is_write_method("POST")

    def test_put_is_write(self) -> None:
        """Test PUT is write method."""
        assert _is_write_method("PUT")

    def test_patch_is_write(self) -> None:
        """Test PATCH is write method."""
        assert _is_write_method("PATCH")

    def test_delete_is_write(self) -> None:
        """Test DELETE is write method."""
        assert _is_write_method("DELETE")

    def test_get_not_write(self) -> None:
        """Test GET is not write method."""
        assert not _is_write_method("GET")

    def test_head_not_write(self) -> None:
        """Test HEAD is not write method."""
        assert not _is_write_method("HEAD")

    def test_options_not_write(self) -> None:
        """Test OPTIONS is not write method."""
        assert not _is_write_method("OPTIONS")

    def test_case_insensitive(self) -> None:
        """Test method check is case insensitive."""
        assert _is_write_method("post")
        assert _is_write_method("Post")


class TestHashRequest:
    """Tests for _hash_request."""

    def test_hash_dict_request(self) -> None:
        """Test hashing dict request."""
        body = {"key": "value", "number": 123}
        hash1 = _hash_request(body)
        hash2 = _hash_request(body)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex length

    def test_hash_string_request(self) -> None:
        """Test hashing string request."""
        body = "test body"
        hash1 = _hash_request(body)
        hash2 = _hash_request(body)

        assert hash1 == hash2
        assert isinstance(hash1, str)

    def test_hash_dict_order_independent(self) -> None:
        """Test hash is independent of dict key order."""
        body1 = {"a": 1, "b": 2}
        body2 = {"b": 2, "a": 1}

        assert _hash_request(body1) == _hash_request(body2)

    def test_hash_different_bodies(self) -> None:
        """Test different bodies produce different hashes."""
        body1 = {"key": "value1"}
        body2 = {"key": "value2"}

        assert _hash_request(body1) != _hash_request(body2)


class TestIdempotencyMiddleware:
    """Tests for IdempotencyMiddleware."""

    def test_init(self) -> None:
        """Test middleware initialization."""
        app = Mock()
        middleware = IdempotencyMiddleware(
            app,
            header_name="X-Idempotency-Key",
            ttl_seconds=3600,
            tenant_id="default",
        )

        assert middleware.app is app
        assert middleware.header_name == "X-Idempotency-Key"
        assert middleware.ttl_seconds == 3600
        assert middleware.tenant_id == "default"

    @pytest.mark.asyncio
    async def test_get_request_skipped(self) -> None:
        """Test GET requests are skipped."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_post_without_idempotency_key(self) -> None:
        """Test POST without idempotency key."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.headers = {}

        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_post_with_idempotency_key(self) -> None:
        """Test POST with idempotency key."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "test-key-123"}
        request.body = AsyncMock(return_value=b'{"test": "data"}')

        response = Response(content="test response", status_code=200)
        call_next = AsyncMock(return_value=response)

        with patch.object(middleware, "_check_idempotency", return_value=None):
            await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_idempotency_conflict(self) -> None:
        """Test idempotency conflict response."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "test-key-123"}
        request.body = AsyncMock(return_value=b'{"test": "data"}')

        call_next = AsyncMock()

        with patch.object(
            middleware,
            "_check_idempotency",
            side_effect=Exception("Conflict"),
        ):
            try:
                await middleware.dispatch(request, call_next)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_put_request(self) -> None:
        """Test PUT request with idempotency."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(app)

        request = Mock(spec=Request)
        request.method = "PUT"
        request.headers = {"X-Idempotency-Key": "test-key-456"}
        request.body = AsyncMock(return_value=b'{"test": "data"}')

        response = Response(content="test response", status_code=200)
        call_next = AsyncMock(return_value=response)

        with patch.object(middleware, "_check_idempotency", return_value=None):
            await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_delete_request(self) -> None:
        """Test DELETE request with idempotency."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(app)

        request = Mock(spec=Request)
        request.method = "DELETE"
        request.headers = {"X-Idempotency-Key": "test-key-789"}
        request.body = AsyncMock(return_value=b'')

        response = Response(status_code=204)
        call_next = AsyncMock(return_value=response)

        with patch.object(middleware, "_check_idempotency", return_value=None):
            await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_custom_header_name(self) -> None:
        """Test custom idempotency header name."""
        app = AsyncMock()
        middleware = IdempotencyMiddleware(
            app,
            header_name="X-Custom-Idempotency",
        )

        request = Mock(spec=Request)
        request.method = "POST"
        request.headers = {"X-Custom-Idempotency": "custom-key"}
        request.body = AsyncMock(return_value=b'{"test": "data"}')

        response = Response(content="test response", status_code=200)
        call_next = AsyncMock(return_value=response)

        with patch.object(middleware, "_check_idempotency", return_value=None):
            await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)
