"""
链路追踪器工厂
"""
import logging
from enum import Enum, auto
from typing import Dict, Optional, Type, Union

from idp.framework.infrastructure.observability.core.config import TracingConfig

from .memory import MemoryTracer
from .postgres import PostgresTracer, PostgresTracingConfig
from .sentry import SentryTracer
from .tracer import BaseTracer

logger = logging.getLogger(__name__)

class TracerType(Enum):
    """追踪器类型"""
    MEMORY = auto()
    SENTRY = auto()
    POSTGRES = auto()  # 新增PostgreSQL类型
    # 未来可以添加更多类型，如 OPENTELEMETRY, DATADOG 等

class TracerFactory:
    """追踪器工厂，用于创建不同类型的追踪器实例"""
    
    _tracer_classes: Dict[TracerType, Type[BaseTracer]] = {
        TracerType.MEMORY: MemoryTracer,
        TracerType.SENTRY: SentryTracer,
        TracerType.POSTGRES: PostgresTracer,  # 新增PostgreSQL追踪器
    }
    
    @classmethod
    def create(
        cls,
        tracer_type: Union[TracerType, str],
        service_name: str,
        sample_rate: float = 1.0,
        **kwargs
    ) -> BaseTracer:
        """创建追踪器实例
        
        Args:
            tracer_type: 追踪器类型，可以是TracerType枚举或字符串
            service_name: 服务名称
            sample_rate: 采样率，默认为1.0（全量采样）
            **kwargs: 额外的参数，会传递给具体的追踪器实现
            
        Returns:
            BaseTracer: 追踪器实例
            
        Raises:
            ValueError: 如果提供了无效的追踪器类型
        """
        # 如果提供的是字符串，转换为枚举类型
        if isinstance(tracer_type, str):
            try:
                tracer_type = TracerType[tracer_type.upper()]
            except KeyError:
                valid_types = ", ".join([t.name for t in TracerType])
                raise ValueError(
                    f"Invalid tracer type: {tracer_type}. Valid types are: {valid_types}"
                )
        
        # 获取追踪器类
        if tracer_type not in cls._tracer_classes:
            valid_types = ", ".join([t.name for t in TracerType])
            raise ValueError(
                f"Unsupported tracer type: {tracer_type}. Supported types are: {valid_types}"
            )
        
        tracer_class = cls._tracer_classes[tracer_type]
        
        # 根据追踪器类型创建实例
        logger.debug(f"Creating tracer of type {tracer_type}")
        
        if tracer_type == TracerType.MEMORY:
            max_spans = kwargs.get('max_spans', 1000)
            return MemoryTracer(service_name, sample_rate, max_spans)
            
        elif tracer_type == TracerType.SENTRY:
            dsn = kwargs.get('dsn')
            if not dsn:
                raise ValueError("DSN must be provided for Sentry tracer")
                
            traces_sample_rate = kwargs.get('traces_sample_rate', sample_rate)
            environment = kwargs.get('environment', 'development')
            release = kwargs.get('release')
            
            return SentryTracer(
                service_name=service_name,
                dsn=dsn,
                sample_rate=traces_sample_rate,
                environment=environment,
                release=release
            )
            
        elif tracer_type == TracerType.POSTGRES:
            # 检查是否提供了PostgreSQL配置
            postgres_config = kwargs.get('postgres_config')
            connection_string = kwargs.get('connection_string')
            
            if not postgres_config and not connection_string:
                raise ValueError("Either postgres_config or connection_string must be provided for PostgreSQL tracer")
            
            if postgres_config:
                # 使用提供的PostgreSQL配置创建追踪器
                return PostgresTracer.from_config(
                    postgres_config,
                    service_name=service_name,
                    sample_rate=sample_rate
                )
            else:
                # 使用连接字符串创建追踪器
                return PostgresTracer(
                    service_name=service_name,
                    connection_string=connection_string,
                    sample_rate=sample_rate,
                    spans_table_name=kwargs.get('spans_table_name', "observability_spans"),
                    events_table_name=kwargs.get('events_table_name', "observability_span_events"),
                    schema_name=kwargs.get('schema_name', "public"),
                    retention_days=kwargs.get('retention_days', 30),
                    batch_size=kwargs.get('batch_size', 100),
                    flush_interval=kwargs.get('flush_interval', 5.0)
                )
        
        # 兜底情况 - 这一般不会发生，因为我们已经验证了追踪器类型
        raise ValueError(f"Unsupported tracer type: {tracer_type}")
    
    @classmethod
    def register_tracer_class(
        cls, 
        tracer_type: TracerType, 
        tracer_class: Type[BaseTracer]
    ) -> None:
        """注册新的追踪器类型和对应的类
        
        Args:
            tracer_type: 追踪器类型
            tracer_class: 追踪器类
        """
        cls._tracer_classes[tracer_type] = tracer_class
        logger.debug(f"Registered new tracer type: {tracer_type}")
    
    @classmethod
    def create_from_config(cls, config: TracingConfig, **kwargs) -> BaseTracer:
        """从配置创建追踪器
        
        Args:
            config: 追踪配置
            **kwargs: 额外的参数，会传递给具体的追踪器实现
            
        Returns:
            BaseTracer: 追踪器实例
        """
        if not config.enabled:
            # 如果未启用追踪，默认使用内存追踪器
            logger.debug("Tracing is disabled, using memory tracer")
            return cls.create(
                tracer_type=TracerType.MEMORY,
                service_name=config.service_name,
                sample_rate=0.0  # 设置采样率为0，不会实际采集
            )
        
        tracer_type_str = kwargs.pop('tracer_type', None) or config.tracer_type or "MEMORY"
        
        # 根据配置选择追踪器类型和参数
        if tracer_type_str.upper() == "SENTRY" and config.sentry_dsn:
            return cls.create(
                tracer_type=TracerType.SENTRY,
                service_name=config.service_name,
                sample_rate=config.sample_rate,
                dsn=config.sentry_dsn,
                environment=kwargs.get('environment', 'development'),
                release=kwargs.get('release')
            )
        elif tracer_type_str.upper() == "POSTGRES":
            # 检查是否提供了PostgreSQL配置
            postgres_config = kwargs.get('postgres_config')
            connection_string = kwargs.get('connection_string')
            
            if not postgres_config and not connection_string:
                raise ValueError("Either postgres_config or connection_string must be provided for PostgreSQL tracer")
                
            return cls.create(
                tracer_type=TracerType.POSTGRES,
                service_name=config.service_name,
                sample_rate=config.sample_rate,
                **kwargs
            )
        else:
            # 默认使用内存追踪器
            return cls.create(
                tracer_type=TracerType.MEMORY,
                service_name=config.service_name,
                sample_rate=config.sample_rate,
                max_spans=kwargs.get('max_spans', 1000)
            ) 