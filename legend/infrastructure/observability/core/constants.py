"""
常量与默认配置
"""
from typing import Dict, Final, List

# 默认的直方图桶配置
DEFAULT_HISTOGRAM_BUCKETS: Final[List[float]] = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

# HTTP请求延迟直方图桶
HTTP_DURATION_BUCKETS: Final[List[float]] = [0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

# 数据库操作延迟直方图桶
DB_DURATION_BUCKETS: Final[List[float]] = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]

# 默认环境标签
DEFAULT_ENV_LABELS: Final[Dict[str, str]] = {
    "service": "unknown-service",
    "env": "development"
}

# 指标类型常量
METRIC_TYPE_COUNTER: Final[str] = "counter"
METRIC_TYPE_GAUGE: Final[str] = "gauge"
METRIC_TYPE_HISTOGRAM: Final[str] = "histogram"
METRIC_TYPE_SUMMARY: Final[str] = "summary"

# 标准标签名称
LABEL_SERVICE: Final[str] = "service"
LABEL_ENV: Final[str] = "env"
LABEL_METHOD: Final[str] = "method"
LABEL_PATH: Final[str] = "path"
LABEL_STATUS: Final[str] = "status"
LABEL_OPERATION: Final[str] = "operation"
LABEL_TABLE: Final[str] = "table"
LABEL_CACHE: Final[str] = "cache_name"
LABEL_TOPIC: Final[str] = "topic"
LABEL_CONSUMER: Final[str] = "consumer_group"
LABEL_ERROR: Final[str] = "error_type"

# HTTP指标名称
METRIC_HTTP_REQUESTS_TOTAL: Final[str] = "http_requests_total"
METRIC_HTTP_REQUEST_DURATION: Final[str] = "http_request_duration_seconds"
METRIC_HTTP_REQUEST_SIZE: Final[str] = "http_request_size_bytes"
METRIC_HTTP_RESPONSE_SIZE: Final[str] = "http_response_size_bytes"

# DB指标名称
METRIC_DB_CONNECTIONS: Final[str] = "db_connections"
METRIC_DB_OPERATION_DURATION: Final[str] = "db_operation_duration_seconds"
METRIC_DB_ERRORS_TOTAL: Final[str] = "db_errors_total"

# 缓存指标名称
METRIC_CACHE_HITS: Final[str] = "cache_hits_total"
METRIC_CACHE_MISSES: Final[str] = "cache_misses_total"
METRIC_CACHE_OPERATION_DURATION: Final[str] = "cache_operation_duration_seconds"

# 消息队列指标名称
METRIC_MESSAGE_PUBLISHED: Final[str] = "message_published_total"
METRIC_MESSAGE_CONSUMED: Final[str] = "message_consumed_total"
METRIC_MESSAGE_PROCESSING_DURATION: Final[str] = "message_processing_duration_seconds"

# 服务操作指标名称
METRIC_SERVICE_OPERATION_DURATION: Final[str] = "service_operation_duration_seconds"
METRIC_SERVICE_REQUESTS_TOTAL: Final[str] = "service_requests_total"
METRIC_SERVICE_ERRORS_TOTAL: Final[str] = "service_errors_total"

# 系统自监控指标名称
METRIC_METRICS_PROCESSING_DURATION: Final[str] = "obs_metrics_processing_seconds"
METRIC_DROPPED_METRICS: Final[str] = "obs_dropped_metrics_total"

# 追踪相关常量
TRACE_HEADER_NAME: Final[str] = "X-Trace-ID"
SPAN_HEADER_NAME: Final[str] = "X-Span-ID"
REQUEST_ID_HEADER_NAME: Final[str] = "X-Request-ID" 