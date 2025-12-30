"""Unit tests for StructuredLoggingMiddleware."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request, Response

from bento.runtime.middleware.logging import StructuredLoggingMiddleware


class TestStructuredLoggingMiddleware:
    """Tests for StructuredLoggingMiddleware."""

    def test_init(self) -> None:
        """Test middleware initialization."""
        app = Mock()
        middleware = StructuredLoggingMiddleware(
            app,
            logger_name="test-logger",
            log_request_body=True,
            log_response_body=True,
        )

        assert middleware.app is app
        assert middleware.logger_name == "test-logger"
        assert middleware.log_request_body is True
        assert middleware.log_response_body is True

    def test_init_with_skip_paths(self) -> None:
        """Test middleware initialization with skip paths."""
        app = Mock()
        skip_paths = {"/health", "/ping"}
        middleware = StructuredLoggingMiddleware(
            app,
            skip_paths=skip_paths,
        )

        assert middleware.skip_paths == skip_paths

    @pytest.mark.asyncio
    async def test_dispatch_normal_request(self) -> None:
        """Test dispatch with normal request."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/users"
        request.headers = {}

        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_skip_health_check(self) -> None:
        """Test dispatch skips health check endpoint."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(
            app,
            skip_paths={"/health", "/ping"},
        )

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/health"

        response = Response(status_code=200)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_post_request(self) -> None:
        """Test dispatch with POST request."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(
            app,
            log_request_body=True,
        )

        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/orders"
        request.headers = {"content-type": "application/json"}
        request.body = AsyncMock(return_value=b'{"test": "data"}')

        response = Response(content="created", status_code=201)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_error_response(self) -> None:
        """Test dispatch with error response."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/invalid"
        request.headers = {}

        response = Response(content="not found", status_code=404)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self) -> None:
        """Test dispatch handles exceptions."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/error"
        request.headers = {}

        call_next = AsyncMock(side_effect=Exception("Test error"))

        with pytest.raises(Exception):
            await middleware.dispatch(request, call_next)

    @pytest.mark.asyncio
    async def test_dispatch_with_request_id(self) -> None:
        """Test dispatch with request ID in state."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/users"
        request.headers = {}
        request.state = Mock()
        request.state.request_id = "test-request-123"

        response = Response(status_code=200)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_log_response_body(self) -> None:
        """Test dispatch logs response body when enabled."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(
            app,
            log_response_body=True,
        )

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/data"
        request.headers = {}

        response = Response(content='{"data": "value"}', status_code=200)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_custom_logger_name(self) -> None:
        """Test dispatch with custom logger name."""
        app = AsyncMock()
        middleware = StructuredLoggingMiddleware(
            app,
            logger_name="custom-logger",
        )

        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/test"
        request.headers = {}

        response = Response(status_code=200)
        call_next = AsyncMock(return_value=response)

        await middleware.dispatch(request, call_next)

        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_multiple_skip_paths(self) -> None:
        """Test dispatch with multiple skip paths."""
        app = AsyncMock()
        skip_paths = {"/health", "/ping", "/metrics", "/status"}
        middleware = StructuredLoggingMiddleware(
            app,
            skip_paths=skip_paths,
        )

        for path in skip_paths:
            request = Mock(spec=Request)
            request.method = "GET"
            request.url = Mock()
            request.url.path = path
            request.headers = {}

            response = Response(status_code=200)
            call_next = AsyncMock(return_value=response)

            await middleware.dispatch(request, call_next)

            call_next.assert_called_once_with(request)
