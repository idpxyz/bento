"""
Prometheus 指标记录器实现
"""
import asyncio
import logging
import threading
from typing import Any, ClassVar, Dict, List, Optional

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server,
)

from ..core import (
    METRIC_DROPPED_METRICS,
    METRIC_METRICS_PROCESSING_DURATION,
    MetricMetadata,
    MetricType,
    StandardMetrics,
)
from .recorder import BaseMetricsRecorder

logger = logging.getLogger(__name__)

class PrometheusRecorder(BaseMetricsRecorder):
    """Prometheus指标记录器实现"""
    
    # 存储所有实例，使每个服务一个环境只有一个实例
    _instances: ClassVar[Dict[str, "PrometheusRecorder"]] = {}
    
    @classmethod
    def get_instance(
        cls, 
        service_name: str, 
        env: str = "dev", 
        prefix: str = "", 
        port: int = 9090
    ) -> "PrometheusRecorder":
        """获取指标记录器实例（单例模式）
        
        Args:
            service_name: 服务名称
            env: 环境标识
            prefix: 指标前缀
            port: Prometheus端口
            
        Returns:
            PrometheusRecorder: 记录器实例
        """
        instance_key = f"{service_name}_{env}"
        
        if instance_key not in cls._instances:
            default_labels = {
                "service": service_name,
                "env": env
            }
            registry = CollectorRegistry()
            instance = cls(
                prefix=prefix,
                default_labels=default_labels,
                port=port,
                registry=registry,
                use_default_registry=False
            )
            cls._instances[instance_key] = instance
        
        return cls._instances[instance_key]
    
    def __init__(
        self, 
        prefix: str = "", 
        default_labels: Optional[Dict[str, str]] = None,
        port: int = 9090,
        registry: Optional[CollectorRegistry] = None,
        use_default_registry: bool = True
    ):
        """初始化Prometheus记录器
        
        Args:
            prefix: 指标名称前缀
            default_labels: 默认标签
            port: Prometheus指标HTTP服务端口
            registry: 自定义Prometheus注册表
            use_default_registry: 是否使用默认注册表
        """
        self._registry = registry or (REGISTRY if use_default_registry else CollectorRegistry())
        self._metrics: Dict[str, Any] = {}
        self._http_server_started = False
        self._port = port
        self._http_server_thread: Optional[threading.Thread] = None
        self._initialized_metrics = set()  # 跟踪已初始化的指标
        
        # 初始化基类
        super().__init__(prefix, default_labels)
        
        # 为监控自身启动的特殊处理
        self._setup_self_monitoring()
        
        # 启动HTTP服务器
        if port > 0:
            self._start_http_server()
    
    def _setup_self_monitoring(self) -> None:
        """设置自监控指标"""
        # 由于这些指标用于监控系统自身，直接创建而不通过通用接口
        processing_time_name = self._get_full_name(METRIC_METRICS_PROCESSING_DURATION)
        dropped_metrics_name = self._get_full_name(METRIC_DROPPED_METRICS)
        
        # 检查这些指标是否已经存在，避免重复创建
        if processing_time_name not in self._initialized_metrics:
            try:
                self._processing_time = Histogram(
                    processing_time_name,
                    "Metrics processing duration",
                    ["operation"],
                    buckets=[0.001, 0.005, 0.01, 0.05, 0.1],
                    registry=self._registry
                )
                self._initialized_metrics.add(processing_time_name)
            except ValueError as e:
                if "Duplicated timeseries" in str(e):
                    logger.warning(f"Reusing existing metric: {processing_time_name}")
                    # 如果指标已存在，尝试从注册表中获取
                    for collector in self._registry._collector_to_names:
                        if processing_time_name in self._registry._collector_to_names[collector]:
                            self._processing_time = collector
                            break
                else:
                    raise
        
        if dropped_metrics_name not in self._initialized_metrics:
            try:
                self._dropped_metrics_counter = Counter(
                    dropped_metrics_name,
                    "Number of dropped metrics",
                    registry=self._registry
                )
                self._initialized_metrics.add(dropped_metrics_name)
            except ValueError as e:
                if "Duplicated timeseries" in str(e):
                    logger.warning(f"Reusing existing metric: {dropped_metrics_name}")
                    # 如果指标已存在，尝试从注册表中获取
                    for collector in self._registry._collector_to_names:
                        if dropped_metrics_name in self._registry._collector_to_names[collector]:
                            self._dropped_metrics_counter = collector
                            break
                else:
                    raise
    
    def _start_http_server(self) -> None:
        """启动Prometheus HTTP服务器"""
        if self._http_server_started:
            return
        
        try:
            if self._registry == REGISTRY:
                # 使用默认注册表时，直接启动服务器
                start_http_server(self._port)
            else:
                # 使用自定义注册表时，指定注册表启动服务器
                start_http_server(self._port, registry=self._registry)
            
            self._http_server_started = True
            logger.info(f"Prometheus metrics server started on port {self._port}")
        except OSError as e:
            if "Address already in use" in str(e):
                # 端口已在使用，服务可能已经在运行
                logger.warning(f"Port {self._port} already in use, assuming metrics server is already running")
                self._http_server_started = True
            else:
                logger.error(f"Failed to start Prometheus HTTP server: {e}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus HTTP server: {e}")
            # 这里不抛出异常，让指标收集继续工作，即使HTTP服务器启动失败
    
    def _register_metric(self, metadata: MetricMetadata) -> None:
        """注册指标
        
        Args:
            metadata: 指标元信息
        """
        full_name = self._get_full_name(metadata.name)
        
        # 如果指标已存在，不重复注册
        if full_name in self._metrics:
            return
        
        # 检查是否在已初始化集合中
        if full_name in self._initialized_metrics:
            # 尝试从注册表中查找
            for collector in self._registry._collector_to_names:
                if full_name in self._registry._collector_to_names[collector]:
                    self._metrics[full_name] = collector
                    return
        
        # 确保标签名不是None
        label_names = metadata.label_names or []
        
        try:
            if metadata.type == MetricType.COUNTER:
                self._metrics[full_name] = Counter(
                    full_name,
                    metadata.help,
                    label_names,
                    registry=self._registry
                )
            elif metadata.type == MetricType.GAUGE:
                self._metrics[full_name] = Gauge(
                    full_name,
                    metadata.help,
                    label_names,
                    registry=self._registry
                )
            elif metadata.type == MetricType.HISTOGRAM:
                self._metrics[full_name] = Histogram(
                    full_name,
                    metadata.help,
                    label_names,
                    buckets=metadata.buckets,
                    registry=self._registry
                )
            elif metadata.type == MetricType.SUMMARY:
                self._metrics[full_name] = Summary(
                    full_name,
                    metadata.help,
                    label_names,
                    registry=self._registry
                )
            else:
                raise ValueError(f"Unsupported metric type: {metadata.type}")
            
            # 添加到已初始化集合
            self._initialized_metrics.add(full_name)
            
            logger.debug(f"Registered metric {full_name} of type {metadata.type} with labels {label_names}")
            
        except ValueError as e:
            if "Duplicated timeseries" in str(e):
                logger.warning(f"Metric {full_name} already registered, attempting to reuse")
                # 尝试从注册表中查找已存在的指标
                for collector in self._registry._collector_to_names:
                    if full_name in self._registry._collector_to_names[collector]:
                        self._metrics[full_name] = collector
                        self._initialized_metrics.add(full_name)
                        break
            else:
                logger.error(f"Failed to register metric {full_name}: {e}")
                raise
    
    async def _record_processing_duration(self, duration: float) -> None:
        """记录指标处理时间
        
        Args:
            duration: 处理时间(秒)
        """
        # 由于Prometheus客户端的方法是同步的，无需使用await
        try:
            self._processing_time.labels(operation="process").observe(duration)
        except Exception as e:
            logger.debug(f"Error recording processing duration: {e}")
    
    async def _record_dropped_metrics(self, count: int = 1) -> None:
        """记录丢弃的指标数量
        
        Args:
            count: 丢弃的数量
        """
        # 由于Prometheus客户端的方法是同步的，无需使用await
        try:
            self._dropped_metrics_counter.inc(count)
        except Exception as e:
            logger.debug(f"Error recording dropped metrics: {e}")
    
    async def _flush_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """刷新指标到Prometheus
        
        Args:
            metrics: 指标数据列表
        """
        # 对于Prometheus，无需批量上报，每个指标已经在调用时实时记录
        # 此方法主要用于非实时记录的指标系统，如Datadog、StatsD等
        start_time = asyncio.get_event_loop().time()
        
        processed = 0
        errors = 0
        
        for metric_data in metrics:
            try:
                name = metric_data.get("name", "")
                if not name:
                    logger.warning("Skipping metric with empty name")
                    continue
                    
                metric_type = metric_data.get("type")
                if not metric_type:
                    logger.warning(f"Skipping metric {name} with missing type")
                    continue
                    
                value = metric_data.get("value")
                # 确保值是数字类型
                if value is None:
                    logger.warning(f"Skipping metric {name} with missing value")
                    continue
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Skipping metric {name} with non-numeric value: {value}")
                    continue
                    
                labels = metric_data.get("labels", {})
                if not isinstance(labels, dict):
                    logger.warning(f"Skipping metric {name} with invalid labels type: {type(labels)}")
                    continue
                
                full_name = self._get_full_name(name)
                
                # 确保指标已注册
                if full_name not in self._metrics:
                    # 查找元数据
                    metadata = StandardMetrics.get_metric_by_name(name)
                    if metadata:
                        try:
                            self._register_metric(metadata)
                        except Exception as reg_error:
                            logger.warning(f"Failed to register metric {name}: {reg_error}")
                            continue
                    else:
                        # 创建一个基本的元数据并注册
                        try:
                            base_metadata = MetricMetadata(
                                name=name,
                                type=metric_type,
                                help=f"Dynamic metric: {name}",
                                label_names=list(labels.keys()) if labels else []
                            )
                            self._register_metric(base_metadata)
                        except Exception as reg_error:
                            logger.warning(f"Failed to create and register dynamic metric {name}: {reg_error}")
                            continue
                
                # 再次检查，因为可能注册失败
                if full_name not in self._metrics:
                    logger.warning(f"Skipping metric {full_name} - registration failed")
                    continue
                
                metric = self._metrics[full_name]
                
                # 获取标签名列表
                # 处理可能未定义_labelnames属性的情况
                label_names = getattr(metric, "_labelnames", [])
                
                # 确保 label_names 不是 None
                if label_names is None:
                    label_names = []
                
                # 准备标签值
                label_values = []
                if label_names:
                    # 确保所有标签都有值
                    for label in label_names:
                        label_value = labels.get(label, "")
                        # 尝试处理特殊的标签值
                        if metric_type == MetricType.GAUGE and label == "state" and label_value == "active":
                            # 特殊情况：状态标签转换为数字
                            label_value = "1"
                        elif metric_type == MetricType.GAUGE and label == "state" and label_value == "idle":
                            label_value = "0"
                        label_values.append(str(label_value))
                
                # 根据指标类型处理
                try:
                    if metric_type == MetricType.COUNTER:
                        if label_values:
                            metric.labels(*label_values).inc(value)
                        else:
                            metric.inc(value)
                    elif metric_type == MetricType.GAUGE:
                        if label_values:
                            metric.labels(*label_values).set(value)
                        else:
                            metric.set(value)
                    elif metric_type == MetricType.HISTOGRAM:
                        if label_values:
                            metric.labels(*label_values).observe(value)
                        else:
                            metric.observe(value)
                    elif metric_type == MetricType.SUMMARY:
                        if label_values:
                            metric.labels(*label_values).observe(value)
                        else:
                            metric.observe(value)
                except Exception as e:
                    logger.error(f"Error recording metric {name}: {e}")
                    errors += 1
                    continue
                
                processed += 1
            except Exception as e:
                error_msg = f"Error processing metric {metric_data.get('name', 'unknown')}: {e}"
                logger.error(error_msg)
                errors += 1
        
        # 记录处理时间
        try:
            duration = asyncio.get_event_loop().time() - start_time
            self._processing_time.labels(operation="flush").observe(duration)
        except Exception as e:
            logger.debug(f"Error recording flush duration: {e}")
        
        if errors > 0:
            logger.warning(f"Failed to process {errors} out of {len(metrics)} metrics")
    
    async def _check_health(self) -> bool:
        """检查Prometheus记录器健康状态
        
        Returns:
            bool: 健康状态
        """
        # 对于Prometheus，主要检查HTTP服务器是否正常启动
        return self._http_server_started
    
    def get_registry(self) -> CollectorRegistry:
        """获取Prometheus注册表
        
        Returns:
            CollectorRegistry: Prometheus注册表
        """
        return self._registry
    
    def reset(self) -> None:
        """重置记录器状态（用于测试环境）
        
        重置后需要重新注册指标
        """
        # 只在自定义注册表时才能重置
        if self._registry != REGISTRY:
            # 创建新的注册表
            self._registry = CollectorRegistry()
            self._metrics.clear()
            self._initialized_metrics.clear()
            
            # 重启 HTTP 服务器
            self._http_server_started = False
            if self._port > 0:
                self._start_http_server()
            
            # 重新设置自监控
            self._setup_self_monitoring()
            
            # 重新注册标准指标
            self._register_standard_metrics() 