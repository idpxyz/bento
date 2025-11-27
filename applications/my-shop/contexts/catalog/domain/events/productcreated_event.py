"""ProductCreated 领域事件"""

from dataclasses import dataclass

from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
@dataclass(frozen=True)
class ProductCreated(DomainEvent):
    """ProductCreated 事件

    开发人员只需要：
    1. 定义事件字段
    2. 在聚合根中触发事件（add_event）

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    topic: str = "productcreated"

    # TODO: 添加事件字段
    # 例如:
    # productcreated_id: str
    # user_id: str
    # old_value: str
    # new_value: str
