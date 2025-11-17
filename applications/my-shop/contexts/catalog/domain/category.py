"""Category 聚合根"""

from dataclasses import dataclass

from bento.domain.aggregate import AggregateRoot


@dataclass
class Category(AggregateRoot):
    """Category 聚合根

    开发人员只需要：
    1. 定义字段
    2. 实现业务方法

    框架自动处理：
    - 事件收集（调用 add_event）
    - 持久化（Repository）
    - 事务管理（UnitOfWork）
    """

    id: str
    name: str
    description: str
    parent_id: str | None = None  # 根分类没有父分类

    def __post_init__(self):
        super().__init__(id=self.id)

    def is_root(self) -> bool:
        """检查是否为根分类"""
        return self.parent_id is None

    def change_name(self, new_name: str) -> None:
        """修改分类名称"""
        if not new_name or not new_name.strip():
            raise ValueError("Category name cannot be empty")
        self.name = new_name.strip()

    def move_to(self, new_parent_id: str | None) -> None:
        """移动到新的父分类"""
        self.parent_id = new_parent_id
