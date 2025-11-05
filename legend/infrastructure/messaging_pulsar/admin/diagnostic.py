from .client import PulsarAdminClient


class Diagnostics:
    def __init__(self, client: PulsarAdminClient):
        self.client = client

    async def get_topic_stats(self, tenant: str, namespace: str, topic: str) -> dict:
        """
        获取主题的运行状态（backlog、tps、订阅状态等）
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/stats'
        return await self.client.get(path)

    async def get_partitioned_topic_metadata(self, tenant: str, namespace: str, topic: str) -> dict:
        """
        获取主题分区元数据（是否分区、分区数）
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/partitions'
        return await self.client.get(path)

    async def get_backlog_size(self, tenant: str, namespace: str, topic: str) -> int:
        """
        获取 backlog 数量（未消费消息总数）
        """
        stats = await self.get_topic_stats(tenant, namespace, topic)
        backlog = 0
        for sub in stats.get("subscriptions", {}).values():
            backlog += sub.get("msgBacklog", 0)
        return backlog

# 实用方式示例
# client = PulsarAdminClient(admin_url="http://localhost:8080")
# diag = Diagnostics(client)

# # 获取 topic 状态
# stats = await diag.get_topic_stats("public", "default", "user.registered")

# # 判断是否为分区 topic
# meta = await diag.get_partitioned_topic_metadata("public", "default", "user.registered")

# # 获取 backlog 消息数
# backlog = await diag.get_backlog_size("public", "default", "user.registered")
