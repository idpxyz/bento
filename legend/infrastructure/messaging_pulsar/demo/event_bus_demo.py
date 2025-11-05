#!/usr/bin/env python3
"""
事件总线 + 多编解码器使用示例

展示如何:
1. 使用不同的编解码器配置事件总线
2. 发布事件并使用不同的编解码格式
3. 接收和处理事件

运行示例: python event_bus_demo.py+
"""

import asyncio
import json
import uuid
from datetime import datetime

from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import get_codec
from idp.framework.infrastructure.messaging.dispatcher.decorator import event_handler
from idp.framework.infrastructure.messaging.pulsar.event_bus import PulsarEventBus

# 定义示例事件数据
USER_REGISTERED_EVENT = {
    "user_id": str(uuid.uuid4()),
    "email": "new_user@example.com",
    "name": "New User",
    "registered_at": datetime.utcnow().isoformat()
}

ORDER_CREATED_EVENT = {
    "order_id": str(uuid.uuid4()),
    "user_id": "user-123",
    "items": [
        {"product_id": "prod-1", "quantity": 2, "price": 9.99},
        {"product_id": "prod-2", "quantity": 1, "price": 19.99}
    ],
    "total_amount": 39.97,
    "created_at": datetime.utcnow().isoformat()
}


# 注册事件处理器
@event_handler("user.registered")
async def handle_user_registered(event: MessageEnvelope):
    """处理用户注册事件"""
    print(f"\n✅ 接收到用户注册事件 ({event.correlation_id})")
    print(f"   事件数据: {json.dumps(event.payload, ensure_ascii=False, indent=2)}")
    print(f"   处理时间: {datetime.utcnow().isoformat()}")


@event_handler("order.created")
async def handle_order_created(event: MessageEnvelope):
    """处理订单创建事件"""
    print(f"\n✅ 接收到订单创建事件 ({event.correlation_id})")
    print(f"   事件数据: {json.dumps(event.payload, ensure_ascii=False, indent=2)}")
    print(f"   处理时间: {datetime.utcnow().isoformat()}")


async def publish_events_with_codec(codec_name: str):
    """使用指定编解码器发布事件"""
    # 获取编解码器
    codec = get_codec(codec_name)
    
    # 创建带特定编解码器的事件总线
    event_bus = PulsarEventBus(codec_name=codec_name)
    
    # 生成关联ID (用于跟踪请求)
    correlation_id = f"demo-{str(uuid.uuid4())[:8]}"
    
    print(f"\n🚀 使用 {codec_name} 编解码器发布事件...")
    
    # 发布用户注册事件
    await event_bus.publish_event(
        event_type="user.registered",
        payload=USER_REGISTERED_EVENT,
        source="demo-service",
        correlation_id=correlation_id
    )
    print(f"   已发布 user.registered 事件")
    
    # 发布订单创建事件
    await event_bus.publish_event(
        event_type="order.created",
        payload=ORDER_CREATED_EVENT,
        source="demo-service",
        correlation_id=correlation_id
    )
    print(f"   已发布 order.created 事件")


async def subscribe_to_events():
    """订阅并处理事件"""
    # 创建事件总线
    event_bus = PulsarEventBus()
    
    print("\n🔔 启动事件订阅...")
    # 启动订阅，监听事件
    await asyncio.gather(
        event_bus.run_subscription("persistent://public/default/user.registered"),
        event_bus.run_subscription("persistent://public/default/order.created")
    )


async def run_demo():
    """运行完整的演示"""
    # 启动事件订阅任务
    subscription_task = asyncio.create_task(subscribe_to_events())
    
    # 等待一会儿以确保订阅已经准备好
    await asyncio.sleep(2)
    
    # 使用不同编解码器发布事件
    await publish_events_with_codec("json")
    await asyncio.sleep(3)  # 等待处理完成
    
    await publish_events_with_codec("protobuf")
    await asyncio.sleep(3)  # 等待处理完成
    
    await publish_events_with_codec("avro")
    await asyncio.sleep(3)  # 等待处理完成
    
    # 取消订阅任务
    subscription_task.cancel()
    try:
        await subscription_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    print("\n===== 事件总线多编解码器示例 =====\n")
    print("该示例展示如何使用不同的编解码器配置事件总线并发布/订阅事件")
    asyncio.run(run_demo()) 