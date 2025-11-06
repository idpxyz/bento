"""Observability module for Bento framework.

This module is reserved for future OpenTelemetry integration.

For production applications, we recommend using OpenTelemetry (OTel) which provides:
- Industry-standard observability
- Automatic instrumentation for common libraries (SQLAlchemy, HTTP, etc.)
- Unified metrics, traces, and logs
- Flexible exporters (Prometheus, Jaeger, OTLP, etc.)

Example integration:
    ```python
    from opentelemetry import trace
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    # Auto-instrument your database and HTTP calls
    SQLAlchemyInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    ```

For basic logging, use Python's standard logging module or structlog.
"""

# Basic logging support for framework use
import logging

logger = logging.getLogger("bento")

__all__ = ["logger"]
