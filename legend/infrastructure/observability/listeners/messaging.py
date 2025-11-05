"""
消息中间件监听器
用于监控消息发布、消费和处理的性能指标和链路追踪
"""
import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

from ..core import IMetricsRecorder, ITracer, SpanKind
from ..core.metadata import StandardMetrics

logger = logging.getLogger(__name__)

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])

class MessagingListener:
    """消息中间件监听器，用于监控消息操作"""

    def __init__(
        self,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
    ):
        """初始化消息中间件监听器
        
        Args:
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
        """
        self.metrics_recorder = metrics_recorder
        self.tracer = tracer
    
    def wrap_producer(
        self, 
        producer_func: F, 
        topic: str = "",
        extract_topic: Optional[Callable[[Any, Any], str]] = None
    ) -> F:
        """装饰消息生产者方法
        
        Args:
            producer_func: 生产者方法
            topic: 默认主题名称
            extract_topic: 从参数中提取主题的函数
            
        Returns:
            F: 装饰后的方法
        """
        @functools.wraps(producer_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_topic = topic
            if extract_topic:
                try:
                    extracted = extract_topic(args, kwargs)
                    if extracted:
                        current_topic = extracted
                except Exception:
                    pass
            
            start_time = time.time()
            span = None
            
            try:
                # 创建 span
                if self.tracer:
                    span_name = f"messaging.publish.{current_topic}"
                    span_attributes = {
                        "messaging.system": "generic",
                        "messaging.destination": current_topic,
                        "messaging.destination_kind": "topic",
                        "messaging.operation": "publish"
                    }
                    
                    span = self.tracer.start_span(
                        name=span_name,
                        kind=SpanKind.PRODUCER,
                        attributes=span_attributes
                    )
                    
                    # 如果消息有headers，注入trace context
                    if 'headers' in kwargs and isinstance(kwargs['headers'], dict):
                        self.tracer.inject_context(kwargs['headers'])
                
                # 执行原始方法
                result = producer_func(*args, **kwargs)
                
                # 记录发布的消息数
                msg_count = 1
                if 'count' in kwargs:
                    try:
                        msg_count = int(kwargs['count'])
                    except (ValueError, TypeError):
                        pass
                
                self.metrics_recorder.increment_counter(
                    StandardMetrics.MESSAGE_PUBLISHED.name,
                    float(msg_count),
                    {"topic": current_topic}
                )
                
                if span:
                    span.set_attribute("messaging.message_count", msg_count)
                
                return result
            except Exception as e:
                # 记录异常
                error_type = type(e).__name__
                
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", error_type)
                
                # 记录错误指标
                self.metrics_recorder.increment_counter(
                    "message_publish_errors_total",
                    1.0,
                    {"topic": current_topic, "error": error_type}
                )
                
                raise
            finally:
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录耗时指标
                self.metrics_recorder.observe_histogram(
                    "message_publish_duration_seconds",
                    duration,
                    {"topic": current_topic}
                )
                
                # 结束 span
                if span:
                    if hasattr(span, "_end_span"):
                        span._end_span()
        
        return cast(F, wrapper)
    
    def wrap_async_producer(
        self, 
        producer_func: AsyncF, 
        topic: str = "",
        extract_topic: Optional[Callable[[Any, Any], str]] = None
    ) -> AsyncF:
        """装饰异步消息生产者方法
        
        Args:
            producer_func: 异步生产者方法
            topic: 默认主题名称
            extract_topic: 从参数中提取主题的函数
            
        Returns:
            AsyncF: 装饰后的异步方法
        """
        @functools.wraps(producer_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_topic = topic
            if extract_topic:
                try:
                    extracted = extract_topic(args, kwargs)
                    if extracted:
                        current_topic = extracted
                except Exception:
                    pass
            
            start_time = time.time()
            span = None
            
            try:
                # 创建 span
                if self.tracer:
                    span_name = f"messaging.publish.{current_topic}"
                    span_attributes = {
                        "messaging.system": "generic",
                        "messaging.destination": current_topic,
                        "messaging.destination_kind": "topic",
                        "messaging.operation": "publish"
                    }
                    
                    span = await self.tracer.start_span(
                        name=span_name,
                        kind=SpanKind.PRODUCER,
                        attributes=span_attributes
                    )
                    
                    # 如果消息有headers，注入trace context
                    if 'headers' in kwargs and isinstance(kwargs['headers'], dict):
                        self.tracer.inject_context(kwargs['headers'])
                
                # 执行原始方法
                result = await producer_func(*args, **kwargs)
                
                # 记录发布的消息数
                msg_count = 1
                if 'count' in kwargs:
                    try:
                        msg_count = int(kwargs['count'])
                    except (ValueError, TypeError):
                        pass
                
                await self.metrics_recorder.increment_counter(
                    StandardMetrics.MESSAGE_PUBLISHED.name,
                    float(msg_count),
                    {"topic": current_topic}
                )
                
                if span:
                    span.set_attribute("messaging.message_count", msg_count)
                
                return result
            except Exception as e:
                # 记录异常
                error_type = type(e).__name__
                
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", error_type)
                
                # 记录错误指标
                await self.metrics_recorder.increment_counter(
                    "message_publish_errors_total",
                    1.0,
                    {"topic": current_topic, "error": error_type}
                )
                
                raise
            finally:
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录耗时指标
                await self.metrics_recorder.observe_histogram(
                    "message_publish_duration_seconds",
                    duration,
                    {"topic": current_topic}
                )
                
                # 结束 span
                if span:
                    await span._end_span()
        
        return cast(AsyncF, wrapper)
    
    def wrap_consumer(
        self, 
        consumer_func: F, 
        topic: str = "",
        consumer_group: str = "default",
        extract_topic: Optional[Callable[[Any, Any], str]] = None,
        extract_context: Optional[Callable[[Any, Any], Dict[str, str]]] = None
    ) -> F:
        """装饰消息消费者方法
        
        Args:
            consumer_func: 消费者方法
            topic: 默认主题名称
            consumer_group: 消费者组名称
            extract_topic: 从参数中提取主题的函数
            extract_context: 从消息中提取追踪上下文的函数
            
        Returns:
            F: 装饰后的方法
        """
        @functools.wraps(consumer_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_topic = topic
            if extract_topic:
                try:
                    extracted = extract_topic(args, kwargs)
                    if extracted:
                        current_topic = extracted
                except Exception:
                    pass
            
            start_time = time.time()
            span = None
            
            try:
                # 提取追踪上下文
                context = {}
                if extract_context and self.tracer:
                    try:
                        context = extract_context(args, kwargs) or {}
                        if context:
                            self.tracer.extract_context(context)
                    except Exception as e:
                        logger.debug(f"Error extracting trace context: {e}")
                
                # 创建 span
                if self.tracer:
                    span_name = f"messaging.consume.{current_topic}"
                    span_attributes = {
                        "messaging.system": "generic",
                        "messaging.destination": current_topic,
                        "messaging.destination_kind": "topic",
                        "messaging.operation": "receive",
                        "messaging.consumer_group": consumer_group
                    }
                    
                    span = self.tracer.start_span(
                        name=span_name,
                        kind=SpanKind.CONSUMER,
                        attributes=span_attributes
                    )
                
                # 执行原始方法
                result = consumer_func(*args, **kwargs)
                
                # 记录消费的消息数
                msg_count = 1
                if 'count' in kwargs:
                    try:
                        msg_count = int(kwargs['count'])
                    except (ValueError, TypeError):
                        pass
                
                self.metrics_recorder.increment_counter(
                    StandardMetrics.MESSAGE_CONSUMED.name,
                    float(msg_count),
                    {"topic": current_topic, "consumer": consumer_group}
                )
                
                if span:
                    span.set_attribute("messaging.message_count", msg_count)
                
                return result
            except Exception as e:
                # 记录异常
                error_type = type(e).__name__
                
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", error_type)
                
                # 记录错误指标
                self.metrics_recorder.increment_counter(
                    "message_consume_errors_total",
                    1.0,
                    {"topic": current_topic, "consumer": consumer_group, "error": error_type}
                )
                
                raise
            finally:
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录耗时指标
                self.metrics_recorder.observe_histogram(
                    StandardMetrics.MESSAGE_PROCESSING_DURATION.name,
                    duration,
                    {"topic": current_topic}
                )
                
                # 结束 span
                if span:
                    if hasattr(span, "_end_span"):
                        span._end_span()
        
        return cast(F, wrapper)
    
    def wrap_async_consumer(
        self, 
        consumer_func: AsyncF, 
        topic: str = "",
        consumer_group: str = "default",
        extract_topic: Optional[Callable[[Any, Any], str]] = None,
        extract_context: Optional[Callable[[Any, Any], Dict[str, str]]] = None
    ) -> AsyncF:
        """装饰异步消息消费者方法
        
        Args:
            consumer_func: 异步消费者方法
            topic: 默认主题名称
            consumer_group: 消费者组名称
            extract_topic: 从参数中提取主题的函数
            extract_context: 从消息中提取追踪上下文的函数
            
        Returns:
            AsyncF: 装饰后的异步方法
        """
        @functools.wraps(consumer_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_topic = topic
            if extract_topic:
                try:
                    extracted = extract_topic(args, kwargs)
                    if extracted:
                        current_topic = extracted
                except Exception:
                    pass
            
            start_time = time.time()
            span = None
            
            try:
                # 提取追踪上下文
                context = {}
                if extract_context and self.tracer:
                    try:
                        context = extract_context(args, kwargs) or {}
                        if context:
                            self.tracer.extract_context(context)
                    except Exception as e:
                        logger.debug(f"Error extracting trace context: {e}")
                
                # 创建 span
                if self.tracer:
                    span_name = f"messaging.consume.{current_topic}"
                    span_attributes = {
                        "messaging.system": "generic",
                        "messaging.destination": current_topic,
                        "messaging.destination_kind": "topic",
                        "messaging.operation": "receive",
                        "messaging.consumer_group": consumer_group
                    }
                    
                    span = await self.tracer.start_span(
                        name=span_name,
                        kind=SpanKind.CONSUMER,
                        attributes=span_attributes
                    )
                
                # 执行原始方法
                result = await consumer_func(*args, **kwargs)
                
                # 记录消费的消息数
                msg_count = 1
                if 'count' in kwargs:
                    try:
                        msg_count = int(kwargs['count'])
                    except (ValueError, TypeError):
                        pass
                
                await self.metrics_recorder.increment_counter(
                    StandardMetrics.MESSAGE_CONSUMED.name,
                    float(msg_count),
                    {"topic": current_topic, "consumer": consumer_group}
                )
                
                if span:
                    span.set_attribute("messaging.message_count", msg_count)
                
                return result
            except Exception as e:
                # 记录异常
                error_type = type(e).__name__
                
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", error_type)
                
                # 记录错误指标
                await self.metrics_recorder.increment_counter(
                    "message_consume_errors_total",
                    1.0,
                    {"topic": current_topic, "consumer": consumer_group, "error": error_type}
                )
                
                raise
            finally:
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录耗时指标
                await self.metrics_recorder.observe_histogram(
                    StandardMetrics.MESSAGE_PROCESSING_DURATION.name,
                    duration,
                    {"topic": current_topic}
                )
                
                # 结束 span
                if span:
                    await span._end_span()
        
        return cast(AsyncF, wrapper)
    
    # 特定中间件的适配器
    def instrument_kafka_producer(self, producer: Any) -> Any:
        """监控Kafka生产者
        
        Args:
            producer: Kafka生产者实例
            
        Returns:
            Any: 装饰后的生产者实例
        """
        if hasattr(producer, 'send'):
            original_send = producer.send
            
            def extract_topic(args, kwargs):
                if args and len(args) > 1:
                    return str(args[1])
                return kwargs.get('topic', '')
            
            # 使用适当的包装器
            if asyncio.iscoroutinefunction(original_send):
                wrapped = self.wrap_async_producer(original_send, extract_topic=extract_topic)
            else:
                wrapped = self.wrap_producer(original_send, extract_topic=extract_topic)
            
            producer.send = wrapped
        
        return producer
    
    def instrument_kafka_consumer(self, consumer: Any, consumer_group: str = "default") -> Any:
        """监控Kafka消费者
        
        Args:
            consumer: Kafka消费者实例
            consumer_group: 消费者组名称
            
        Returns:
            Any: 装饰后的消费者实例
        """
        # 提取headers中的跟踪上下文
        def extract_context(args, kwargs):
            if args and len(args) > 1:
                if hasattr(args[1], 'headers'):
                    headers = args[1].headers
                    if headers and isinstance(headers, dict):
                        return headers
            return {}
        
        for method_name in ['poll', 'consume']:
            if hasattr(consumer, method_name):
                original_method = getattr(consumer, method_name)
                
                if asyncio.iscoroutinefunction(original_method):
                    wrapped = self.wrap_async_consumer(
                        original_method, 
                        consumer_group=consumer_group,
                        extract_context=extract_context
                    )
                else:
                    wrapped = self.wrap_consumer(
                        original_method, 
                        consumer_group=consumer_group,
                        extract_context=extract_context
                    )
                
                setattr(consumer, method_name, wrapped)
        
        return consumer
    
    def instrument_rabbitmq_producer(self, channel: Any) -> Any:
        """监控RabbitMQ生产者
        
        Args:
            channel: RabbitMQ通道实例
            
        Returns:
            Any: 装饰后的通道实例
        """
        if hasattr(channel, 'basic_publish'):
            original_publish = channel.basic_publish
            
            def extract_topic(args, kwargs):
                # 对于RabbitMQ，使用exchange和routing_key组合
                exchange = kwargs.get('exchange', '')
                routing_key = kwargs.get('routing_key', '')
                if exchange and routing_key:
                    return f"{exchange}.{routing_key}"
                elif exchange:
                    return exchange
                elif routing_key:
                    return routing_key
                return ''
            
            # 使用适当的包装器
            if asyncio.iscoroutinefunction(original_publish):
                wrapped = self.wrap_async_producer(original_publish, extract_topic=extract_topic)
            else:
                wrapped = self.wrap_producer(original_publish, extract_topic=extract_topic)
            
            channel.basic_publish = wrapped
        
        return channel
    
    def instrument_rabbitmq_consumer(self, channel: Any, consumer_tag: str = "default") -> Any:
        """监控RabbitMQ消费者
        
        Args:
            channel: RabbitMQ通道实例
            consumer_tag: 消费者标签
            
        Returns:
            Any: 装饰后的通道实例
        """
        # 提取headers中的跟踪上下文
        def extract_context(args, kwargs):
            if 'properties' in kwargs and hasattr(kwargs['properties'], 'headers'):
                headers = kwargs['properties'].headers
                if headers and isinstance(headers, dict):
                    return headers
            return {}
        
        for method_name in ['basic_consume', 'basic_get']:
            if hasattr(channel, method_name):
                original_method = getattr(channel, method_name)
                
                if asyncio.iscoroutinefunction(original_method):
                    wrapped = self.wrap_async_consumer(
                        original_method, 
                        consumer_group=consumer_tag,
                        extract_context=extract_context
                    )
                else:
                    wrapped = self.wrap_consumer(
                        original_method, 
                        consumer_group=consumer_tag,
                        extract_context=extract_context
                    )
                
                setattr(channel, method_name, wrapped)
        
        return channel
    
    def instrument_pulsar_producer(self, producer: Any) -> Any:
        """监控Pulsar生产者
        
        Args:
            producer: Pulsar生产者实例
            
        Returns:
            Any: 装饰后的生产者实例
        """
        if hasattr(producer, 'send'):
            original_send = producer.send
            
            # 使用适当的包装器
            if asyncio.iscoroutinefunction(original_send):
                wrapped = self.wrap_async_producer(original_send, topic=producer.topic)
            else:
                wrapped = self.wrap_producer(original_send, topic=producer.topic)
            
            producer.send = wrapped
        
        return producer
    
    def instrument_pulsar_consumer(self, consumer: Any) -> Any:
        """监控Pulsar消费者
        
        Args:
            consumer: Pulsar消费者实例
            
        Returns:
            Any: 装饰后的消费者实例
        """
        # 提取headers中的跟踪上下文
        def extract_context(args, kwargs):
            if len(args) > 1 and hasattr(args[1], 'properties'):
                properties = args[1].properties
                if properties and isinstance(properties, dict):
                    return properties
            return {}
        
        consumer_group = getattr(consumer, 'subscription_name', 'default')
        topic = getattr(consumer, 'topic', '')
        
        for method_name in ['receive', 'read_next']:
            if hasattr(consumer, method_name):
                original_method = getattr(consumer, method_name)
                
                if asyncio.iscoroutinefunction(original_method):
                    wrapped = self.wrap_async_consumer(
                        original_method, 
                        topic=topic,
                        consumer_group=consumer_group,
                        extract_context=extract_context
                    )
                else:
                    wrapped = self.wrap_consumer(
                        original_method, 
                        topic=topic,
                        consumer_group=consumer_group,
                        extract_context=extract_context
                    )
                
                setattr(consumer, method_name, wrapped)
        
        return consumer
    
    @classmethod
    def install_kafka_producer(
        cls,
        producer: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
    ) -> "MessagingListener":
        """安装Kafka生产者监听器
        
        Args:
            producer: Kafka生产者实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            
        Returns:
            MessagingListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer)
        listener.instrument_kafka_producer(producer)
        return listener
    
    @classmethod
    def install_kafka_consumer(
        cls,
        consumer: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
        consumer_group: str = "default",
    ) -> "MessagingListener":
        """安装Kafka消费者监听器
        
        Args:
            consumer: Kafka消费者实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            consumer_group: 消费者组名称
            
        Returns:
            MessagingListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer)
        listener.instrument_kafka_consumer(consumer, consumer_group)
        return listener
    
    @classmethod
    def install_rabbitmq_producer(
        cls,
        channel: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
    ) -> "MessagingListener":
        """安装RabbitMQ生产者监听器
        
        Args:
            channel: RabbitMQ通道实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            
        Returns:
            MessagingListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer)
        listener.instrument_rabbitmq_producer(channel)
        return listener
    
    @classmethod
    def install_rabbitmq_consumer(
        cls,
        channel: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
        consumer_tag: str = "default",
    ) -> "MessagingListener":
        """安装RabbitMQ消费者监听器
        
        Args:
            channel: RabbitMQ通道实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            consumer_tag: 消费者标签
            
        Returns:
            MessagingListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer)
        listener.instrument_rabbitmq_consumer(channel, consumer_tag)
        return listener
    
    @classmethod
    def install_pulsar_producer(
        cls,
        producer: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
    ) -> "MessagingListener":
        """安装Pulsar生产者监听器
        
        Args:
            producer: Pulsar生产者实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            
        Returns:
            MessagingListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer)
        listener.instrument_pulsar_producer(producer)
        return listener
    
    @classmethod
    def install_pulsar_consumer(
        cls,
        consumer: Any,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
    ) -> "MessagingListener":
        """安装Pulsar消费者监听器
        
        Args:
            consumer: Pulsar消费者实例
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            
        Returns:
            MessagingListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer)
        listener.instrument_pulsar_consumer(consumer)
        return listener
    
# 使用示例
"""
# Kafka Producer
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers='localhost:9092')
listener = MessagingListener.install_kafka_producer(
    producer,
    metrics_recorder,
    tracer
)

# 使用被监控的producer发送消息
producer.send('my-topic', b'message value')

# Kafka Consumer
from kafka import KafkaConsumer

consumer = KafkaConsumer('my-topic', group_id='my-group')
listener = MessagingListener.install_kafka_consumer(
    consumer,
    metrics_recorder,
    tracer,
    consumer_group='my-group'
)

# 使用被监控的consumer消费消息
for message in consumer:
    print(message)
""" 