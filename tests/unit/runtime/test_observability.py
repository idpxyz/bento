"""Tests for runtime observability helpers (OpenTelemetry setup)."""

from __future__ import annotations

import builtins
import sys
from types import ModuleType
from typing import Any

import pytest

from bento.runtime.observability import otel, tracing


class _DummySpanExporter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummyMetricExporter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummyReader:
    def __init__(self, exporter=None, prefix=None):
        self.exporter = exporter
        self.prefix = prefix


class _DummyTracerProvider:
    def __init__(self):
        self.processors: list[object] = []

    def add_span_processor(self, processor):
        self.processors.append(processor)


class _DummyMeterProvider:
    def __init__(self, metric_readers=None):
        self.metric_readers = metric_readers or []


class _DummyProcessor:
    def __init__(self, exporter):
        self.exporter = exporter


def _install_fake_opentelemetry(monkeypatch):
    modules: dict[str, ModuleType | object] = {}

    # Base package
    opentelemetry_pkg = ModuleType("opentelemetry")
    trace_module = ModuleType("opentelemetry.trace")

    def set_tracer_provider(provider: Any) -> None:  # pragma: no cover - assigned below
        setattr(trace_module, "provider", provider)

    setattr(trace_module, "provider", None)
    setattr(trace_module, "set_tracer_provider", set_tracer_provider)
    setattr(trace_module, "get_tracer", lambda name: f"tracer:{name}")
    setattr(opentelemetry_pkg, "trace", trace_module)

    modules["opentelemetry"] = opentelemetry_pkg
    modules["opentelemetry.trace"] = trace_module

    # sdk.trace
    sdk_trace = ModuleType("opentelemetry.sdk.trace")
    setattr(sdk_trace, "TracerProvider", _DummyTracerProvider)
    modules["opentelemetry.sdk.trace"] = sdk_trace

    sdk_trace_export = ModuleType("opentelemetry.sdk.trace.export")
    setattr(sdk_trace_export, "BatchSpanProcessor", _DummyProcessor)
    setattr(sdk_trace_export, "SimpleSpanProcessor", _DummyProcessor)
    setattr(sdk_trace_export, "ConsoleSpanExporter", _DummySpanExporter)
    modules["opentelemetry.sdk.trace.export"] = sdk_trace_export

    jaeger_export_module = ModuleType("opentelemetry.exporter.jaeger.thrift")
    setattr(jaeger_export_module, "JaegerExporter", _DummySpanExporter)
    modules["opentelemetry.exporter.jaeger.thrift"] = jaeger_export_module

    otlp_trace_module = ModuleType("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")
    setattr(otlp_trace_module, "OTLPSpanExporter", _DummySpanExporter)
    modules["opentelemetry.exporter.otlp.proto.grpc.trace_exporter"] = otlp_trace_module

    # Metrics modules
    metrics_module = ModuleType("opentelemetry.metrics")
    setattr(metrics_module, "provider", None)

    def set_meter_provider(provider: Any) -> None:  # pragma: no cover - simple setter
        setattr(metrics_module, "provider", provider)

    setattr(metrics_module, "set_meter_provider", set_meter_provider)
    modules["opentelemetry.metrics"] = metrics_module

    sdk_metrics = ModuleType("opentelemetry.sdk.metrics")
    setattr(sdk_metrics, "MeterProvider", _DummyMeterProvider)
    modules["opentelemetry.sdk.metrics"] = sdk_metrics

    sdk_metrics_export = ModuleType("opentelemetry.sdk.metrics.export")
    setattr(
        sdk_metrics_export,
        "PeriodicExportingMetricReader",
        _DummyReader,
    )
    setattr(sdk_metrics_export, "ConsoleMetricExporter", _DummyMetricExporter)
    modules["opentelemetry.sdk.metrics.export"] = sdk_metrics_export

    prometheus_module = ModuleType("opentelemetry.exporter.prometheus")
    setattr(prometheus_module, "PrometheusMetricReader", _DummyReader)
    modules["opentelemetry.exporter.prometheus"] = prometheus_module

    otlp_metric_module = ModuleType("opentelemetry.exporter.otlp.proto.grpc.metric_exporter")
    setattr(otlp_metric_module, "OTLPMetricExporter", _DummyMetricExporter)
    modules["opentelemetry.exporter.otlp.proto.grpc.metric_exporter"] = otlp_metric_module

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    return {
        "trace_module": trace_module,
        "metrics_module": metrics_module,
    }


@pytest.fixture
def fake_otel(monkeypatch):
    return _install_fake_opentelemetry(monkeypatch)


def test_setup_tracing_console(fake_otel):
    provider = otel.setup_tracing("order-service")
    assert isinstance(provider, _DummyTracerProvider)
    assert fake_otel["trace_module"].provider is provider
    assert provider.processors  # console processor added


def test_setup_tracing_jaeger(fake_otel):
    provider = otel.setup_tracing(
        "order-service",
        trace_exporter="jaeger",
        jaeger_host="jaeger",
        jaeger_port=9000,
    )
    assert isinstance(provider, _DummyTracerProvider)
    processor = provider.processors[0]
    assert isinstance(processor.exporter, _DummySpanExporter)
    assert processor.exporter.kwargs["agent_host_name"] == "jaeger"
    assert processor.exporter.kwargs["agent_port"] == 9000


def test_setup_tracing_otlp(fake_otel):
    provider = otel.setup_tracing(
        "order-service",
        trace_exporter="otlp",
        otlp_endpoint="http://otel:4317",
    )
    assert isinstance(provider, _DummyTracerProvider)
    processor = provider.processors[0]
    assert processor.exporter.kwargs["endpoint"] == "http://otel:4317"


def test_setup_tracing_import_error(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # pragma: no cover - fallback path
        if name.startswith("opentelemetry"):
            raise ImportError("missing otel")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert otel.setup_tracing("svc") is None


def test_setup_metrics_console(fake_otel):
    provider = otel.setup_metrics()
    assert isinstance(provider, _DummyMeterProvider)
    assert fake_otel["metrics_module"].provider is provider
    assert provider.metric_readers


def test_setup_metrics_prometheus(fake_otel):
    provider = otel.setup_metrics(metrics_exporter="prometheus", prometheus_prefix="svc_")
    assert isinstance(provider, _DummyMeterProvider)
    reader = provider.metric_readers[0]
    assert isinstance(reader, _DummyReader)
    assert reader.prefix == "svc_"


def test_setup_metrics_otlp(fake_otel):
    provider = otel.setup_metrics(metrics_exporter="otlp", otlp_endpoint="http://otel:4318")
    assert isinstance(provider, _DummyMeterProvider)
    reader = provider.metric_readers[0]
    assert isinstance(reader.exporter, _DummyMetricExporter)
    assert reader.exporter.kwargs["endpoint"] == "http://otel:4318"


def test_setup_metrics_import_error(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("missing otel")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert otel.setup_metrics() is None


def test_tracing_manager_enable_jaeger(fake_otel):
    manager = tracing.TracingManager()
    manager.enable_jaeger("svc", host="jaeger", port=16686)
    assert manager.get_tracer() == "tracer:bento.runtime.observability.tracing"


def test_tracing_manager_enable_otlp(fake_otel):
    manager = tracing.TracingManager()
    manager.enable_otlp(endpoint="http://collector:4317")
    assert manager.get_tracer() == "tracer:bento.runtime.observability.tracing"
