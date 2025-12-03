"""{{Name}} 领域事件"""
from dataclasses import dataclass

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class {{Name}}(DomainEvent):
    """{{Name}} 事件

    开发人员只需要：
    1. 定义事件字段（业务数据）
    2. 在聚合根中触发事件（调用 add_event）

    框架自动处理：
    - 事件持久化（Outbox 模式保证至少一次投递）
    - 事件发布（消息队列 / 事件总线）
    - 事件追踪（event_id, occurred_at, topic）
    - 事务一致性（与聚合根保存在同一事务中）
    
    事件字段：
    - topic: 事件主题/类型（用于路由和订阅）
    - event_id: 事件唯一标识（自动生成）
    - occurred_at: 事件发生时间（自动生成）
    - aggregate_id: 聚合根 ID（自动填充）
    """
    topic: str = "{{context}}.{{name_lower}}.{{EventName}}"

    # TODO: 添加业务字段（必填字段需使用关键字参数实例化）
    # 例如:
    # {{name_lower}}_id: str  # 聚合根 ID
    # user_id: str           # 操作者 ID
    # old_status: str        # 变更前状态
    # new_status: str        # 变更后状态
    #
    # 使用示例（在聚合根中）:
    # class {{Name}}(AggregateRoot):
    #     def change_status(self, new_status: str):
    #         old_status = self.status
    #         self.status = new_status
    #         
    #         # 触发领域事件
    #         self.add_event({{Name}}StatusChanged(
    #             {{name_lower}}_id=str(self.id),
    #             old_status=old_status,
    #             new_status=new_status,
    #         ))
    #
    # 事件订阅示例（在 Event Handler 中）:
    # @event_handler("{{context}}.{{name_lower}}.{{EventName}}")
    # async def handle_{{EventName}}(event: {{Name}}):
    #     # 处理事件逻辑
    #     logger.info(f"处理事件: {event.topic}")
    #     # 调用其他服务、发送通知等
