"""事件总线示例。



展示如何使用端口与适配器架构的事件总线。

"""



import asyncio

import logging

from typing import List



from idp.framework.domain.event.base import DomainEvent

from idp.framework.domain.event.context import event_bus_context

from idp.framework.domain.event.ports import EventBusPort

from idp.framework.domain.event.examples.examples import UserCreatedEvent, UserUpdatedEvent

from idp.framework.infrastructure.messaging_full.adapter.factory import EventBusAdapterFactory

from idp.framework.infrastructure.messaging_full.core.config import MessageBusConfig, MessageBusType



# 配置日志

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)





async def handle_user_created(event: DomainEvent) -> bool:

    """处理用户创建事件

    

    Args:

        event: 用户创建事件

        

    Returns:

        bool: 处理结果

    """

    if isinstance(event, UserCreatedEvent):

        logger.info(f"处理用户创建事件: {event.username} ({event.email})")

        return True

    return False





async def handle_user_updated(event: DomainEvent) -> bool:

    """处理用户更新事件

    

    Args:

        event: 用户更新事件

        

    Returns:

        bool: 处理结果

    """

    if isinstance(event, UserUpdatedEvent):

        logger.info(f"处理用户更新事件: {event.user_id}, 变更: {event.changes}")

        return True

    return False





async def publish_events(event_bus: EventBusPort) -> None:

    """发布事件

    

    Args:

        event_bus: 事件总线

    """

    # 创建用户创建事件

    user_created = UserCreatedEvent(

        user_id="user-123",

        username="john_doe",

        email="john@example.com",

        roles=["user", "admin"],

        metadata={"source": "user_service", "ip_address": "192.168.1.1"}

    )

    

    # 发布用户创建事件

    message_id = await event_bus.publish(user_created)

    logger.info(f"已发布用户创建事件，消息ID: {message_id}")

    

    # 等待事件处理

    await asyncio.sleep(1)

    

    # 创建用户更新事件

    user_updated = UserUpdatedEvent(

        user_id="user-123",

        changes={"username": "john_smith", "email": "john.smith@example.com"},

        metadata={"source": "profile_service"}

    )

    

    # 发布用户更新事件

    message_id = await event_bus.publish(user_updated)

    logger.info(f"已发布用户更新事件，消息ID: {message_id}")

    

    # 等待事件处理

    await asyncio.sleep(1)





async def example_with_context_manager() -> None:

    """使用上下文管理器的示例"""

    logger.info("=== 使用上下文管理器的示例 ===")

    

    # 创建事件总线适配器

    config = MessageBusConfig(bus_type=MessageBusType.MEMORY)

    event_bus = await EventBusAdapterFactory.create_adapter(config)

    

    # 使用上下文管理器

    async with event_bus_context(event_bus) as bus:

        # 注册事件类型

        bus.register_event_types([UserCreatedEvent, UserUpdatedEvent])

        

        # 订阅事件

        await bus.subscribe(UserCreatedEvent, handle_user_created)

        await bus.subscribe(UserUpdatedEvent, handle_user_updated)

        

        # 发布事件

        await publish_events(bus)





async def example_with_manual_lifecycle() -> None:

    """手动管理生命周期的示例"""

    logger.info("=== 手动管理生命周期的示例 ===")

    

    # 获取事件总线适配器单例

    event_bus = await EventBusAdapterFactory.get_instance()

    

    try:

        # 初始化事件总线

        await event_bus.initialize()

        

        # 注册事件类型

        event_bus.register_event_types([UserCreatedEvent, UserUpdatedEvent])

        

        # 订阅事件

        await event_bus.subscribe(UserCreatedEvent, handle_user_created)

        await event_bus.subscribe(UserUpdatedEvent, handle_user_updated)

        

        # 发布事件

        await publish_events(event_bus)

    finally:

        # 关闭事件总线

        await event_bus.shutdown()





async def example_with_dependency_injection(event_bus: EventBusPort) -> None:

    """依赖注入的示例

    

    Args:

        event_bus: 事件总线

    """

    logger.info("=== 依赖注入的示例 ===")

    

    # 注册事件类型

    event_bus.register_event_types([UserCreatedEvent, UserUpdatedEvent])

    

    # 订阅事件

    await event_bus.subscribe(UserCreatedEvent, handle_user_created)

    await event_bus.subscribe(UserUpdatedEvent, handle_user_updated)

    

    # 发布事件

    await publish_events(event_bus)





async def main() -> None:

    """主函数"""

    # 使用上下文管理器的示例

    await example_with_context_manager()

    

    # 手动管理生命周期的示例

    await example_with_manual_lifecycle()

    

    # 依赖注入的示例

    event_bus = await EventBusAdapterFactory.create_adapter()

    async with event_bus_context(event_bus) as bus:

        await example_with_dependency_injection(bus)





if __name__ == "__main__":

    asyncio.run(main()) 