import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from confluent_kafka import KafkaException

from idp.framework.infrastructure.messaging.common.logging import get_logger
from idp.framework.infrastructure.messaging.common.metrics import (
    count_messages,
    processing_time,
    record_error,
    record_message_size,
    track_time,
    update_producer_queue_size,
)
from idp.framework.infrastructure.messaging.common.schemas import (
    Message,
    MessageDeliveryResult,
    MessageDeliveryStatus,
)
from idp.framework.infrastructure.messaging.config.settings import get_settings
from idp.framework.infrastructure.messaging.kafka import AsyncProducer

# Initialize logger
logger = get_logger(__name__)


class AsyncMessageProducer:
    """
    Asynchronous Kafka message producer.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
    ) -> None:
        """
        Initialize the producer.

        Args:
            client_id (Optional[str]): Client ID for the producer
            bootstrap_servers (Optional[str]): Kafka bootstrap servers
        """
        self.settings = get_settings()
        self.client_id = (
            client_id or f"{self.settings.producer.client_id_prefix}-{uuid.uuid4()}"
        )
        self.bootstrap_servers = bootstrap_servers or ",".join(
            self.settings.kafka.bootstrap_servers
        )
        self.producer: Optional[AsyncProducer] = None
        self.is_connected = False

    async def connect(self) -> None:
        """
        Connect to Kafka.
        """
        if self.is_connected:
            return

        try:
            # Create the producer
            self.producer = AsyncProducer(
                client_id=self.client_id,
                bootstrap_servers=self.bootstrap_servers,
            )
            self.is_connected = True

            logger.info(
                "Connected to Kafka",
                client_id=self.client_id,
                bootstrap_servers=self.bootstrap_servers,
            )
        except Exception as e:
            logger.error(
                "Failed to connect to Kafka",
                error=str(e),
                client_id=self.client_id,
                bootstrap_servers=self.bootstrap_servers,
            )
            # 跳过指标记录
            # record_error("", "producer", "connection_error")
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from Kafka.
        """
        if not self.is_connected or not self.producer:
            return

        try:
            await self.producer.close()
            self.is_connected = False
            logger.info(
                "Disconnected from Kafka",
                client_id=self.client_id,
            )
        except Exception as e:
            logger.error(
                "Failed to disconnect from Kafka",
                error=str(e),
                client_id=self.client_id,
            )
            # 跳过指标记录
            # record_error("", "producer", "disconnection_error")

    async def send_message(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> MessageDeliveryResult:
        """
        发送消息到指定的主题。

        Args:
            topic: 主题名称
            message: 消息内容
            key: 消息键（可选）
            headers: 消息头（可选）

        Returns:
            MessageDeliveryResult: 消息发送结果
        """
        # 生成消息ID用于跟踪
        message_id = str(uuid.uuid4())

        # 检查生产者是否已连接
        if not self.producer or not self.producer.is_connected:
            error_message = "Kafka producer is not connected"
            logger.error(
                "Failed to send message: producer not connected",
                message_id=message_id,
                topic=topic,
            )
            return MessageDeliveryResult(
                status=MessageDeliveryStatus.FAILED,
                topic=topic,
                error=error_message,
                timestamp=datetime.now().isoformat(),
                message_id=message_id,
            )

        # 准备消息头 - 确保所有值都是字符串
        message_headers = {}
        if headers:
            for k, v in headers.items():
                message_headers[k] = str(v)

        # 添加标准头信息
        message_headers.update(
            {
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(
            "Sending message to Kafka",
            message_id=message_id,
            topic=topic,
            key=key,
        )

        try:
            # 确保消息是字典类型
            if not isinstance(message, dict):
                logger.warning(
                    "Message is not a dictionary, attempting to convert",
                    message_id=message_id,
                    topic=topic,
                    message_type=type(message).__name__,
                )
                # 如果消息有 model_dump 方法（Pydantic模型），使用它
                if hasattr(message, "model_dump"):
                    message_dict = message.model_dump()
                # 如果消息有 dict 方法，使用它
                elif hasattr(message, "dict"):
                    message_dict = message.dict()
                # 否则尝试直接转换为字典
                else:
                    try:
                        message_dict = dict(message)
                    except (TypeError, ValueError):
                        # 如果无法转换为字典，则将其包装在字典中
                        message_dict = {"value": str(message)}
            else:
                message_dict = message

            # 直接发送消息，不使用回调
            await self.producer.send(
                topic=topic,
                value=message_dict,  # AsyncProducer.send 会处理字典到JSON的转换
                key=key,
                headers=message_headers,
            )

            # 发送后立即轮询以处理任何待处理的事件
            await self.producer.poll(0)

            logger.info(
                "Message sent successfully",
                message_id=message_id,
                topic=topic,
            )

            # 返回成功结果
            return MessageDeliveryResult(
                status=MessageDeliveryStatus.DELIVERED,
                topic=topic,
                timestamp=datetime.now().isoformat(),
                message_id=message_id,
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Failed to send message",
                message_id=message_id,
                topic=topic,
                error=error_message,
                exc_info=True,
            )

            # 返回失败结果
            return MessageDeliveryResult(
                status=MessageDeliveryStatus.FAILED,
                topic=topic,
                error=error_message,
                timestamp=datetime.now().isoformat(),
                message_id=message_id,
            )

    async def __aenter__(self) -> "AsyncMessageProducer":
        """
        Enter async context manager.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit async context manager.
        """
        await self.disconnect()
