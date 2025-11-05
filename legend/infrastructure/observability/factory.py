"""
可观测性工厂模块
提供创建可观测性实例的工厂函数
"""
import logging
from typing import Any, Dict, Optional, Protocol

from .core import IMetricsRecorder, ITracer, ObservabilityConfig
from .core.config import ObservabilityConfig
from .metrics.postgres import PostgresMetricsRecorder
from .metrics.prometheus import PrometheusRecorder
from .metrics.recorder import BaseMetricsRecorder
from .tracing import BaseTracer, MemoryTracer

logger = logging.getLogger(__name__)


class Observability:
    """可观测性聚合类
    
    集中管理各种可观测性组件，如指标记录器和分布式追踪
    """
    
    def __init__(
        self,
        config: ObservabilityConfig,
        metrics_recorder: Optional[IMetricsRecorder] = None,
        tracer: Optional[ITracer] = None,
    ):
        """初始化可观测性管理器
        
        Args:
            config: 可观测性配置
            metrics_recorder: 指标记录器实例，如果为None则根据配置创建
            tracer: 分布式追踪器实例，如果为None则根据配置创建
        """
        self.config = config
        self._metrics_recorder = metrics_recorder
        self._tracer = tracer
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化所有组件"""
        if self._initialized:
            return
        
        # 如果未提供指标记录器，尝试创建默认实例
        if self._metrics_recorder is None and self.config.metrics.enabled:
            try:
                if self.config.metrics.recorder_type == "PROMETHEUS":
                    self._metrics_recorder = PrometheusRecorder(
                        prefix=self.config.metrics.name_prefix,
                        default_labels={
                            "env": self.config.env,
                            **self.config.metrics.default_labels
                        }
                    )
                elif self.config.metrics.recorder_type == "MEMORY":
                    self._metrics_recorder = BaseMetricsRecorder(
                        prefix=self.config.metrics.name_prefix,
                        default_labels={
                            "env": self.config.env,
                            **self.config.metrics.default_labels
                        }
                    )
                elif self.config.metrics.recorder_type == "POSTGRES":
                    if not self.config.metrics.postgres:
                        raise ValueError("PostgreSQL configuration is required for POSTGRES recorder type")
                    self._metrics_recorder = PostgresMetricsRecorder.from_config(
                        config=self.config.metrics
                    )
                else:
                    logger.warning(f"未知的指标记录器类型: {self.config.metrics.recorder_type}, 使用内存记录器")
                    self._metrics_recorder = BaseMetricsRecorder(
                        prefix=self.config.metrics.name_prefix,
                        default_labels={"env": self.config.env}
                    )
            except Exception as e:
                logger.error(f"创建指标记录器失败: {e}")
                self._metrics_recorder = BaseMetricsRecorder(
                    prefix=self.config.metrics.prefix,
                    default_labels={"env": self.config.env}
                )
        
        # 如果未提供追踪器，尝试创建默认实例
        if self._tracer is None and self.config.tracing.enabled:
            try:
                if self.config.tracing.tracer_type == "MEMORY":
                    self._tracer = MemoryTracer(
                        service_name=self.config.tracing.service_name,
                        sample_rate=self.config.tracing.sample_rate
                    )
                elif self.config.tracing.tracer_type == "SENTRY":
                    try:
                        from .tracing.sentry_tracer import SentryTracer
                        self._tracer = SentryTracer(
                            service_name=self.config.tracing.service_name,
                            dsn=self.config.tracing.sentry_dsn,
                            sample_rate=self.config.tracing.sample_rate
                        )
                    except ImportError:
                        logger.warning("无法导入Sentry追踪器，回退到内存追踪器")
                        self._tracer = MemoryTracer(
                            service_name=self.config.tracing.service_name,
                            sample_rate=self.config.tracing.sample_rate
                        )
                elif self.config.tracing.tracer_type == "POSTGRES":
                    try:
                        from .tracing.postgres_tracer import PostgresTracer
                        self._tracer = PostgresTracer(
                            service_name=self.config.tracing.service_name,
                            sample_rate=self.config.tracing.sample_rate,
                            connection=self.config.tracing.postgres_connection,
                            schema=self.config.tracing.postgres_schema,
                            spans_table=self.config.tracing.postgres_spans_table,
                            events_table=self.config.tracing.postgres_events_table,
                            retention_days=self.config.tracing.postgres_retention_days,
                            batch_size=self.config.batch_size,
                            flush_interval=self.config.tracing.postgres_flush_interval
                        )
                    except ImportError as e:
                        logger.warning(f"无法创建PostgreSQL追踪器: {e}")
                        self._tracer = MemoryTracer(
                            service_name=self.config.tracing.service_name,
                            sample_rate=self.config.tracing.sample_rate
                        )
                else:
                    logger.warning(f"未知的追踪器类型: {self.config.tracing.tracer_type}, 使用内存追踪器")
                    self._tracer = MemoryTracer(
                        service_name=self.config.tracing.service_name,
                        sample_rate=self.config.tracing.sample_rate
                    )
            except Exception as e:
                logger.error(f"创建追踪器失败: {e}")
                self._tracer = MemoryTracer(
                    service_name=self.config.tracing.service_name,
                    sample_rate=self.config.tracing.sample_rate
                )
        
        # 初始化组件
        if self._metrics_recorder is not None:
            await self._metrics_recorder.initialize()
        
        if self._tracer is not None:
            await self._tracer.initialize()
        
        self._initialized = True
        logger.info("可观测性组件初始化完成")
    
    async def cleanup(self) -> None:
        """清理所有组件"""
        if not self._initialized:
            return
        
        if self._metrics_recorder is not None:
            await self._metrics_recorder.cleanup()
        
        if self._tracer is not None:
            await self._tracer.cleanup()
        
        self._initialized = False
        logger.info("可观测性组件已清理")
    
    def get_metrics_recorder(self) -> Optional[IMetricsRecorder]:
        """获取指标记录器实例
        
        Returns:
            指标记录器实例，如果未启用则返回None
        """
        return self._metrics_recorder
    
    def get_tracer(self) -> Optional[ITracer]:
        """获取分布式追踪器实例
        
        Returns:
            分布式追踪器实例，如果未启用则返回None
        """
        return self._tracer


def create_observability(config: ObservabilityConfig) -> Observability:
    """创建可观测性实例
    
    创建可观测性管理器并返回，具体组件会在调用initialize方法时创建
    
    Args:
        config: 可观测性配置
        
    Returns:
        可观测性管理器实例
    """
    return Observability(config=config) 