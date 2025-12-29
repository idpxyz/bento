"""Category 聚合根 - 智能 ID 处理"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot

if TYPE_CHECKING:
    pass


@dataclass
class Category(AggregateRoot):
    """Category 聚合根

    ✅ 智能 ID 处理：
    - 使用 Bento 标准 ID 类型
    - 自动序列化/反序列化
    - 类型安全

    开发人员只需要：
    1. 定义字段
    2. 实现业务方法

    框架自动处理：
    - 事件收集（调用 add_event）
    - 持久化（Repository）
    - 事务管理（UnitOfWork）
    """

    id: ID  # ✅ 使用标准 ID 类型
    name: str
    description: str
    parent_id: ID | None = None  # ✅ 父分类 ID 也使用标准类型

    def __post_init__(self):
        super().__init__(id=str(self.id))  # ✅ ID 自动转字符串

    def is_root(self) -> bool:
        """检查是否为根分类"""
        return self.parent_id is None

    def change_name(self, new_name: str) -> None:
        """修改分类名称"""
        if not new_name or not new_name.strip():
            raise ValueError("Category name cannot be empty")
        self.name = new_name.strip()

    def move_to(self, new_parent_id: ID | None) -> None:
        """移动到新的父分类"""
        self.parent_id = new_parent_id

    @classmethod
    def create(cls, id: ID, name: str, description: str, parent_id: ID | None = None) -> Category:
        """Factory method to create a new category with CategoryCreated event.

        This method ensures that the CategoryCreated event is automatically
        triggered when a new category is created.
        """
        # Import here to avoid circular import
        from contexts.catalog.domain.events.categorycreated_event import CategoryCreated

        category = cls(
            id=id,
            name=name,
            description=description,
            parent_id=parent_id,
        )

        # Trigger CategoryCreated event with aggregate_id set to category id
        event = CategoryCreated(
            aggregate_id=str(category.id),
            category_id=str(category.id),
            category_name=category.name,
            parent_id=str(category.parent_id) if category.parent_id else None,
        )
        category.add_event(event)

        return category

    def mark_deleted(self) -> None:
        """标记分类为已删除，触发事件"""
        # Import here to avoid circular import
        from contexts.catalog.domain.events.categorydeleted_event import CategoryDeleted

        event = CategoryDeleted(
            category_id=str(self.id),
            category_name=self.name,
        )
        self.add_event(event)
