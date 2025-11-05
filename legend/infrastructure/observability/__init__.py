"""
可观测性模块
提供监控指标、分布式追踪、异常监控等功能
"""
# 在这里导入核心组件
# 完整代码请参考 Design.md 文件

# 导出所有公开的符号
__all__ = [
    # 核心接口
    "SpanKind",
    "Span",
    "IMetricsRecorder",
    "ITracer",
    
    # 模型
    "MetricType",
    "MetricMetadata",
    "StandardMetrics",
    "MetricsConfig",
    "TracingConfig",
    "ObservabilityConfig",
    "PostgresCommonConfig",
    "PostgresObservabilityConfig",
    
    # 指标记录器
    "BaseMetricsRecorder",
    "PrometheusRecorder",
    
    # 追踪器
    "BaseTracer",
    "BaseSpan",
    "MemoryTracer",
    "MemorySpan",
    
    # 中间件
    "MetricsMiddleware",
    "TracingMiddleware",
    "RequestIdMiddleware",
    
    # 工厂函数
    "create_observability"
] 

# 导出核心接口和模型
from .core import (
    IMetricsRecorder,
    ITracer,
    MetricMetadata,
    MetricsConfig,
    MetricType,
    ObservabilityConfig,
    PostgresCommonConfig,
    PostgresObservabilityConfig,
    Span,
    SpanKind,
    StandardMetrics,
    TracingConfig,
)

# 导出工厂函数
from .factory import create_observability

# 导出指标记录器
from .metrics import BaseMetricsRecorder, PrometheusRecorder

# 导出中间件
from .middleware import MetricsMiddleware, RequestIdMiddleware, TracingMiddleware

# 导出追踪器
from .tracing import BaseSpan, BaseTracer, MemorySpan, MemoryTracer

# 添加对监听器的导出，需保留之前的所有导出
try:
    from .listeners import CacheListener, MessagingListener, SQLAlchemyListener
    __all__.extend(["SQLAlchemyListener", "CacheListener", "MessagingListener"])
except ImportError:
    pass 