from abc import ABC, abstractmethod
from typing import Callable

from .base_message import MessageEnvelope


class AbstractEventBus(ABC):
    """
    抽象事件总线，供上层微服务使用。发布领域事件、订阅领域事件处理器。
    """

    @abstractmethod
    async def publish_event(self, event_type: str, payload: dict, source: str, correlation_id: str) -> None:
        """
        发布事件。将自动封装为 MessageEnvelope。
        """
        raise NotImplementedError

    @abstractmethod
    def register_handler(self, event_type: str, handler: Callable[[MessageEnvelope], None]) -> None:
        """
        注册事件处理器。需先注册再运行订阅。
        """
        raise NotImplementedError

    @abstractmethod
    async def run_subscription(self, topic: str) -> None:
        """
        启动订阅，监听 Topic，路由消息给注册的处理器。
        """
        raise NotImplementedError
