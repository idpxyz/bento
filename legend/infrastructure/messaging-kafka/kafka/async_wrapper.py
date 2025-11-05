import asyncio
import functools
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient, NewPartitions, NewTopic
from confluent_kafka.schema_registry import SchemaRegistryClient

from idp.framework.infrastructure.messaging.common.logging import get_logger
from idp.framework.infrastructure.messaging.config.settings import get_settings

# 初始化日志记录器
logger = get_logger(__name__)


def json_serializer(obj: Any) -> str:
    """
    自定义 JSON 序列化器，处理特殊类型如 UUID 和 datetime。

    Args:
        obj: 要序列化的对象

    Returns:
        str: 序列化后的字符串表示
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    elif hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        return obj.dict()
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# 类型变量用于泛型函数签名
T = TypeVar("T")

# 全局线程池，用于异步执行同步 Kafka 操作
_thread_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="kafka_async_")


async def run_in_executor(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    在线程池中异步执行同步函数。

    Args:
        func: 要执行的同步函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数的返回值
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _thread_pool, functools.partial(func, *args, **kwargs)
    )


class AsyncProducer:
    """
    confluent-kafka Producer 的异步封装。
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化异步生产者。

        Args:
            client_id: 客户端 ID
            bootstrap_servers: Kafka 服务器地址
            **kwargs: 其他 Kafka 配置参数
        """
        self.settings = get_settings()
        self.client_id = (
            client_id or f"{self.settings.producer.client_id_prefix}-{uuid.uuid4()}"
        )

        # Force use of explicitly provided bootstrap servers and ensure it's not empty
        if bootstrap_servers:
            self.bootstrap_servers = bootstrap_servers
            # Make sure environment variables are consistent
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = bootstrap_servers
        elif os.environ.get("KAFKA_BOOTSTRAP_SERVERS"):
            self.bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
        else:
            self.bootstrap_servers = ",".join(self.settings.kafka.bootstrap_servers)
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = self.bootstrap_servers

        logger.info(f"AsyncProducer using bootstrap servers: {self.bootstrap_servers}")

        # 创建配置
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
            "acks": self.settings.producer.acks,
            "compression.type": self.settings.producer.compression_type,
            "batch.size": self.settings.producer.batch_size,
            "linger.ms": self.settings.producer.linger_ms,
            "retries": self.settings.producer.retries,
            "max.in.flight.requests.per.connection": self.settings.producer.max_in_flight,
            "enable.idempotence": self.settings.producer.idempotence,
            "delivery.timeout.ms": self.settings.producer.delivery_timeout_ms,
            **kwargs,
        }

        # 添加安全配置（如果需要）
        if self.settings.kafka.security_protocol != "PLAINTEXT":
            config["security.protocol"] = self.settings.kafka.security_protocol

            if self.settings.kafka.sasl_mechanism:
                config["sasl.mechanism"] = self.settings.kafka.sasl_mechanism

            if self.settings.kafka.sasl_username and self.settings.kafka.sasl_password:
                config["sasl.username"] = self.settings.kafka.sasl_username
                config["sasl.password"] = self.settings.kafka.sasl_password

        # 创建同步生产者
        try:
            self.producer = Producer(config)
            self.is_connected = True

            logger.info(
                "Kafka producer initialized",
                client_id=self.client_id,
                bootstrap_servers=self.bootstrap_servers,
            )
        except Exception as e:
            self.is_connected = False
            logger.error(
                "Failed to initialize Kafka producer",
                error=str(e),
                client_id=self.client_id,
                bootstrap_servers=self.bootstrap_servers,
            )
            raise

    async def flush(self, timeout: float = -1) -> None:
        """
        异步刷新所有消息。

        Args:
            timeout: 超时时间（秒）
        """
        if not self.is_connected:
            logger.warning("Cannot flush: producer is not connected")
            return

        try:
            await run_in_executor(self.producer.flush, timeout)
        except Exception as e:
            logger.error(
                "Error during flush",
                error=str(e),
            )
            raise

    async def send(
        self,
        topic: str,
        value: Union[str, bytes, Dict[str, Any]],
        key: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: Optional[int] = None,
        timestamp: Optional[int] = None,
        on_delivery: Optional[Callable[[KafkaError, Message], None]] = None,
    ) -> None:
        """
        异步发送消息到 Kafka。

        Args:
            topic: 主题
            value: 消息值
            key: 消息键
            headers: 消息头
            partition: 分区
            timestamp: 时间戳
            on_delivery: 交付回调
        """
        if not self.is_connected:
            error_msg = "Cannot send message: producer is not connected"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # 处理值
        try:
            if isinstance(value, dict):
                # 使用自定义 JSON 编码器处理 UUID 和其他特殊类型
                value = json.dumps(value, default=json_serializer).encode("utf-8")
            elif isinstance(value, str):
                value = value.encode("utf-8")

            # 处理键
            if isinstance(key, str):
                key = key.encode("utf-8")

            # 处理头
            kafka_headers = None
            if headers:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]
        except Exception as e:
            error_msg = f"Error preparing message: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        # 使用线程池异步发送消息
        try:
            logger.debug(
                "Sending message to Kafka",
                topic=topic,
                partition=partition,
            )

            # 准备参数，移除所有 None 值
            produce_kwargs = {
                "topic": topic,
                "value": value,
            }

            if key is not None:
                produce_kwargs["key"] = key

            if kafka_headers is not None:
                produce_kwargs["headers"] = kafka_headers

            if partition is not None:
                produce_kwargs["partition"] = partition

            if timestamp is not None:
                produce_kwargs["timestamp"] = timestamp

            if on_delivery is not None:
                produce_kwargs["on_delivery"] = on_delivery

            # 发送消息
            await run_in_executor(self.producer.produce, **produce_kwargs)

            logger.debug(
                "Message sent to Kafka (queued)",
                topic=topic,
                partition=partition,
            )
        except Exception as e:
            # 如果发送失败，记录错误但不调用回调
            # 回调机制在这里可能导致问题，所以我们完全跳过它
            error_msg = f"Failed to send message to topic {topic}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def poll(self, timeout: float = 0) -> None:
        """
        异步轮询 Kafka 事件。

        Args:
            timeout: 超时时间（秒）
        """
        if not self.is_connected:
            logger.warning("Cannot poll: producer is not connected")
            return

        try:
            await run_in_executor(self.producer.poll, timeout)
        except Exception as e:
            logger.error(
                "Error during poll",
                error=str(e),
            )
            raise

    async def close(self) -> None:
        """
        异步关闭生产者。
        """
        if not self.is_connected:
            logger.warning("Cannot close: producer is not connected")
            return

        try:
            await self.flush(timeout=10)
            self.is_connected = False
            logger.info(
                "Kafka producer closed",
                client_id=self.client_id,
            )
        except Exception as e:
            logger.error(
                "Error during close",
                error=str(e),
            )
            self.is_connected = False
            raise

    async def __aenter__(self) -> "AsyncProducer":
        """
        异步上下文管理器入口。
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        异步上下文管理器退出。
        """
        await self.close()


class AsyncConsumer:
    """
    confluent-kafka Consumer 的异步封装。
    """

    def __init__(
        self,
        group_id: str,
        topics: Optional[List[str]] = None,
        client_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        auto_commit: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化异步消费者。

        Args:
            group_id: 消费者组 ID
            topics: 要订阅的主题列表
            client_id: 客户端 ID
            bootstrap_servers: Kafka 服务器地址
            auto_commit: 是否自动提交偏移量
            **kwargs: 其他 Kafka 配置参数
        """
        self.settings = get_settings()
        self.group_id = f"{self.settings.consumer.group_id_prefix}-{group_id}"
        self.client_id = client_id or f"{self.group_id}-{uuid.uuid4()}"

        # Force use of explicitly provided bootstrap servers and ensure it's not empty
        if bootstrap_servers:
            self.bootstrap_servers = bootstrap_servers
            # Make sure environment variables are consistent
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = bootstrap_servers
        elif os.environ.get("KAFKA_BOOTSTRAP_SERVERS"):
            self.bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
        else:
            self.bootstrap_servers = ",".join(self.settings.kafka.bootstrap_servers)
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = self.bootstrap_servers

        logger.info(f"AsyncConsumer using bootstrap servers: {self.bootstrap_servers}")

        self.topics = topics or []
        self.auto_commit = (
            auto_commit
            if auto_commit is not None
            else self.settings.consumer.enable_auto_commit
        )

        # 创建配置
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "client.id": self.client_id,
            "auto.offset.reset": self.settings.consumer.auto_offset_reset,
            "enable.auto.commit": self.auto_commit,
            "max.poll.interval.ms": self.settings.consumer.max_poll_interval_ms,
            "session.timeout.ms": self.settings.consumer.session_timeout_ms,
            "heartbeat.interval.ms": self.settings.consumer.heartbeat_interval_ms,
            "isolation.level": self.settings.consumer.isolation_level,
            **kwargs,
        }

        # 添加安全配置（如果需要）
        if self.settings.kafka.security_protocol != "PLAINTEXT":
            config["security.protocol"] = self.settings.kafka.security_protocol

            if self.settings.kafka.sasl_mechanism:
                config["sasl.mechanism"] = self.settings.kafka.sasl_mechanism

            if self.settings.kafka.sasl_username and self.settings.kafka.sasl_password:
                config["sasl.username"] = self.settings.kafka.sasl_username
                config["sasl.password"] = self.settings.kafka.sasl_password

        # 创建同步消费者
        self.consumer = Consumer(config)
        self.is_connected = True

        # 如果提供了主题，则订阅
        if self.topics:
            self.consumer.subscribe(self.topics)

        logger.info(
            "Kafka consumer initialized",
            client_id=self.client_id,
            group_id=self.group_id,
            topics=self.topics,
            bootstrap_servers=self.bootstrap_servers,
        )

    async def subscribe(self, topics: List[str]) -> None:
        """
        异步订阅主题。

        Args:
            topics: 要订阅的主题列表
        """
        self.topics = topics
        await run_in_executor(self.consumer.subscribe, topics)

    async def unsubscribe(self) -> None:
        """
        异步取消订阅所有主题。
        """
        self.topics = []
        await run_in_executor(self.consumer.unsubscribe)

    async def poll(self, timeout: float = 1.0) -> Optional[Message]:
        """
        异步轮询消息。

        Args:
            timeout: 超时时间（秒）

        Returns:
            消息对象，如果没有消息则为 None
        """
        return await run_in_executor(self.consumer.poll, timeout)

    async def consume(
        self, num_messages: int = 1, timeout: float = 1.0
    ) -> List[Message]:
        """
        异步消费多条消息。

        Args:
            num_messages: 要消费的消息数量
            timeout: 超时时间（秒）

        Returns:
            消息列表
        """
        return await run_in_executor(self.consumer.consume, num_messages, timeout)

    async def commit(
        self,
        message: Optional[Message] = None,
        offsets: Optional[List[TopicPartition]] = None,
        asynchronous: bool = False,
    ) -> None:
        """
        异步提交偏移量。

        Args:
            message: 要提交的消息
            offsets: 要提交的偏移量列表
            asynchronous: 是否异步提交
        """
        await run_in_executor(self.consumer.commit, message, offsets, asynchronous)

    async def close(self) -> None:
        """
        异步关闭消费者。
        """
        if self.is_connected:
            await run_in_executor(self.consumer.close)
            self.is_connected = False
            logger.info(
                "Kafka consumer closed",
                client_id=self.client_id,
                group_id=self.group_id,
            )

    async def get_watermark_offsets(self, partition: TopicPartition) -> tuple[int, int]:
        """
        异步获取水位线偏移量。

        Args:
            partition: 主题分区

        Returns:
            (低水位线, 高水位线) 元组
        """
        return await run_in_executor(self.consumer.get_watermark_offsets, partition)

    async def __aenter__(self) -> "AsyncConsumer":
        """
        异步上下文管理器入口。
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        异步上下文管理器退出。
        """
        await self.close()


class AsyncAdminClient:
    """
    confluent-kafka AdminClient 的异步封装。
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化异步管理客户端。

        Args:
            client_id: 客户端 ID
            bootstrap_servers: Kafka 服务器地址
            **kwargs: 其他 Kafka 配置参数
        """
        self.settings = get_settings()
        self.client_id = client_id or f"admin-{uuid.uuid4()}"
        self.bootstrap_servers = bootstrap_servers or ",".join(
            self.settings.kafka.bootstrap_servers
        )

        # 创建配置
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
            **kwargs,
        }

        # 添加安全配置（如果需要）
        if self.settings.kafka.security_protocol != "PLAINTEXT":
            config["security.protocol"] = self.settings.kafka.security_protocol

            if self.settings.kafka.sasl_mechanism:
                config["sasl.mechanism"] = self.settings.kafka.sasl_mechanism

            if self.settings.kafka.sasl_username and self.settings.kafka.sasl_password:
                config["sasl.username"] = self.settings.kafka.sasl_username
                config["sasl.password"] = self.settings.kafka.sasl_password

        # 创建同步管理客户端
        self.admin_client = AdminClient(config)

        logger.info(
            "Kafka admin client initialized",
            client_id=self.client_id,
            bootstrap_servers=self.bootstrap_servers,
        )

    async def create_topics(
        self,
        topics: List[NewTopic],
        operation_timeout: float = 30,
        request_timeout: float = 30,
    ) -> Dict[str, Any]:
        """
        异步创建主题。

        Args:
            topics: 要创建的主题列表
            operation_timeout: 操作超时时间（秒）
            request_timeout: 请求超时时间（秒）

        Returns:
            创建结果
        """
        return await run_in_executor(
            self.admin_client.create_topics,
            topics,
            operation_timeout=operation_timeout,
            request_timeout=request_timeout,
        )

    async def delete_topics(
        self,
        topics: List[str],
        operation_timeout: float = 30,
        request_timeout: float = 30,
    ) -> Dict[str, Any]:
        """
        异步删除主题。

        Args:
            topics: 要删除的主题列表
            operation_timeout: 操作超时时间（秒）
            request_timeout: 请求超时时间（秒）

        Returns:
            删除结果
        """
        return await run_in_executor(
            self.admin_client.delete_topics,
            topics,
            operation_timeout=operation_timeout,
            request_timeout=request_timeout,
        )

    async def list_topics(self, timeout: float = 10) -> Dict[str, Any]:
        """
        异步列出主题。

        Args:
            timeout: 超时时间（秒）

        Returns:
            主题列表
        """
        return await run_in_executor(
            functools.partial(self.admin_client.list_topics, timeout=timeout)
        )

    async def list_consumer_groups(self, request_timeout: float = 10) -> Dict[str, Any]:
        """
        异步列出消费者组。

        Args:
            request_timeout: 请求超时时间（秒）

        Returns:
            消费者组列表
        """
        return await run_in_executor(
            self.admin_client.list_consumer_groups, request_timeout=request_timeout
        )

    async def describe_consumer_groups(
        self, groups: List[str], request_timeout: float = 10
    ) -> Dict[str, Any]:
        """
        异步描述消费者组。

        Args:
            groups: 要描述的消费者组列表
            request_timeout: 请求超时时间（秒）

        Returns:
            消费者组描述
        """
        return await run_in_executor(
            self.admin_client.describe_consumer_groups,
            groups,
            request_timeout=request_timeout,
        )

    async def describe_configs(
        self, resources: List[Any], request_timeout: float = 10
    ) -> Dict[str, Any]:
        """
        异步获取资源配置。

        Args:
            resources: 要获取配置的资源列表
            request_timeout: 请求超时时间（秒）

        Returns:
            资源配置
        """
        return await run_in_executor(
            self.admin_client.describe_configs,
            resources,
            request_timeout=request_timeout,
        )

    async def get_committed_offset(
        self, group_id: str, topic: str, partition: int
    ) -> Optional[int]:
        """
        异步获取已提交的偏移量。

        Args:
            group_id: 消费者组 ID
            topic: 主题名称
            partition: 分区 ID

        Returns:
            已提交的偏移量，如果不存在则为 None
        """
        try:
            # 创建临时消费者
            consumer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": f"{self.client_id}-offset-checker",
                "group.id": group_id,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }

            # 添加安全配置（如果需要）
            if self.settings.kafka.security_protocol != "PLAINTEXT":
                consumer_config["security.protocol"] = (
                    self.settings.kafka.security_protocol
                )

                if self.settings.kafka.sasl_mechanism:
                    consumer_config["sasl.mechanism"] = (
                        self.settings.kafka.sasl_mechanism
                    )

                if (
                    self.settings.kafka.sasl_username
                    and self.settings.kafka.sasl_password
                ):
                    consumer_config["sasl.username"] = self.settings.kafka.sasl_username
                    consumer_config["sasl.password"] = self.settings.kafka.sasl_password

            consumer = Consumer(consumer_config)

            # 创建主题分区
            topic_partition = TopicPartition(topic, partition)

            # 获取已提交的偏移量
            committed = await run_in_executor(
                consumer.committed, [topic_partition], timeout=10
            )

            # 关闭消费者
            await run_in_executor(consumer.close)

            # 返回偏移量
            if committed and committed[0].offset > -1:
                return committed[0].offset
            else:
                return None
        except Exception as e:
            logger.error(
                "Failed to get committed offset",
                group_id=group_id,
                topic=topic,
                partition=partition,
                error=str(e),
            )
            return None

    async def get_watermark_offsets(
        self, topic: str, partition: int
    ) -> Optional[tuple[int, int]]:
        """
        异步获取水位线偏移量。

        Args:
            topic: 主题名称
            partition: 分区 ID

        Returns:
            (低水位线, 高水位线) 元组，如果不存在则为 None
        """
        try:
            # 创建临时消费者
            consumer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": f"{self.client_id}-watermark-checker",
                "group.id": f"watermark-checker-{uuid.uuid4()}",
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }

            # 添加安全配置（如果需要）
            if self.settings.kafka.security_protocol != "PLAINTEXT":
                consumer_config["security.protocol"] = (
                    self.settings.kafka.security_protocol
                )

                if self.settings.kafka.sasl_mechanism:
                    consumer_config["sasl.mechanism"] = (
                        self.settings.kafka.sasl_mechanism
                    )

                if (
                    self.settings.kafka.sasl_username
                    and self.settings.kafka.sasl_password
                ):
                    consumer_config["sasl.username"] = self.settings.kafka.sasl_username
                    consumer_config["sasl.password"] = self.settings.kafka.sasl_password

            consumer = Consumer(consumer_config)

            # 获取水位线
            watermarks = await run_in_executor(
                consumer.get_watermark_offsets, TopicPartition(topic, partition)
            )

            # 关闭消费者
            await run_in_executor(consumer.close)

            return watermarks
        except Exception as e:
            logger.error(
                "Failed to get watermark offsets",
                topic=topic,
                partition=partition,
                error=str(e),
            )
            return None

    async def alter_consumer_group_offsets(
        self, group_id: str, topic: str, partition: int, offset: int
    ) -> bool:
        """
        异步修改消费者组偏移量。

        Args:
            group_id: 消费者组 ID
            topic: 主题名称
            partition: 分区 ID
            offset: 新的偏移量

        Returns:
            是否成功修改偏移量
        """
        try:
            # 创建临时消费者
            consumer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": f"{self.client_id}-offset-setter",
                "group.id": group_id,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }

            # 添加安全配置（如果需要）
            if self.settings.kafka.security_protocol != "PLAINTEXT":
                consumer_config["security.protocol"] = (
                    self.settings.kafka.security_protocol
                )

                if self.settings.kafka.sasl_mechanism:
                    consumer_config["sasl.mechanism"] = (
                        self.settings.kafka.sasl_mechanism
                    )

                if (
                    self.settings.kafka.sasl_username
                    and self.settings.kafka.sasl_password
                ):
                    consumer_config["sasl.username"] = self.settings.kafka.sasl_username
                    consumer_config["sasl.password"] = self.settings.kafka.sasl_password

            consumer = Consumer(consumer_config)

            # 创建主题分区
            topic_partition = TopicPartition(topic, partition, offset)

            # 修改偏移量
            await run_in_executor(
                consumer.commit, offsets=[topic_partition], asynchronous=False
            )

            # 关闭消费者
            await run_in_executor(consumer.close)

            return True
        except Exception as e:
            logger.error(
                "Failed to alter consumer group offsets",
                group_id=group_id,
                topic=topic,
                partition=partition,
                offset=offset,
                error=str(e),
            )
            return False

    async def get_offset_for_time(
        self, topic: str, partition: int, timestamp: int
    ) -> Optional[int]:
        """
        异步获取指定时间戳的偏移量。

        Args:
            topic: 主题名称
            partition: 分区 ID
            timestamp: 时间戳（毫秒）

        Returns:
            偏移量，如果不存在则为 None
        """
        try:
            # 创建临时消费者
            consumer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": f"{self.client_id}-offset-time-checker",
                "group.id": f"offset-time-checker-{uuid.uuid4()}",
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }

            # 添加安全配置（如果需要）
            if self.settings.kafka.security_protocol != "PLAINTEXT":
                consumer_config["security.protocol"] = (
                    self.settings.kafka.security_protocol
                )

                if self.settings.kafka.sasl_mechanism:
                    consumer_config["sasl.mechanism"] = (
                        self.settings.kafka.sasl_mechanism
                    )

                if (
                    self.settings.kafka.sasl_username
                    and self.settings.kafka.sasl_password
                ):
                    consumer_config["sasl.username"] = self.settings.kafka.sasl_username
                    consumer_config["sasl.password"] = self.settings.kafka.sasl_password

            consumer = Consumer(consumer_config)

            # 创建主题分区
            topic_partition = TopicPartition(topic, partition, timestamp)

            # 获取指定时间戳的偏移量
            offsets_for_times = await run_in_executor(
                consumer.offsets_for_times, [topic_partition]
            )

            # 关闭消费者
            await run_in_executor(consumer.close)

            # 返回偏移量
            if offsets_for_times and offsets_for_times[0].offset > -1:
                return offsets_for_times[0].offset
            else:
                return None
        except Exception as e:
            logger.error(
                "Failed to get offset for time",
                topic=topic,
                partition=partition,
                timestamp=timestamp,
                error=str(e),
            )
            return None

    async def alter_partition_reassignments(
        self, reassignments: List[Dict[str, Any]], request_timeout: float = 30
    ) -> Dict[str, Any]:
        """
        异步执行分区重分配。

        Args:
            reassignments: 重分配计划列表，每个计划包含 topic, partition, replicas
            request_timeout: 请求超时时间（秒）

        Returns:
            重分配结果
        """
        # 按主题和分区组织重分配计划
        reassignment_dict = {}
        for reassignment in reassignments:
            topic = reassignment["topic"]
            partition = reassignment["partition"]
            replicas = reassignment["replicas"]

            if topic not in reassignment_dict:
                reassignment_dict[topic] = {}

            # 直接使用副本列表
            reassignment_dict[topic][partition] = replicas

        # 执行分区重分配
        return await run_in_executor(
            self.admin_client.alter_partition_reassignments,
            reassignment_dict,
            request_timeout=request_timeout,
        )

    async def alter_configs(
        self, resources: List[Any], request_timeout: float = 30
    ) -> Dict[str, Any]:
        """
        异步修改资源配置。

        Args:
            resources: 要修改配置的资源列表
            request_timeout: 请求超时时间（秒）

        Returns:
            修改结果
        """
        return await run_in_executor(
            self.admin_client.alter_configs, resources, request_timeout=request_timeout
        )

    async def create_partitions(
        self,
        new_partitions: List[NewPartitions],
        operation_timeout: float = 30,
        request_timeout: float = 30,
    ) -> Dict[str, Any]:
        """
        异步增加主题的分区数量。

        Args:
            new_partitions: 要创建的分区列表，使用 NewPartitions 类
            operation_timeout: 操作超时时间（秒）
            request_timeout: 请求超时时间（秒）

        Returns:
            创建结果
        """
        return await run_in_executor(
            self.admin_client.create_partitions,
            new_partitions,
            operation_timeout=operation_timeout,
            request_timeout=request_timeout,
        )


class AsyncSchemaRegistryClient:
    """
    confluent-kafka SchemaRegistryClient 的异步封装。
    """

    def __init__(self, url: Optional[str] = None, **kwargs: Any) -> None:
        """
        初始化异步模式注册表客户端。

        Args:
            url: 模式注册表 URL
            **kwargs: 其他配置参数
        """
        self.settings = get_settings()
        self.url = url or self.settings.schema_registry.url

        # 创建配置
        config = {"url": self.url, **kwargs}

        # 添加认证（如果需要）
        if (
            self.settings.schema_registry.auth_user
            and self.settings.schema_registry.auth_password
        ):
            config["basic.auth.user.info"] = (
                f"{self.settings.schema_registry.auth_user}:{self.settings.schema_registry.auth_password}"
            )

        # 创建同步模式注册表客户端
        self.schema_registry_client = SchemaRegistryClient(config)

        logger.info(
            "Schema registry client initialized",
            url=self.url,
        )

    async def register_schema(
        self, subject: str, schema: str, schema_type: str = "AVRO"
    ) -> int:
        """
        异步注册模式。

        Args:
            subject: 主题
            schema: 模式定义
            schema_type: 模式类型

        Returns:
            模式 ID
        """
        return await run_in_executor(
            self.schema_registry_client.register_schema,
            subject=subject,
            schema=schema,
            schema_type=schema_type,
        )

    async def get_schema(self, schema_id: int) -> Dict[str, Any]:
        """
        异步获取模式。

        Args:
            schema_id: 模式 ID

        Returns:
            模式信息
        """
        return await run_in_executor(self.schema_registry_client.get_schema, schema_id)

    async def get_subjects(self) -> List[str]:
        """
        异步获取所有主题。

        Returns:
            主题列表
        """
        return await run_in_executor(self.schema_registry_client.get_subjects)

    async def get_latest_version(self, subject: str) -> Dict[str, Any]:
        """
        异步获取最新版本的模式。

        Args:
            subject: 主题

        Returns:
            模式信息
        """
        return await run_in_executor(
            self.schema_registry_client.get_latest_version, subject
        )

    async def check_compatibility(
        self, subject: str, schema: str, version: str = "latest"
    ) -> bool:
        """
        异步检查模式兼容性。

        Args:
            subject: 主题
            schema: 模式定义
            version: 版本

        Returns:
            是否兼容
        """
        return await run_in_executor(
            self.schema_registry_client.test_compatibility,
            subject=subject,
            schema=schema,
            version=version,
        )
