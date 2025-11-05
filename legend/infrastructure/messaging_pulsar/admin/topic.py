import json
from typing import List, Optional

from .client import PulsarAdminClient


class Topics:
    def __init__(self, client: PulsarAdminClient):
        """
        初始化主题管理器。

        :param client: PulsarAdminClient 实例
        """
        self.client = client

    async def list_topics(self, tenant: str, namespace: str) -> List[str]:
        """
        获取指定命名空间下的所有主题。

        :param tenant: 租户名称
        :param namespace: 命名空间名称
        :return: 主题名称列表
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}'
        return await self.client.get(path)

    async def create_topic(self, tenant: str, namespace: str, topic: str, partitions: Optional[int] = None):
        """
        创建主题。

        :param tenant: 租户名称
        :param namespace: 命名空间名称
        :param topic: 主题名称
        :param partitions: 分区数，如果是分区主题
        """
        topic_path = f'persistent://{tenant}/{namespace}/{topic}'
        if partitions:
            path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/partitions'
            await self.client.put(path, json={'partitions': partitions})
        else:
            path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}'
            await self.client.put(path)

    async def delete_topic(self, tenant: str, namespace: str, topic: str, force: bool = False):
        """
        删除主题。

        :param tenant: 租户名称
        :param namespace: 命名空间名称
        :param topic: 主题名称
        :param force: 是否强制删除
        """
        topic_path = f'persistent://{tenant}/{namespace}/{topic}'
        path = f'/admin/v2/{topic_path}'
        if force:
            path += '?force=true'
        await self.client.delete(path)

    async def get_retention(self, tenant: str, namespace: str, topic: str) -> dict:
        """
        获取主题的消息保留策略。

        :param tenant: 租户名称
        :param namespace: 命名空间名称
        :param topic: 主题名称
        :return: 保留策略的字典表示
        """
        topic_path = f'persistent://{tenant}/{namespace}/{topic}'
        path = f'/admin/v2/{topic_path}/retention'
        return await self.client.get(path)

    async def set_retention(self, tenant: str, namespace: str, topic: str, size_in_mb: int, time_in_minutes: int):
        """
        设置主题的消息保留策略。

        :param tenant: 租户名称
        :param namespace: 命名空间名称
        :param topic: 主题名称
        :param size_in_mb: 保留的消息大小（MB）
        :param time_in_minutes: 保留的时间（分钟）
        """
        topic_path = f'persistent://{tenant}/{namespace}/{topic}'
        path = f'/admin/v2/{topic_path}/retention'
        retention_policies = {
            'retentionSizeInMB': size_in_mb,
            'retentionTimeInMinutes': time_in_minutes
        }
        await self.client.post(path, json=retention_policies)
