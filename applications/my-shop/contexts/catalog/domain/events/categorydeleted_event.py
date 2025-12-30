"""CategoryDeleted 领域事件"""

from dataclasses import dataclass, field

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class CategoryDeleted(DomainEvent):
    """CategoryDeleted 事件

    当分类被删除时触发。
    """

    # 事件字段（使用 field() 确保字段顺序正确）
    category_id: str = field(default="")
    category_name: str = field(default="")

    # 覆盖基类的 topic 字段
    topic: str = field(default="catalog.category.deleted")
