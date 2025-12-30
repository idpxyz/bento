"""Simple unit tests for middleware components."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request, Response

from bento.runtime.middleware.idempotency import _is_write_method, _hash_request
from bento.runtime.middleware.request_id import RequestIDMiddleware


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
        assert len(hash1) == 64

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


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    def test_init(self) -> None:
        """Test middleware initialization."""
        app = Mock()
        middleware = RequestIDMiddleware(
            app,
            header_name="X-Request-ID",
        )

        assert middleware.app is app
        assert middleware.header_name == "X-Request-ID"

    @pytest.mark.asyncio
    async def test_dispatch_generates_request_id(self) -> None:
        """Test dispatch generates request ID."""
        app = AsyncMock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        response = Response()
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_uses_existing_request_id(self) -> None:
        """Test dispatch uses existing request ID from header."""
        app = AsyncMock()
        middleware = RequestIDMiddleware(app)

        request = Mock(spec=Request)
        request.headers = {"X-Request-ID": "existing-id-123"}
        request.state = Mock()

        response = Response()
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_custom_header_name(self) -> None:
        """Test dispatch with custom header name."""
        app = AsyncMock()
        middleware = RequestIDMiddleware(
            app,
            header_name="X-Custom-ID",
        )

        request = Mock(spec=Request)
        request.headers = {"X-Custom-ID": "custom-id-456"}
        request.state = Mock()

        response = Response()
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)
