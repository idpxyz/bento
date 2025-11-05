import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from confluent_kafka.admin import (
    RESOURCE_TOPIC,
    ConfigResource,
    ConfigSource,
    NewPartitions,
    NewTopic,
)

from idp.framework.infrastructure.messaging.common.logging import get_logger
from idp.framework.infrastructure.messaging.common.schemas import (
    ConsumerGroupInfo,
    TopicConfig,
)
from idp.framework.infrastructure.messaging.config.settings import get_settings
from idp.framework.infrastructure.messaging.exception import TopicCreationError
from idp.framework.infrastructure.messaging.kafka import AsyncAdminClient

# 初始化日志记录器
logger = get_logger(__name__)


class KafkaAdmin:
    """
    Kafka 管理 API。
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
    ) -> None:
        """
        初始化 Kafka 管理 API。

        Args:
            client_id: 客户端 ID
            bootstrap_servers: Kafka 服务器地址
        """
        self.settings = get_settings()
        self.client_id = client_id or f"admin-{uuid.uuid4()}"
        self.bootstrap_servers = bootstrap_servers or ",".join(
            self.settings.kafka.bootstrap_servers
        )
        self.admin_client = AsyncAdminClient(
            client_id=self.client_id,
            bootstrap_servers=self.bootstrap_servers,
        )

        logger.info(
            "Kafka admin initialized",
            client_id=self.client_id,
            bootstrap_servers=self.bootstrap_servers,
        )

    async def list_topics(self) -> List[str]:
        """
        列出所有主题，排除系统主题。

        Returns:
            主题名称列表，不包含系统主题
        """
        try:
            logger.info(
                "Listing topics from Kafka",
                bootstrap_servers=self.bootstrap_servers,
            )

            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            logger.info(
                "Got cluster metadata",
                metadata_type=type(cluster_metadata).__name__,
            )

            if hasattr(cluster_metadata, "topics"):
                all_topics = list(cluster_metadata.topics.keys())

                # 过滤掉系统主题
                system_prefixes = [
                    "_confluent-",
                    "_schemas",
                    "__",
                    "docker-connect-",
                    "_confluent",
                    "default_ksql_",
                ]

                user_topics = [
                    topic
                    for topic in all_topics
                    if not any(topic.startswith(prefix) for prefix in system_prefixes)
                ]

                logger.info(
                    "Listed topics",
                    total_count=len(all_topics),
                    user_topic_count=len(user_topics),
                    user_topics=user_topics,
                )

                return user_topics
            else:
                logger.warning(
                    "Cluster metadata does not have topics attribute",
                    metadata=str(cluster_metadata),
                )
                return []
        except Exception as e:
            logger.error(
                "Failed to list topics",
                error=str(e),
                exc_info=True,
            )
            raise

    async def create_topic(self, topic_config: TopicConfig) -> TopicConfig:
        """
        创建主题。

        Args:
            topic_config: 主题配置

        Returns:
            创建的主题配置
        """
        try:
            # 创建 NewTopic 对象
            new_topic = NewTopic(
                topic_config.name,
                num_partitions=topic_config.partitions,
                replication_factor=topic_config.replication_factor,
                config=topic_config.configs,
            )

            # 创建主题
            result = await self.admin_client.create_topics(
                [new_topic], operation_timeout=30.0
            )

            # 检查结果
            for topic, future in result.items():
                try:
                    future.result()  # 等待完成
                    logger.info(
                        "Created topic",
                        topic=topic,
                        partitions=topic_config.partitions,
                        replication_factor=topic_config.replication_factor,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to create topic",
                        topic=topic,
                        error=str(e),
                    )
                    raise TopicCreationError(str(e), topic)

            return topic_config
        except Exception as e:
            logger.error(
                "Failed to create topic",
                topic=topic_config.name,
                error=str(e),
            )
            raise

    async def delete_topic(self, topic: str) -> bool:
        """
        删除主题。

        Args:
            topic: 主题名称

        Returns:
            是否成功删除
        """
        try:
            # 删除主题
            result = await self.admin_client.delete_topics(
                [topic], operation_timeout=30.0
            )

            # 检查结果
            for topic_name, future in result.items():
                try:
                    future.result()  # 等待完成
                    logger.info(
                        "Deleted topic",
                        topic=topic_name,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to delete topic",
                        topic=topic_name,
                        error=str(e),
                    )
                    return False

            return True
        except Exception as e:
            logger.error(
                "Failed to delete topic",
                topic=topic,
                error=str(e),
            )
            raise

    async def list_consumer_groups(self) -> List[str]:
        """
        列出所有消费者组。

        Returns:
            消费者组 ID 列表
        """
        try:
            logger.info("Listing consumer groups")

            # 获取消费者组列表
            result = await self.admin_client.list_consumer_groups()

            # 正确处理返回结果
            groups = []

            # 检查结果结构
            if hasattr(result, "valid"):
                # 如果结果有 valid 属性，使用它
                groups = [group.group_id for group in result.valid]
            elif isinstance(result, dict) and "valid" in result:
                # 如果结果是字典且有 valid 键，使用它
                groups = [group.group_id for group in result["valid"]]
            else:
                # 尝试直接迭代结果
                try:
                    for group in result:
                        if hasattr(group, "group_id"):
                            groups.append(group.group_id)
                        elif isinstance(group, dict) and "group_id" in group:
                            groups.append(group["group_id"])
                except (TypeError, AttributeError):
                    logger.warning(
                        "Unexpected result structure from list_consumer_groups",
                        result_type=type(result).__name__,
                        result=str(result),
                    )

            logger.info(
                "Listed consumer groups",
                count=len(groups),
                groups=groups,
            )

            return groups
        except Exception as e:
            logger.error(
                "Failed to list consumer groups",
                error=str(e),
                exc_info=True,
            )
            raise

    async def describe_consumer_group(self, group_id: str) -> ConsumerGroupInfo:
        """
        描述消费者组。

        Args:
            group_id: 消费者组 ID

        Returns:
            消费者组信息
        """
        try:
            logger.info(
                "Describing consumer group",
                group_id=group_id,
            )

            # 获取消费者组描述
            result = await self.admin_client.describe_consumer_groups([group_id])

            # 检查结果结构
            if not result:
                logger.warning(
                    "Empty result from describe_consumer_groups",
                    group_id=group_id,
                )
                return ConsumerGroupInfo(
                    group_id=group_id,
                    topics=[],
                    members=0,
                    status="UNKNOWN",
                )

            # 尝试获取组描述
            group_description = None

            # 如果结果是字典，尝试获取组描述
            if isinstance(result, dict):
                if group_id in result:
                    future = result[group_id]
                    try:
                        group_description = future.result()
                    except Exception as e:
                        logger.error(
                            "Failed to get result from future",
                            group_id=group_id,
                            error=str(e),
                        )
                        raise

            # 如果没有获取到组描述，返回默认值
            if not group_description:
                logger.warning(
                    "No group description found",
                    group_id=group_id,
                    result_type=type(result).__name__,
                )
                return ConsumerGroupInfo(
                    group_id=group_id,
                    topics=[],
                    members=0,
                    status="UNKNOWN",
                )

            # 提取主题
            topics = set()
            members_count = 0

            if hasattr(group_description, "members"):
                members_count = len(group_description.members)
                for member in group_description.members:
                    if hasattr(member, "assignment") and hasattr(
                        member.assignment, "topic_partitions"
                    ):
                        for topic_partition in member.assignment.topic_partitions:
                            if hasattr(topic_partition, "topic"):
                                topics.add(topic_partition.topic)

            # 获取状态
            status = "UNKNOWN"
            if hasattr(group_description, "state"):
                status = group_description.state

            # 创建消费者组信息
            group_info = ConsumerGroupInfo(
                group_id=group_id,
                topics=list(topics),
                members=members_count,
                status=status,
            )

            logger.info(
                "Described consumer group",
                group_id=group_id,
                topics=list(topics),
                members=members_count,
                status=status,
            )

            return group_info
        except Exception as e:
            logger.error(
                "Failed to describe consumer group",
                group_id=group_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_topic_detail(self, topic: str) -> Dict[str, Any]:
        """
        获取主题的详细信息。

        Args:
            topic: 主题名称

        Returns:
            Dict[str, Any]: 主题详细信息
        """
        try:
            logger.info(
                "Getting topic detail",
                topic=topic,
            )

            # 获取主题元数据 - 修复参数传递
            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            if topic not in cluster_metadata.topics:
                logger.error(
                    "Topic not found",
                    topic=topic,
                )
                raise ValueError(f"Topic {topic} not found")

            topic_metadata = cluster_metadata.topics[topic]

            # 获取主题配置
            configs = await self.get_topic_configs(topic)

            # 计算副本因子
            replication_factor = 0
            if topic_metadata.partitions:
                # 假设所有分区的副本因子相同
                first_partition = next(iter(topic_metadata.partitions.values()))
                replication_factor = len(first_partition.replicas)

            # 创建主题详细信息
            topic_detail = {
                "name": topic,
                "partitions": len(topic_metadata.partitions),
                "replication_factor": replication_factor,
                "configs": configs,
                "is_internal": topic_metadata.is_internal,
                "created_at": None,  # Kafka 不提供创建时间
            }

            logger.info(
                "Got topic detail",
                topic=topic,
                partitions=topic_detail["partitions"],
                replication_factor=topic_detail["replication_factor"],
            )

            return topic_detail
        except Exception as e:
            logger.error(
                "Failed to get topic detail",
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_topic_partitions(self, topic: str) -> Dict[str, Any]:
        """
        获取主题的分区信息。

        Args:
            topic: 主题名称

        Returns:
            Dict[str, Any]: 主题分区信息
        """
        try:
            logger.info(
                "Getting topic partitions",
                topic=topic,
            )

            # 获取主题元数据 - 修复参数传递
            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            if topic not in cluster_metadata.topics:
                logger.error(
                    "Topic not found",
                    topic=topic,
                )
                raise ValueError(f"Topic {topic} not found")

            topic_metadata = cluster_metadata.topics[topic]

            # 创建分区信息列表
            partitions = []
            for partition_id, partition_metadata in topic_metadata.partitions.items():
                partition_info = {
                    "partition": partition_id,
                    "leader": partition_metadata.leader,
                    "replicas": partition_metadata.replicas,
                    "isr": partition_metadata.isrs,
                }
                partitions.append(partition_info)

            # 创建主题分区信息
            topic_partitions = {
                "topic": topic,
                "partitions": partitions,
            }

            logger.info(
                "Got topic partitions",
                topic=topic,
                partition_count=len(partitions),
            )

            return topic_partitions
        except Exception as e:
            logger.error(
                "Failed to get topic partitions",
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_topic_configs(self, topic: str) -> Dict[str, str]:
        """
        获取主题的配置信息。

        Args:
            topic: 主题名称

        Returns:
            Dict[str, str]: 主题配置信息
        """
        try:
            logger.info(
                "Getting topic configs",
                topic=topic,
            )

            # 创建配置资源
            config_resource = ConfigResource(RESOURCE_TOPIC, topic)

            # 获取配置
            result = await self.admin_client.describe_configs([config_resource])

            configs = {}
            for resource, future in result.items():
                try:
                    config_entries = future.result()
                    for config_entry in config_entries:
                        # 只包含非默认配置
                        if config_entry.source != ConfigSource.DEFAULT_CONFIG:
                            configs[config_entry.name] = config_entry.value
                except Exception as e:
                    logger.error(
                        "Failed to get config for resource",
                        resource=resource.name,
                        error=str(e),
                    )

            logger.info(
                "Got topic configs",
                topic=topic,
                config_count=len(configs),
            )

            return configs
        except Exception as e:
            logger.error(
                "Failed to get topic configs",
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_consumer_group_offsets(
        self, group_id: str, topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取消费者组的偏移量信息。

        Args:
            group_id: 消费者组 ID
            topic: 可选，过滤特定主题的偏移量

        Returns:
            List[Dict[str, Any]]: 消费者组偏移量信息
        """
        try:
            logger.info(
                "Getting consumer group offsets",
                group_id=group_id,
                topic=topic,
            )

            # 获取消费者组描述
            group_description = await self.describe_consumer_group(group_id)

            # 如果指定了主题，过滤主题
            topics_to_check = group_description.topics
            if topic:
                if topic in topics_to_check:
                    topics_to_check = [topic]
                else:
                    logger.warning(
                        "Topic not found in consumer group",
                        group_id=group_id,
                        topic=topic,
                    )
                    return []

            # 获取主题分区信息
            offsets = []
            for topic_name in topics_to_check:
                # 获取主题分区
                topic_partitions = await self.get_topic_partitions(topic_name)

                # 获取消费者组偏移量
                for partition_info in topic_partitions["partitions"]:
                    partition_id = partition_info["partition"]

                    # 获取消费者组偏移量
                    committed_offset = await self.admin_client.get_committed_offset(
                        group_id, topic_name, partition_id
                    )

                    # 获取水位线
                    watermarks = await self.admin_client.get_watermark_offsets(
                        topic_name, partition_id
                    )

                    # 计算滞后量
                    lag = 0
                    if committed_offset is not None and watermarks is not None:
                        lag = max(0, watermarks[1] - committed_offset)

                    # 创建偏移量信息
                    offset_info = {
                        "topic": topic_name,
                        "partition": partition_id,
                        "offset": (
                            committed_offset if committed_offset is not None else -1
                        ),
                        "high_watermark": (
                            watermarks[1] if watermarks is not None else -1
                        ),
                        "low_watermark": (
                            watermarks[0] if watermarks is not None else -1
                        ),
                        "lag": lag,
                    }

                    offsets.append(offset_info)

            logger.info(
                "Got consumer group offsets",
                group_id=group_id,
                offset_count=len(offsets),
            )

            return offsets
        except Exception as e:
            logger.error(
                "Failed to get consumer group offsets",
                group_id=group_id,
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise

    async def reset_consumer_group_offsets(
        self,
        group_id: str,
        topic: str,
        partition: Optional[int] = None,
        offset: Optional[int] = None,
        timestamp: Optional[int] = None,
        reset_to: Optional[str] = None,
    ) -> bool:
        """
        重置消费者组的偏移量。

        Args:
            group_id: 消费者组 ID
            topic: 主题名称
            partition: 可选，分区 ID
            offset: 可选，指定偏移量
            timestamp: 可选，指定时间戳
            reset_to: 可选，重置到的位置（earliest, latest, specific）

        Returns:
            bool: 是否成功重置偏移量
        """
        try:
            logger.info(
                "Resetting consumer group offsets",
                group_id=group_id,
                topic=topic,
                partition=partition,
                offset=offset,
                timestamp=timestamp,
                reset_to=reset_to,
            )

            # 获取主题分区
            topic_partitions = await self.get_topic_partitions(topic)

            # 确定要重置的分区
            partitions_to_reset = []
            if partition is not None:
                # 检查分区是否存在
                partition_exists = any(
                    p["partition"] == partition for p in topic_partitions["partitions"]
                )
                if not partition_exists:
                    logger.error(
                        "Partition not found",
                        topic=topic,
                        partition=partition,
                    )
                    raise ValueError(
                        f"Partition {partition} not found in topic {topic}"
                    )

                partitions_to_reset = [partition]
            else:
                # 重置所有分区
                partitions_to_reset = [
                    p["partition"] for p in topic_partitions["partitions"]
                ]

            # 确定要重置到的偏移量
            for partition_id in partitions_to_reset:
                if reset_to == "earliest":
                    # 重置到最早的偏移量
                    watermarks = await self.admin_client.get_watermark_offsets(
                        topic, partition_id
                    )
                    if watermarks is not None:
                        await self.admin_client.alter_consumer_group_offsets(
                            group_id, topic, partition_id, watermarks[0]
                        )
                elif reset_to == "latest":
                    # 重置到最新的偏移量
                    watermarks = await self.admin_client.get_watermark_offsets(
                        topic, partition_id
                    )
                    if watermarks is not None:
                        await self.admin_client.alter_consumer_group_offsets(
                            group_id, topic, partition_id, watermarks[1]
                        )
                elif reset_to == "specific" and offset is not None:
                    # 重置到指定的偏移量
                    await self.admin_client.alter_consumer_group_offsets(
                        group_id, topic, partition_id, offset
                    )
                elif timestamp is not None:
                    # 重置到指定时间戳的偏移量
                    offset_for_time = await self.admin_client.get_offset_for_time(
                        topic, partition_id, timestamp
                    )
                    if offset_for_time is not None:
                        await self.admin_client.alter_consumer_group_offsets(
                            group_id, topic, partition_id, offset_for_time
                        )
                else:
                    logger.error(
                        "Invalid reset parameters",
                        reset_to=reset_to,
                        offset=offset,
                        timestamp=timestamp,
                    )
                    raise ValueError("Invalid reset parameters")

            logger.info(
                "Reset consumer group offsets",
                group_id=group_id,
                topic=topic,
                partitions=partitions_to_reset,
            )

            return True
        except Exception as e:
            logger.error(
                "Failed to reset consumer group offsets",
                group_id=group_id,
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_cluster_info(self) -> Dict[str, Any]:
        """
        获取 Kafka 集群信息。

        Returns:
            Dict[str, Any]: 集群信息
        """
        try:
            logger.info("Getting cluster info")

            # 获取集群元数据
            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            # 获取集群 ID
            cluster_id = (
                cluster_metadata.cluster_id
                if hasattr(cluster_metadata, "cluster_id")
                else "unknown"
            )

            # 获取控制器 ID
            controller_id = (
                cluster_metadata.controller_id
                if hasattr(cluster_metadata, "controller_id")
                else -1
            )

            # 获取代理节点数量
            broker_count = (
                len(cluster_metadata.brokers)
                if hasattr(cluster_metadata, "brokers")
                else 0
            )

            # 获取主题数量
            topic_count = (
                len(cluster_metadata.topics)
                if hasattr(cluster_metadata, "topics")
                else 0
            )

            # 创建集群信息
            cluster_info = {
                "id": cluster_id,
                "controller_id": controller_id,
                "broker_count": broker_count,
                "topic_count": topic_count,
            }

            logger.info(
                "Got cluster info",
                cluster_id=cluster_id,
                controller_id=controller_id,
                broker_count=broker_count,
                topic_count=topic_count,
            )

            return cluster_info
        except Exception as e:
            logger.error(
                "Failed to get cluster info",
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_cluster_brokers(self) -> List[Dict[str, Any]]:
        """
        获取 Kafka 集群的代理节点信息。

        Returns:
            List[Dict[str, Any]]: 代理节点信息列表
        """
        try:
            logger.info("Getting cluster brokers")

            # 获取集群元数据
            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            # 获取代理节点信息
            brokers = []
            if hasattr(cluster_metadata, "brokers"):
                for broker_id, broker_metadata in cluster_metadata.brokers.items():
                    broker_info = {
                        "id": broker_id,
                        "host": broker_metadata.host,
                        "port": broker_metadata.port,
                        "rack": (
                            broker_metadata.rack
                            if hasattr(broker_metadata, "rack")
                            else None
                        ),
                    }
                    brokers.append(broker_info)

            logger.info(
                "Got cluster brokers",
                broker_count=len(brokers),
            )

            return brokers
        except Exception as e:
            logger.error(
                "Failed to get cluster brokers",
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_cluster_controller(self) -> Dict[str, Any]:
        """
        获取 Kafka 集群的控制器信息。

        Returns:
            Dict[str, Any]: 控制器信息
        """
        try:
            logger.info("Getting cluster controller")

            # 获取集群元数据
            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            # 获取控制器 ID
            controller_id = (
                cluster_metadata.controller_id
                if hasattr(cluster_metadata, "controller_id")
                else -1
            )

            # 获取控制器节点信息
            controller_info = None
            if (
                controller_id != -1
                and hasattr(cluster_metadata, "brokers")
                and controller_id in cluster_metadata.brokers
            ):
                controller_metadata = cluster_metadata.brokers[controller_id]
                controller_info = {
                    "id": controller_id,
                    "host": controller_metadata.host,
                    "port": controller_metadata.port,
                    "epoch": -1,  # Kafka 不提供 epoch 信息
                }
            else:
                # 如果找不到控制器信息，返回默认值
                controller_info = {
                    "id": controller_id,
                    "host": "unknown",
                    "port": -1,
                    "epoch": -1,
                }

            logger.info(
                "Got cluster controller",
                controller_id=controller_id,
            )

            return controller_info
        except Exception as e:
            logger.error(
                "Failed to get cluster controller",
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_cluster_assignments(
        self, topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取 Kafka 集群的分区分配信息。

        Args:
            topic: 可选，过滤特定主题的分区分配

        Returns:
            List[Dict[str, Any]]: 分区分配信息列表
        """
        try:
            logger.info(
                "Getting cluster assignments",
                topic=topic,
            )

            # 获取集群元数据 - 修复参数传递
            cluster_metadata = await self.admin_client.list_topics(timeout=10.0)

            # 获取分区分配信息
            assignments = []
            for topic_name, topic_metadata in cluster_metadata.topics.items():
                # 如果指定了主题，只返回该主题的分区分配
                if topic and topic_name != topic:
                    continue

                for (
                    partition_id,
                    partition_metadata,
                ) in topic_metadata.partitions.items():
                    assignment = {
                        "topic": topic_name,
                        "partition": partition_id,
                        "leader": partition_metadata.leader,
                        "replicas": partition_metadata.replicas,
                        "isr": partition_metadata.isrs,
                    }
                    assignments.append(assignment)

            logger.info(
                "Got cluster assignments",
                assignment_count=len(assignments),
            )

            return assignments
        except Exception as e:
            logger.error(
                "Failed to get cluster assignments",
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise

    async def alter_topic_replication_factor(
        self, topic: str, new_replication_factor: int
    ) -> bool:
        """
        修改主题的副本因子。

        Args:
            topic: 主题名称
            new_replication_factor: 新的副本因子

        Returns:
            bool: 是否成功修改副本因子
        """
        try:
            logger.info(
                "Altering topic replication factor",
                topic=topic,
                new_replication_factor=new_replication_factor,
            )

            # 获取主题分区信息
            topic_partitions = await self.get_topic_partitions(topic)

            # 获取集群 broker 信息
            brokers = await self.get_cluster_brokers()
            broker_ids = [broker["id"] for broker in brokers]

            if len(broker_ids) < new_replication_factor:
                logger.error(
                    "Not enough brokers for requested replication factor",
                    topic=topic,
                    broker_count=len(broker_ids),
                    requested_replication_factor=new_replication_factor,
                )
                raise ValueError(
                    f"Not enough brokers ({len(broker_ids)}) for requested replication factor ({new_replication_factor})"
                )

            # 创建分区重分配计划
            reassignment_plan = []
            for partition_info in topic_partitions["partitions"]:
                partition_id = partition_info["partition"]
                current_replicas = partition_info["replicas"]

                # 确保当前的 leader 仍然是第一个副本
                leader = partition_info["leader"]

                # 创建新的副本列表，确保 leader 是第一个
                new_replicas = [leader]

                # 添加其他 broker 作为副本，直到达到所需的副本因子
                for broker_id in broker_ids:
                    if (
                        broker_id != leader
                        and len(new_replicas) < new_replication_factor
                    ):
                        new_replicas.append(broker_id)

                # 创建分区重分配计划
                reassignment = {
                    "topic": topic,
                    "partition": partition_id,
                    "replicas": new_replicas,
                }
                reassignment_plan.append(reassignment)

            # 执行分区重分配
            result = await self.admin_client.alter_partition_reassignments(
                reassignment_plan
            )

            # 检查结果
            success = True
            for topic_name, partitions in result.items():
                for partition_id, future in partitions.items():
                    try:
                        future.result()  # 等待完成
                        logger.info(
                            "Altered partition replicas",
                            topic=topic_name,
                            partition=partition_id,
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to alter partition replicas",
                            topic=topic_name,
                            partition=partition_id,
                            error=str(e),
                        )
                        success = False

            logger.info(
                "Altered topic replication factor",
                topic=topic,
                new_replication_factor=new_replication_factor,
                success=success,
            )

            return success
        except Exception as e:
            logger.error(
                "Failed to alter topic replication factor",
                topic=topic,
                new_replication_factor=new_replication_factor,
                error=str(e),
                exc_info=True,
            )
            raise

    async def alter_topic_configs(self, topic: str, configs: Dict[str, str]) -> bool:
        """
        修改主题的配置。

        Args:
            topic: 主题名称
            configs: 配置字典，键为配置名称，值为配置值

        Returns:
            bool: 是否成功修改配置
        """
        try:
            logger.info(
                "Altering topic configs",
                topic=topic,
                configs=configs,
            )

            # 创建配置资源
            config_resource = ConfigResource(RESOURCE_TOPIC, topic)

            # 设置配置
            for key, value in configs.items():
                config_resource.set_config(key, value)

            # 执行配置修改
            result = await self.admin_client.alter_configs([config_resource])

            # 检查结果
            success = True
            for resource, future in result.items():
                try:
                    future.result()  # 等待完成
                    logger.info(
                        "Altered topic configs",
                        topic=resource.name,
                        configs=configs,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to alter topic configs",
                        topic=resource.name,
                        configs=configs,
                        error=str(e),
                    )
                    success = False

            return success
        except Exception as e:
            logger.error(
                "Failed to alter topic configs",
                topic=topic,
                configs=configs,
                error=str(e),
                exc_info=True,
            )
            raise

    async def increase_topic_partitions(
        self,
        topic: str,
        new_total_count: int,
        replica_assignment: Optional[List[List[int]]] = None,
    ) -> bool:
        """
        增加主题的分区数量。

        Args:
            topic: 主题名称
            new_total_count: 新的分区总数
            replica_assignment: 可选的副本分配列表，每个分区一个副本列表

        Returns:
            bool: 是否成功增加分区数量
        """
        try:
            logger.info(
                "Increasing topic partitions",
                topic=topic,
                new_total_count=new_total_count,
                replica_assignment=replica_assignment,
            )

            # 获取主题分区信息
            topic_partitions = await self.get_topic_partitions(topic)
            current_partition_count = len(topic_partitions["partitions"])

            if new_total_count <= current_partition_count:
                logger.warning(
                    "New partition count must be greater than current count",
                    topic=topic,
                    current_count=current_partition_count,
                    requested_count=new_total_count,
                )
                return False

            # 创建 NewPartitions 对象，不使用 replica_assignment 参数
            # 这样 Kafka 会自动分配副本
            new_partitions = NewPartitions(topic=topic, new_total_count=new_total_count)

            # 执行分区创建
            result = await self.admin_client.create_partitions([new_partitions])

            # 检查结果
            success = True
            for topic_name, future in result.items():
                try:
                    future.result()  # 等待完成
                    logger.info(
                        "Increased topic partitions",
                        topic=topic_name,
                        new_total_count=new_total_count,
                    )
                except Exception as e:
                    success = False
                    logger.error(
                        "Failed to increase topic partitions",
                        topic=topic_name,
                        error=str(e),
                        exc_info=True,
                    )

            return success
        except Exception as e:
            logger.error(
                "Failed to increase topic partitions",
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            return False
