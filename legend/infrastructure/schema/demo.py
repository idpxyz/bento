import json
from datetime import datetime

import aiohttp
import pulsar
from pulsar.schema import AvroSchema, Record

from idp.framework.infrastructure.schema.generated.models.chat import Chat


class ChatRecord(Record):
    """Pulsar schema for Chat messages"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    class Record:
        id = str
        data = str
        created_at = int  # 使用整数存储毫秒时间戳


async def ensure_namespace_exists(tenant: str, namespace: str):
    """确保命名空间存在"""
    admin_url = "http://192.168.8.137:8080"
    url = f"{admin_url}/admin/v2/namespaces/{tenant}/{namespace}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # 检查命名空间是否存在
        async with session.get(url, headers=headers) as response:
            if response.status == 404:
                # 创建命名空间
                tenant_url = f"{admin_url}/admin/v2/tenants/{tenant}"
                async with session.get(tenant_url, headers=headers) as tenant_response:
                    if tenant_response.status == 404:
                        # 创建租户
                        tenant_config = {
                            "adminRoles": [],
                            "allowedClusters": ["standalone"]
                        }
                        async with session.put(tenant_url, headers=headers, json=tenant_config) as put_response:
                            if put_response.status not in (200, 204):
                                print(f"创建租户失败: {tenant}, 状态码: {put_response.status}")
                                return False
                
                # 创建命名空间
                namespace_config = {
                    "replication_clusters": ["standalone"],
                    "retention_policies": {
                        "retentionTimeInMinutes": 0,
                        "retentionSizeInMB": 0
                    }
                }
                async with session.put(url, headers=headers, json=namespace_config) as put_response:
                    if put_response.status in (200, 204):
                        print(f"成功创建命名空间: {tenant}/{namespace}")
                        return True
                    else:
                        print(f"创建命名空间失败: {tenant}/{namespace}, 状态码: {put_response.status}")
                        return False
            elif response.status == 200:
                print(f"命名空间已存在: {tenant}/{namespace}")
                return True
            else:
                print(f"检查命名空间失败: {tenant}/{namespace}, 状态码: {response.status}")
                return False


async def ensure_topic_exists(tenant: str, namespace: str, topic: str):
    """确保主题存在"""
    admin_url = "http://192.168.8.137:8080"
    
    # 首先检查是否为分区主题
    partitioned_url = f"{admin_url}/admin/v2/persistent/{tenant}/{namespace}/{topic}/partitions"
    non_partitioned_url = f"{admin_url}/admin/v2/persistent/{tenant}/{namespace}/{topic}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # 先尝试创建非分区主题
        async with session.put(non_partitioned_url, headers=headers) as response:
            if response.status in (200, 204, 409):  # 409 表示主题已存在
                print(f"成功创建主题: {topic}")
                return True
            else:
                print(f"创建主题失败: {topic}, 状态码: {response.status}")
                try:
                    error_text = await response.text()
                    print(f"错误详情: {error_text}")
                except:
                    pass
                return False


async def delete_schema(tenant: str, namespace: str, topic: str):
    """删除指定主题的 schema"""
    admin_url = "http://192.168.8.137:8080"
    url = f"{admin_url}/admin/v2/schemas/{tenant}/{namespace}/{topic}/schema"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as response:
            if response.status in (200, 204):
                print(f"成功删除 schema: {topic}")
                return True
            else:
                print(f"删除 schema 失败: {topic}, 状态码: {response.status}")
                return False


async def main():
    # 解析主题名称
    topic = "persistent://idp/framework/chat"
    topic_parts = topic.replace("persistent://", "").split("/")
    tenant, namespace, topic_name = topic_parts

    # 确保命名空间存在
    if not await ensure_namespace_exists(tenant, namespace):
        print("创建命名空间失败，退出程序")
        return

    # 确保主题存在
    if not await ensure_topic_exists(tenant, namespace, topic_name):
        print("创建主题失败，退出程序")
        return

    # 首先删除现有的 schema
    await delete_schema(tenant, namespace, topic_name)

    # 创建 Pulsar 客户端
    client = pulsar.Client('pulsar://192.168.8.137:6650')

    try:
        # 使用 AvroSchema 创建生产者
        producer = client.create_producer(
            topic=topic,
            schema=AvroSchema(ChatRecord)
        )

        # 从 Pydantic 模型创建 Record 实例
        chat_pydantic = Chat(
            id="123",
            data="Hello Pulsar!",
            created_at=datetime.now()
        )

        # 转换为 Pulsar Record
        chat_record = ChatRecord(
            id=chat_pydantic.id,
            data=chat_pydantic.data,
            created_at=int(chat_pydantic.created_at.timestamp() * 1000)  # 转换为毫秒时间戳并确保是整数
        )

        # 发送消息
        producer.send(chat_record)
        print("消息发送成功")

    finally:
        # 关闭生产者和客户端
        if 'producer' in locals():
            producer.close()
        client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
