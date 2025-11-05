import asyncio
import json
from typing import Callable, Optional

from pulsar import ConsumerType

from ..core.base_message import MessageEnvelope
from ..core.codec import MessageCodec, get_codec
from ..core.event_bus import AbstractEventBus
from ..dispatcher.registry import get_handlers, register
from .client import get_pulsar_client


class PulsarEventBus(AbstractEventBus):
    """
    Pulsar 实现的事件总线
    支持自定义编解码器：json, protobuf, avro
    """
    
    def __init__(self, codec_name: str = "json", codec: Optional[MessageCodec] = None):
        """
        初始化 Pulsar 事件总线
        
        参数:
            codec_name: 编解码器名称，可选值: "json", "protobuf", "avro"
            codec: 自定义编解码器实例，如提供则优先使用
        """
        self.client = get_pulsar_client()
        self.producers = {}
        # 允许直接传入编解码器实例，否则按名称获取
        self.codec = codec if codec else get_codec(codec_name)

    async def publish_event(self, event_type: str, payload: dict, source: str, correlation_id: str) -> None:
        """
        发布事件。将自动封装为 MessageEnvelope
        
        参数:
            event_type: 事件类型
            payload: 事件数据
            source: 事件来源
            correlation_id: 关联ID，用于跟踪请求
        """
        topic = f"persistent://public/default/{event_type}"
        if topic not in self.producers:
            self.producers[topic] = self.client.create_producer(topic)

        envelope = MessageEnvelope(
            event_type=event_type,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
        )
        serialized = self.codec.encode(envelope)
        self.producers[topic].send(serialized)

    def register_handler(self, event_type: str, handler: Callable[[MessageEnvelope], None]) -> None:
        """
        注册事件处理器。需先注册再运行订阅
        
        参数:
            event_type: 事件类型
            handler: 处理函数，接收 MessageEnvelope 参数
        """
        register(event_type, handler)

    async def run_subscription(self, topic: str) -> None:
        """
        启动订阅，监听 Topic，路由消息给注册的处理器
        
        参数:
            topic: 要订阅的主题
        """
        consumer = self.client.subscribe(
            topic,
            subscription_name="default-sub",
            consumer_type=ConsumerType.Shared
        )
        while True:
            msg = consumer.receive()
            try:
                envelope = self.codec.decode(msg.data())
                handlers = get_handlers(envelope.event_type)
                
                # 如果没有处理器，记录并确认消息
                if not handlers:
                    print(f"Warning: No handlers registered for event type: {envelope.event_type}")
                    consumer.acknowledge(msg)
                    continue
                
                # 执行所有注册的处理器
                for handler in handlers:
                    await handler(envelope)
                
                # 所有处理器执行成功后确认消息
                consumer.acknowledge(msg)
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                # 处理失败，将消息标记为未处理（可以触发重试策略）
                consumer.negative_acknowledge(msg)
                # TODO: log error / metrics hook
