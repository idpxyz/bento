from functools import wraps
from time import time
from typing import Any, Callable, Dict, Optional, TypeVar

from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server

from idp.framework.infrastructure.messaging.common.logging import get_logger
from idp.framework.infrastructure.messaging.config.settings import get_settings

# Type variables for generic function signatures
F = TypeVar("F", bound=Callable[..., Any])
R = TypeVar("R")

# Initialize logger
logger = get_logger(__name__)

# Define metrics
message_counter = Counter(
    "message_bus_messages_total",
    "Total number of messages processed",
    ["topic", "status", "service"],
)

message_size = Histogram(
    "message_bus_message_size_bytes",
    "Size of messages in bytes",
    ["topic", "service"],
    buckets=(100, 1000, 10000, 100000, 1000000),
)

processing_time = Histogram(
    "message_bus_processing_time_seconds",
    "Time spent processing messages",
    ["service", "operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5),
)

consumer_lag = Gauge(
    "message_bus_consumer_lag",
    "Consumer lag in number of messages",
    ["topic", "consumer_group"],
)

producer_queue_size = Gauge(
    "message_bus_producer_queue_size",
    "Number of messages waiting to be sent",
    ["topic", "producer_id"],
)

error_counter = Counter(
    "message_bus_errors_total",
    "Total number of errors",
    ["topic", "service", "error_type"],
)


def start_metrics_server() -> None:
    """
    Start the Prometheus metrics server.
    """
    settings = get_settings()

    if settings.monitoring.enable_prometheus:
        try:
            start_http_server(settings.monitoring.prometheus_port)
            logger.info(
                "Started Prometheus metrics server",
                port=settings.monitoring.prometheus_port,
            )
        except Exception as e:
            logger.error(
                "Failed to start Prometheus metrics server",
                error=str(e),
                port=settings.monitoring.prometheus_port,
            )


def track_time(
    metric: Histogram,
    labels: Optional[Dict[str, str]] = None,
) -> Callable[[F], F]:
    """
    Decorator to track the execution time of a function.

    Args:
        metric (Histogram): Prometheus histogram to record the time
        labels (Optional[Dict[str, str]]): Labels to add to the metric

    Returns:
        Callable: Decorator function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time() - start
                label_values = labels or {}

                # 确保所有标签值都是安全的
                safe_labels = {}
                for key, value in label_values.items():
                    safe_labels[key] = sanitize_label_value(value)

                # 如果函数被调用时传入了 topic 参数，添加到标签中
                if "topic" in kwargs and "topic" not in safe_labels:
                    safe_labels["topic"] = sanitize_label_value(kwargs["topic"])

                try:
                    metric.labels(**safe_labels).observe(duration)
                except Exception as e:
                    logger.warning(
                        "Failed to record metric",
                        error=str(e),
                        metric=metric._name,
                        labels=safe_labels,
                    )

        return wrapper  # type: ignore

    return decorator


def count_messages(
    topic: str,
    service: str,
    status: str = "success",
) -> None:
    """
    Count a message being processed.

    Args:
        topic (str): Kafka topic
        service (str): Service name
        status (str): Status of the message processing
    """
    # 确保标签值是有效的
    safe_topic = sanitize_label_value(topic)
    safe_service = sanitize_label_value(service)
    safe_status = sanitize_label_value(status)

    message_counter.labels(
        topic=safe_topic, service=safe_service, status=safe_status
    ).inc()


def record_message_size(
    topic: str,
    service: str,
    size_bytes: int,
) -> None:
    """
    Record the size of a message.

    Args:
        topic (str): Kafka topic
        service (str): Service name
        size_bytes (int): Size of the message in bytes
    """
    # 确保标签值是有效的
    safe_topic = sanitize_label_value(topic)
    safe_service = sanitize_label_value(service)

    message_size.labels(topic=safe_topic, service=safe_service).observe(size_bytes)


def record_error(
    topic: str,
    service: str,
    error_type: str,
) -> None:
    """
    Record an error.

    Args:
        topic (str): Kafka topic
        service (str): Service name
        error_type (str): Type of error
    """
    # 确保标签值是有效的
    safe_topic = sanitize_label_value(topic)
    safe_service = sanitize_label_value(service)
    safe_error_type = sanitize_label_value(error_type)

    error_counter.labels(
        topic=safe_topic, service=safe_service, error_type=safe_error_type
    ).inc()


def sanitize_label_value(value: str) -> str:
    """
    确保标签值符合 Prometheus 的要求。

    Args:
        value (str): 原始标签值

    Returns:
        str: 安全的标签值
    """
    # 如果值为空，使用默认值
    if not value:
        return "unknown"

    # 替换不允许的字符
    return value.replace("-", "_").replace(".", "_").replace(" ", "_")


def update_consumer_lag(
    topic: str,
    consumer_group: str,
    lag: int,
) -> None:
    """
    Update the consumer lag metric.

    Args:
        topic (str): Kafka topic
        consumer_group (str): Consumer group ID
        lag (int): Lag in number of messages
    """
    # 确保标签值是有效的
    safe_topic = sanitize_label_value(topic)
    safe_consumer_group = sanitize_label_value(consumer_group)

    consumer_lag.labels(topic=safe_topic, consumer_group=safe_consumer_group).set(lag)


def update_producer_queue_size(
    topic: str,
    producer_id: str,
    queue_size: int,
) -> None:
    """
    Update the producer queue size metric.

    Args:
        topic (str): Kafka topic
        producer_id (str): Producer ID
        queue_size (int): Queue size in number of messages
    """
    # 确保标签值是有效的
    safe_topic = sanitize_label_value(topic)
    safe_producer_id = sanitize_label_value(producer_id)

    producer_queue_size.labels(topic=safe_topic, producer_id=safe_producer_id).set(
        queue_size
    )
