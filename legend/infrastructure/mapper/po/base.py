"""持久化对象映射器基类模块。

提供持久化对象映射器的基类实现。

Key Components:
- POMapper: 持久化对象映射器基类
"""

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    get_type_hints,
)

from ..core.mapper import BidirectionalMapperImpl, MapperBuilder
from ..core.strategies import AutoMappingStrategy, CompositeMappingStrategy
from ..registry import po_mapper_registry

# 类型变量
D = TypeVar('D')  # 领域对象类型
P = TypeVar('P')  # 持久化对象类型


class POMapper(BidirectionalMapperImpl[D, P], Generic[D, P]):
    """持久化对象映射器基类

    提供领域对象和持久化对象之间的映射功能。
    """

    def __init__(self, domain_type: Type[D], po_type: Type[P], auto_map: bool = True, exclude_paths: Optional[List[str]] = None):
        """初始化持久化对象映射器

        Args:
            domain_type: 领域对象类型
            po_type: 持久化对象类型
            auto_map: 是否启用自动映射
            exclude_paths: 排除自动映射的属性路径列表
        """
        # 创建映射策略
        if auto_map:
            to_target_strategy = AutoMappingStrategy(
                domain_type, po_type, exclude_paths or [])
            to_source_strategy = AutoMappingStrategy(
                po_type, domain_type, exclude_paths or [])
        else:
            to_target_strategy = CompositeMappingStrategy(domain_type, po_type)
            to_source_strategy = CompositeMappingStrategy(po_type, domain_type)

        # 调用父类构造函数
        super().__init__(
            source_type=domain_type,
            target_type=po_type,
            to_target_strategy=to_target_strategy,
            to_source_strategy=to_source_strategy
        )

        # 注册到全局注册表
        po_mapper_registry.register_domain_to_po(domain_type, po_type, self)

    def to_po(self, domain: D) -> P:
        """将领域对象映射到持久化对象

        Args:
            domain: 领域对象

        Returns:
            P: 映射后的持久化对象
        """
        return self.map(domain)

    def to_domain(self, po: P) -> D:
        """将持久化对象映射到领域对象

        Args:
            po: 持久化对象

        Returns:
            D: 映射后的领域对象
        """
        return self.map_to_source(po)

    def to_pos(self, domains: List[D]) -> List[P]:
        """批量将领域对象映射到持久化对象

        Args:
            domains: 领域对象列表

        Returns:
            List[P]: 映射后的持久化对象列表
        """
        return self.map_list(domains)

    def to_domains(self, pos: List[P]) -> List[D]:
        """批量将持久化对象映射到领域对象

        Args:
            pos: 持久化对象列表

        Returns:
            List[D]: 映射后的领域对象列表
        """
        return self.map_to_source_list(pos)
