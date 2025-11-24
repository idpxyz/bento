"""Category 聚合根 - 智能 ID 处理"""

from dataclasses import dataclass

from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot


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
