from abc import ABC, abstractmethod

from .base_message import MessageEnvelope


class AbstractMessageBus(ABC):
    """
    抽象消息总线接口，方便依赖注入，支持多种中间件
    """

    @abstractmethod
    async def publish(self, topic: str, message: MessageEnvelope) -> None:
        """
        发布一个消息到指定 topic
        """
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, topic: str, handler: callable) -> None:
        """
        订阅某个 topic，处理函数 handler 需接收 MessageEnvelope
        """
        raise NotImplementedError
