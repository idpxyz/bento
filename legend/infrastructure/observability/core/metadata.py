"""
度量项元信息模型
"""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .constants import (
    DB_DURATION_BUCKETS,
    HTTP_DURATION_BUCKETS,
    LABEL_CACHE,
    LABEL_CONSUMER,
    LABEL_ERROR,
    LABEL_METHOD,
    LABEL_OPERATION,
    LABEL_PATH,
    LABEL_STATUS,
    LABEL_TABLE,
    LABEL_TOPIC,
    METRIC_CACHE_HITS,
    METRIC_CACHE_MISSES,
    METRIC_CACHE_OPERATION_DURATION,
    METRIC_DB_CONNECTIONS,
    METRIC_DB_ERRORS_TOTAL,
    METRIC_DB_OPERATION_DURATION,
    METRIC_DROPPED_METRICS,
    METRIC_HTTP_REQUEST_DURATION,
    METRIC_HTTP_REQUEST_SIZE,
    METRIC_HTTP_REQUESTS_TOTAL,
    METRIC_HTTP_RESPONSE_SIZE,
    METRIC_MESSAGE_CONSUMED,
    METRIC_MESSAGE_PROCESSING_DURATION,
    METRIC_MESSAGE_PUBLISHED,
    METRIC_METRICS_PROCESSING_DURATION,
    METRIC_SERVICE_ERRORS_TOTAL,
    METRIC_SERVICE_OPERATION_DURATION,
    METRIC_SERVICE_REQUESTS_TOTAL,
)


class MetricType(str, Enum):
    """度量项类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"      # 摘要

class MetricMetadata(BaseModel):
    """度量项元信息"""
    name: str = Field(..., description="指标名称")
    type: MetricType = Field(..., description="指标类型")
    help: str = Field(..., description="指标描述")
    unit: str = Field(default="", description="单位(如 seconds, bytes)")
    label_names: List[str] = Field(default_factory=list, description="标签名列表")
    buckets: Optional[List[float]] = Field(
        default=None, 
        description="直方图 bucket 列表(仅 histogram 类型)"
    )
    objectives: Optional[Dict[float, float]] = Field(
        default=None,
        description="分位数目标(仅 summary 类型)"
    )
    alert_threshold: Optional[float] = Field(
        default=None,
        description="告警阈值"
    )

class StandardMetrics:
    """标准度量项定义"""
    
    # 系统自监控指标
    METRICS_PROCESSING_DURATION = MetricMetadata(
        name=METRIC_METRICS_PROCESSING_DURATION,
        type=MetricType.HISTOGRAM,
        help="Metrics processing duration",
        unit="seconds",
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1],
        alert_threshold=1.0  # 处理时间超过1秒告警
    )
    
    DROPPED_METRICS = MetricMetadata(
        name=METRIC_DROPPED_METRICS,
        type=MetricType.COUNTER,
        help="Number of dropped metrics",
        alert_threshold=100  # 丢弃超过100个指标告警
    )
    
    # HTTP 相关
    HTTP_REQUEST_TOTAL = MetricMetadata(
        name=METRIC_HTTP_REQUESTS_TOTAL,
        type=MetricType.COUNTER,
        help="Total number of HTTP requests",
        label_names=[LABEL_METHOD, LABEL_PATH, LABEL_STATUS]
    )
    
    HTTP_REQUEST_DURATION = MetricMetadata(
        name=METRIC_HTTP_REQUEST_DURATION,
        type=MetricType.HISTOGRAM,
        help="HTTP request duration in seconds",
        unit="seconds",
        label_names=[LABEL_METHOD, LABEL_PATH],
        buckets=HTTP_DURATION_BUCKETS
    )
    
    HTTP_REQUEST_SIZE = MetricMetadata(
        name=METRIC_HTTP_REQUEST_SIZE,
        type=MetricType.HISTOGRAM,
        help="HTTP request size in bytes",
        unit="bytes",
        label_names=[LABEL_METHOD, LABEL_PATH],
        buckets=[64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    )
    
    HTTP_RESPONSE_SIZE = MetricMetadata(
        name=METRIC_HTTP_RESPONSE_SIZE,
        type=MetricType.HISTOGRAM,
        help="HTTP response size in bytes",
        unit="bytes",
        label_names=[LABEL_METHOD, LABEL_PATH],
        buckets=[64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    )
    
    # 数据库相关
    DB_CONNECTIONS = MetricMetadata(
        name=METRIC_DB_CONNECTIONS,
        type=MetricType.GAUGE,
        help="Number of database connections",
        label_names=["pool_name", "state"]
    )
    
    DB_OPERATION_DURATION = MetricMetadata(
        name=METRIC_DB_OPERATION_DURATION,
        type=MetricType.HISTOGRAM,
        help="Database operation duration in seconds",
        unit="seconds",
        label_names=[LABEL_OPERATION, LABEL_TABLE],
        buckets=DB_DURATION_BUCKETS
    )
    
    DB_ERRORS = MetricMetadata(
        name=METRIC_DB_ERRORS_TOTAL,
        type=MetricType.COUNTER,
        help="Total number of database errors",
        label_names=[LABEL_OPERATION, LABEL_ERROR]
    )
    
    # 缓存相关
    CACHE_HITS = MetricMetadata(
        name=METRIC_CACHE_HITS,
        type=MetricType.COUNTER,
        help="Total number of cache hits",
        label_names=[LABEL_CACHE]
    )
    
    CACHE_MISSES = MetricMetadata(
        name=METRIC_CACHE_MISSES,
        type=MetricType.COUNTER,
        help="Total number of cache misses",
        label_names=[LABEL_CACHE]
    )
    
    CACHE_OPERATION_DURATION = MetricMetadata(
        name=METRIC_CACHE_OPERATION_DURATION,
        type=MetricType.HISTOGRAM,
        help="Cache operation duration in seconds",
        unit="seconds",
        label_names=[LABEL_OPERATION, LABEL_CACHE],
        buckets=[0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1]
    )
    
    # 消息队列相关
    MESSAGE_PUBLISHED = MetricMetadata(
        name=METRIC_MESSAGE_PUBLISHED,
        type=MetricType.COUNTER,
        help="Total number of published messages",
        label_names=[LABEL_TOPIC]
    )
    
    MESSAGE_CONSUMED = MetricMetadata(
        name=METRIC_MESSAGE_CONSUMED,
        type=MetricType.COUNTER,
        help="Total number of consumed messages",
        label_names=[LABEL_TOPIC, LABEL_CONSUMER]
    )
    
    MESSAGE_PROCESSING_DURATION = MetricMetadata(
        name=METRIC_MESSAGE_PROCESSING_DURATION,
        type=MetricType.HISTOGRAM,
        help="Message processing duration in seconds",
        unit="seconds",
        label_names=[LABEL_TOPIC],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
    )
    
    # 服务操作相关
    SERVICE_OPERATION_DURATION = MetricMetadata(
        name=METRIC_SERVICE_OPERATION_DURATION,
        type=MetricType.HISTOGRAM,
        help="Service operation duration in seconds",
        unit="seconds",
        label_names=["service", "success"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
    )
    
    SERVICE_REQUESTS_TOTAL = MetricMetadata(
        name=METRIC_SERVICE_REQUESTS_TOTAL,
        type=MetricType.COUNTER,
        help="Total number of service requests",
        label_names=["service", "operation"]
    )
    
    SERVICE_ERRORS_TOTAL = MetricMetadata(
        name=METRIC_SERVICE_ERRORS_TOTAL,
        type=MetricType.COUNTER,
        help="Total number of service errors",
        label_names=["service", "error_type"]
    )

    @classmethod
    def get_all_metrics(cls) -> List[MetricMetadata]:
        """获取所有标准度量项"""
        return [
            value for name, value in vars(cls).items()
            if isinstance(value, MetricMetadata)
        ]
    
    @classmethod
    def get_metric_by_name(cls, name: str) -> Optional[MetricMetadata]:
        """根据名称获取度量项元信息
        
        Args:
            name: 度量项名称
            
        Returns:
            Optional[MetricMetadata]: 度量项元信息，不存在则返回None
        """
        for metric in cls.get_all_metrics():
            if metric.name == name:
                return metric
        return None 