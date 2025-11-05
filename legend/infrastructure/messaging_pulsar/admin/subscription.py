import time
from typing import List

from .client import PulsarAdminClient


class Subscriptions:
    def __init__(self, client: PulsarAdminClient):
        self.client = client

    async def list_subscriptions(self, tenant: str, namespace: str, topic: str) -> List[str]:
        """
        列出 Topic 下的所有订阅者
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/subscriptions'
        return await self.client.get(path)

    async def delete_subscription(self, tenant: str, namespace: str, topic: str, sub_name: str, force: bool = True):
        """
        删除订阅者（默认强制删除）
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/subscription/{sub_name}'
        if force:
            path += '?force=true'
        await self.client.delete(path)

    async def reset_cursor_to_time(self, tenant: str, namespace: str, topic: str, sub_name: str, timestamp_ms: int):
        """
        将订阅的消费位点重置到指定时间（毫秒）
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/subscription/{sub_name}/resetcursor/{timestamp_ms}'
        await self.client.post(path)

    async def reset_cursor_to_latest(self, tenant: str, namespace: str, topic: str, sub_name: str):
        """
        将订阅重置到最新位点（跳过 backlog）
        """
        now_ms = int(time.time() * 1000)
        await self.reset_cursor_to_time(tenant, namespace, topic, sub_name, now_ms)

    async def get_subscription_stats(self, tenant: str, namespace: str, topic: str, sub_name: str) -> dict:
        """
        查看某订阅者的消费状态
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/subscription/{sub_name}'
        return await self.client.get(path)


# 实用方式示例
# client = PulsarAdminClient(admin_url="http://localhost:8080")
# subs = Subscriptions(client)

# await subs.list_subscriptions("public", "default", "user.registered")
# await subs.delete_subscription("public", "default", "user.registered", "default-sub")
# await subs.reset_cursor_to_latest("public", "default", "user.registered", "default-sub")
