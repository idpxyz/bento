"""通用排序顺序管理器

Framework 通用组件，提供高效的排序顺序管理功能。
适用于任何需要维护有序集合的领域场景。

设计原则：
1. 高度通用：不依赖特定业务领域
2. 类型安全：支持泛型类型
3. 性能优化：使用索引和批量操作
4. 易于使用：提供简洁的API
5. 可扩展：支持自定义排序策略
"""

from dataclasses import dataclass
from typing import Generic, List, Optional, Protocol, TypeVar

from idp.framework.exception.classified import DomainException
from idp.framework.exception.code.domain import DomainExceptionCode

# 类型变量定义
T = TypeVar('T')


class SortableItem(Protocol):
    """可排序项目的协议

    任何实现了这个协议的对象都可以被排序管理器管理。
    """
    @property
    def id(self) -> str:
        """项目唯一标识符"""
        ...

    @property
    def sort_order(self) -> int:
        """排序顺序"""
        ...

    @sort_order.setter
    def sort_order(self, value: int) -> None:
        """设置排序顺序"""
        ...


@dataclass
class SortableItemWrapper(Generic[T]):
    """可排序项目包装器

    将任意对象包装为可排序项目，用于排序管理器。
    """
    item: T
    id: str
    sort_order: int

    def __post_init__(self):
        """后初始化，设置排序顺序到原始对象"""
        if hasattr(self.item, 'sort_order'):
            self.item.sort_order = self.sort_order


class SortOrderManager(Generic[T]):
    """通用排序顺序管理器

    职责：
    1. 集中管理所有排序相关的逻辑
    2. 提供高效的排序操作
    3. 确保排序顺序的一致性和连续性
    4. 支持批量操作优化
    5. 支持自定义排序策略
    """

    def __init__(self, items: Optional[List[T]] = None,
                 id_extractor: Optional[callable] = None,
                 sort_order_extractor: Optional[callable] = None,
                 sort_order_setter: Optional[callable] = None):
        """初始化排序管理器

        Args:
            items: 要管理的项目列表
            id_extractor: ID提取函数，默认使用item.id
            sort_order_extractor: 排序顺序提取函数，默认使用item.sort_order
            sort_order_setter: 排序顺序设置函数，默认使用item.sort_order = value
        """
        self.items = items or []
        self.id_extractor = id_extractor or (
            lambda item: getattr(item, 'id', str(id(item))))
        self.sort_order_extractor = sort_order_extractor or (
            lambda item: getattr(item, 'sort_order', 0))
        self.sort_order_setter = sort_order_setter or (
            lambda item, value: setattr(item, 'sort_order', value))

        # 创建包装器
        self._wrappers = self._create_wrappers()
        self._rebuild_indexes()

    def _create_wrappers(self) -> List[SortableItemWrapper[T]]:
        """创建项目包装器"""
        wrappers = []
        for item in self.items:
            wrapper = SortableItemWrapper(
                item=item,
                id=self.id_extractor(item),
                sort_order=self.sort_order_extractor(item)
            )
            wrappers.append(wrapper)
        return wrappers

    def _rebuild_indexes(self) -> None:
        """重建索引"""
        self.id_to_wrapper = {
            wrapper.id: wrapper for wrapper in self._wrappers}
        self.order_to_wrapper = {
            wrapper.sort_order: wrapper for wrapper in self._wrappers}
        self.max_order = max(
            wrapper.sort_order for wrapper in self._wrappers) if self._wrappers else 0

    def get_max_order(self) -> int:
        """获取最大排序顺序"""
        return self.max_order

    def validate_position(self, position: int, allow_append: bool = True) -> None:
        """验证位置是否有效

        Args:
            position: 目标位置
            allow_append: 是否允许追加到末尾

        Raises:
            DomainException: 当位置无效时
        """
        max_position = len(self._wrappers) + \
            1 if allow_append else len(self._wrappers)

        if position < 1:
            raise DomainException(
                code=DomainExceptionCode.SORT_ORDER_OUT_OF_RANGE,
                details={
                    "message": "Sort order must be at least 1",
                    "provided_position": position,
                    "suggestion": "Please provide a position >= 1"
                }
            )

        if position > max_position:
            raise DomainException(
                code=DomainExceptionCode.SORT_ORDER_OUT_OF_RANGE,
                details={
                    "message": f"Position cannot exceed {max_position}",
                    "provided_position": position,
                    "max_allowed": max_position,
                    "suggestion": f"Please provide a position between 1 and {max_position}"
                }
            )

    def insert_at_position(self, item: T, position: int) -> None:
        """在指定位置插入项目

        Args:
            item: 要插入的项目
            position: 目标位置

        Raises:
            DomainException: 当位置无效时
        """
        # 验证位置
        self.validate_position(position, allow_append=True)

        # 创建包装器
        wrapper = SortableItemWrapper(
            item=item,
            id=self.id_extractor(item),
            sort_order=position
        )

        # 如果位置已存在，调整现有元素
        if position <= self.max_order:
            self._batch_adjust_orders(position, 1)

        # 设置新元素的排序顺序
        wrapper.sort_order = position
        self.sort_order_setter(item, position)

        # 添加到包装器列表（不直接操作 SQLAlchemy 集合）
        self._wrappers.append(wrapper)

        # 重建索引
        self._rebuild_indexes()

    def remove_by_id(self, item_id: str) -> None:
        """根据ID删除项目

        Args:
            item_id: 要删除的项目ID

        Raises:
            DomainException: 当项目不存在时
        """
        # 查找要删除的包装器
        wrapper_to_remove = self.id_to_wrapper.get(item_id)
        if not wrapper_to_remove:
            raise DomainException(
                code=DomainExceptionCode.ENTITY_NOT_FOUND,
                details={
                    "item_id": item_id,
                    "suggestion": "Please provide a valid item ID"
                }
            )

        # 记录删除位置
        position = wrapper_to_remove.sort_order

        # 删除包装器（不直接操作 SQLAlchemy 集合）
        self._wrappers = [w for w in self._wrappers if w.id != item_id]

        # 调整后续元素的排序顺序
        self._batch_adjust_orders(position + 1, -1)

        # 重建索引
        self._rebuild_indexes()

    def move_to_position(self, item_id: str, new_position: int) -> None:
        """将项目移动到新位置

        Args:
            item_id: 要移动的项目ID
            new_position: 新位置

        Raises:
            DomainException: 当项目不存在或位置无效时
        """
        # 查找要移动的包装器
        wrapper_to_move = self.id_to_wrapper.get(item_id)
        if not wrapper_to_move:
            raise DomainException(
                code=DomainExceptionCode.ENTITY_NOT_FOUND,
                details={
                    "item_id": item_id,
                    "suggestion": "Please provide a valid item ID"
                }
            )

        # 验证新位置
        self.validate_position(new_position, allow_append=True)

        # 记录当前位置
        current_position = wrapper_to_move.sort_order

        # 如果位置相同，无需移动
        if current_position == new_position:
            return

        # 根据移动方向调整其他元素
        if new_position < current_position:
            # 向前移动：将中间元素向后移动
            for wrapper in self._wrappers:
                if (wrapper.id != item_id and
                        new_position <= wrapper.sort_order < current_position):
                    wrapper.sort_order += 1
                    self.sort_order_setter(wrapper.item, wrapper.sort_order)
        else:
            # 向后移动：将中间元素向前移动
            for wrapper in self._wrappers:
                if (wrapper.id != item_id and
                        current_position < wrapper.sort_order <= new_position):
                    wrapper.sort_order -= 1
                    self.sort_order_setter(wrapper.item, wrapper.sort_order)

        # 设置新位置
        wrapper_to_move.sort_order = new_position
        self.sort_order_setter(wrapper_to_move.item, new_position)

        # 重建索引
        self._rebuild_indexes()

    def _batch_adjust_orders(self, start_position: int, delta: int, exclude_id: Optional[str] = None) -> None:
        """批量调整排序顺序

        Args:
            start_position: 开始调整的位置
            delta: 调整的增量（正数向后移动，负数向前移动）
            exclude_id: 要排除的项目ID
        """
        for wrapper in self._wrappers:
            if wrapper.sort_order >= start_position and wrapper.id != exclude_id:
                wrapper.sort_order += delta
                self.sort_order_setter(wrapper.item, wrapper.sort_order)

    def get_sorted_items(self) -> List[T]:
        """获取排序后的项目列表"""
        sorted_wrappers = sorted(self._wrappers, key=lambda x: x.sort_order)
        return [wrapper.item for wrapper in sorted_wrappers]

    def get_item_at_position(self, position: int) -> Optional[T]:
        """获取指定位置的项目"""
        wrapper = self.order_to_wrapper.get(position)
        return wrapper.item if wrapper else None

    def get_item_by_id(self, item_id: str) -> Optional[T]:
        """根据ID获取项目"""
        wrapper = self.id_to_wrapper.get(item_id)
        return wrapper.item if wrapper else None

    def has_position(self, position: int) -> bool:
        """检查指定位置是否有项目"""
        return position in self.order_to_wrapper

    def get_available_positions(self) -> List[int]:
        """获取可用的位置列表"""
        return sorted(self.order_to_wrapper.keys())

    def get_next_position(self) -> int:
        """获取下一个可用位置"""
        return self.max_order + 1

    def compact_orders(self) -> None:
        """压缩排序顺序，确保连续性"""
        sorted_wrappers = sorted(self._wrappers, key=lambda x: x.sort_order)
        for i, wrapper in enumerate(sorted_wrappers):
            wrapper.sort_order = i + 1
            self.sort_order_setter(wrapper.item, wrapper.sort_order)
        self._rebuild_indexes()

    def add_item(self, item: T, position: Optional[int] = None) -> None:
        """添加项目

        Args:
            item: 要添加的项目
            position: 指定位置，如果为None则追加到末尾
        """
        if position is None:
            position = self.get_next_position()
        self.insert_at_position(item, position)

    def remove_item(self, item: T) -> None:
        """删除项目

        Args:
            item: 要删除的项目
        """
        item_id = self.id_extractor(item)
        self.remove_by_id(item_id)

    def update_item_position(self, item: T, new_position: int) -> None:
        """更新项目位置

        Args:
            item: 要更新的项目
            new_position: 新位置
        """
        item_id = self.id_extractor(item)
        self.move_to_position(item_id, new_position)

    def get_item_count(self) -> int:
        """获取项目数量"""
        return len(self._wrappers)

    def is_empty(self) -> bool:
        """检查是否为空"""
        return len(self._wrappers) == 0

    def clear(self) -> None:
        """清空所有项目"""
        self._wrappers.clear()
        self._rebuild_indexes()
