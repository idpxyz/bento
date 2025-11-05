from typing import TypeVar, Generic, Type, Dict, Any
from idp.framework.domain.event.base import DomainEvent
from idp.framework.infrastructure.mapper import Mapper, MapperBuilder

S = TypeVar('S', bound=DomainEvent)
T = TypeVar('T')

class EventMapper(Generic[S, T]):
    """
    事件映射器

    用于将领域事件映射为DTO或其他表示形式
    """

    def __init__(self, event_type: Type[S], target_type: Type[T], mapper: Mapper[S, T]):
        """
        初始化事件映射器

        Args:
            event_type: 事件类型
            target_type: 目标类型
            mapper: 映射器
        """
        self.event_type = event_type
        self.target_type = target_type
        self.mapper = mapper

    def map(self, event: S) -> T:
        """
        映射事件

        Args:
            event: 要映射的事件

        Returns:
            映射后的对象
        """
        return self.mapper.map(event)

    @staticmethod
    def create(event_type: Type[S], target_type: Type[T], mapping_config: Dict[str, Any] = None) -> 'EventMapper[S, T]':
        """
        创建事件映射器

        Args:
            event_type: 事件类型
            target_type: 目标类型
            mapping_config: 映射配置

        Returns:
            事件映射器
        """
        builder = MapperBuilder.for_types(event_type, target_type)

        # 应用映射配置
        if mapping_config:
            for source_path, target_path in mapping_config.get("field_mappings", {}).items():
                builder.map(source_path, target_path)

            for target_path, mapping_func in mapping_config.get("custom_mappings", {}).items():
                builder.map_custom(target_path, mapping_func)

        # 自动映射其余字段
        builder.auto_map()

        # 构建映射器
        mapper = builder.build()

        return EventMapper(event_type, target_type, mapper)
