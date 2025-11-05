"""映射器实现模块。

提供映射器接口的具体实现。

Key Components:
- GenericMapper: 通用映射器实现
- MapperBuilder: 映射器构建器实现
"""

import concurrent.futures
import inspect
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.mapper import MapperExceptionCode
from idp.framework.infrastructure.mapper.core.context import MappingContext
from idp.framework.infrastructure.mapper.core.converter import type_converter_registry
from idp.framework.infrastructure.mapper.core.interfaces import (
    BidirectionalMapper,
    IMapperBuilder,
    Mapper,
)
from idp.framework.infrastructure.mapper.core.strategies import (
    AutoMappingStrategy,
    CompositeMappingStrategy,
    ExplicitMappingStrategy,
    MappingStrategy,
)

# 类型变量
S = TypeVar('S')  # 源类型
T = TypeVar('T')  # 目标类型


class GenericMapper(Mapper[S, T], Generic[S, T]):
    """通用映射器实现

    基于映射策略将源对象映射到目标对象。
    """

    def __init__(self, source_type: Type[S], target_type: Type[T], strategy: MappingStrategy[S, T]):
        """初始化通用映射器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            strategy: 映射策略

        Raises:
            Exception: 如果源类型或目标类型为空
        """
        if not source_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Source type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID
            )

        if not target_type:
            raise idp_exception_factory.infrastructure_exception(
                message="Target type cannot be None",
                code=InfrastructureExceptionCode.MAPPER_CONFIG_INVALID
            )

        self.source_type = source_type
        self.target_type = target_type
        self.strategy = strategy

    def map(self, source: S) -> T:
        """将源对象映射到目标类型的新实例

        Args:
            source: 源对象

        Returns:
            T: 映射后的目标对象
        """
        if source is None:
            return None

        # 创建映射上下文
        context = MappingContext()
        return self.map_with_context(source, context)

    def map_with_context(self, source: S, context: MappingContext) -> T:
        """使用上下文映射源对象到目标类型的新实例

        Args:
            source: 源对象
            context: 映射上下文

        Returns:
            T: 映射后的目标对象
        """
        if source is None:
            return None

        source_id = id(source)

        # 检查是否已经映射过该对象，如果是，则直接返回已映射的对象
        if context.has_mapped_object(source):
            return context.get_mapped_object(source)

        try:
            # 如果目标类型是 dataclass 且有必需参数，自动用 source 的同名属性补全
            import dataclasses
            if dataclasses.is_dataclass(self.target_type):
                fields = dataclasses.fields(self.target_type)
                kwargs = {}
                for f in fields:
                    if f.init and hasattr(source, f.name):
                        kwargs[f.name] = getattr(source, f.name)
                target = self.target_type(**kwargs)
                self.strategy.apply_with_context(source, target, context)
                context.register_mapped_object(source, target)
                return target
            # 默认逻辑
            if hasattr(self.strategy, 'apply_with_context'):
                target = self.target_type()
                self.strategy.apply_with_context(source, target, context)
                context.register_mapped_object(source, target)
                return target
            else:
                target = self.strategy.apply(source, self.target_type)
                if target is not None:
                    context.register_mapped_object(source, target)
                return target
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map object: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": type(
                    source).__name__, "target_type": self.target_type.__name__},
                cause=e
            )

    def map_to_target(self, source: S, target: T) -> None:
        """将源对象映射到已存在的目标对象

        Args:
            source: 源对象
            target: 目标对象
        """
        if source is None or target is None:
            return

        # 创建映射上下文
        context = MappingContext()
        self.map_to_target_with_context(source, target, context)

    def map_to_target_with_context(self, source: S, target: T, context: MappingContext) -> None:
        """使用上下文将源对象映射到现有的目标对象

        Args:
            source: 源对象
            target: 目标对象
            context: 映射上下文
        """
        if source is None or target is None:
            return

        source_id = id(source)

        # 检查是否已经映射过该对象，如果是，则直接返回
        if context.has_mapped_object(source):
            return

        try:
            # 注册映射对象
            context.register_mapped_object(source, target)

            # 使用策略映射到目标实例
            if hasattr(self.strategy, 'apply_with_context'):
                # 如果策略支持上下文，使用上下文映射
                self.strategy.apply_with_context(source, target, context)
            else:
                # 如果策略不支持上下文，使用普通方法
                self.strategy.apply_to_existing(source, target)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map object to target: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": type(
                    source).__name__, "target_type": type(target).__name__},
                cause=e
            )

    def map_list(self, source_list: List[S]) -> List[T]:
        """将源对象列表映射到目标类型的新实例列表

        Args:
            source_list: 源对象列表

        Returns:
            List[T]: 映射后的目标对象列表
        """
        if source_list is None:
            return None

        # 创建映射上下文
        context = MappingContext()
        return self.map_list_with_context(source_list, context)

    def map_list_with_context(self, source_list: List[S], context: MappingContext) -> List[T]:
        """将源对象列表映射到目标类型的新实例列表，使用映射上下文

        Args:
            source_list: 源对象列表
            context: 映射上下文

        Returns:
            List[T]: 映射后的目标对象列表
        """
        if source_list is None:
            return None

        try:
            result = []
            for source in source_list:
                target = self.map_with_context(source, context)
                result.append(target)
            return result
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to map list: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": f"List[{self.source_type.__name__}]",
                         "target_type": f"List[{self.target_type.__name__}]"},
                cause=e
            )


class MapperBuilder(IMapperBuilder[S, T], Generic[S, T]):
    """映射器构建器实现

    用于构建映射器的构建器实现，支持链式调用配置映射规则
    """

    @staticmethod
    def for_types(source_type: Type[S], target_type: Type[T]) -> 'MapperBuilder[S, T]':
        """
        指定源类型和目标类型

        Args:
            source_type: 源类型
            target_type: 目标类型

        Returns:
            MapperBuilder: 构建器实例
        """
        return MapperBuilder(source_type, target_type)

    def __init__(self, source_type: Type[S], target_type: Type[T]):
        """初始化映射器构建器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
        """
        self.source_type = source_type
        self.target_type = target_type
        self.property_mappings: List[Tuple[str, str]] = []
        self.custom_mappings: List[Tuple[str, Callable[[S], Any]]] = []
        self.reverse_mappings: List[Tuple[str, Callable[[T], Any]]] = []
        self.nested_mappings: List[Tuple[str, str, Mapper]] = []
        self.collection_mappings: List[Tuple[str, str, Mapper]] = []
        self.auto_mapping_enabled = False
        self.exclude_paths: List[str] = []
        self.preserve_domain_events = True
        self.batch_size_threshold = 100
        self.max_workers = 10

    def map(self, source_path: str, target_path: str) -> 'MapperBuilder[S, T]':
        """配置源路径到目标路径的映射

        Args:
            source_path: 源对象属性路径
            target_path: 目标对象属性路径

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        if not source_path or not target_path:
            raise InfrastructureException(
                message="Source path and target path cannot be empty",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_path": source_path,
                         "target_path": target_path}
            )

        self.property_mappings.append((source_path, target_path))
        return self

    def map_custom(self, target_path: str, mapping_func: Callable[[S], Any]) -> 'MapperBuilder[S, T]':
        """配置自定义映射函数

        Args:
            target_path: 目标对象属性路径
            mapping_func: 映射函数，接收源对象作为参数，返回映射后的值

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        if not target_path or not callable(mapping_func):
            raise InfrastructureException(
                message="Target path cannot be empty and mapping function must be callable",
                code=MapperExceptionCode.MAPPER_CUSTOM_CONFIG_INVALID,
                details={"target_path": target_path,
                         "mapping_func": str(mapping_func)}
            )

        self.custom_mappings.append((target_path, mapping_func))
        return self

    def map_reverse(self, source_path: str, mapping_func: Callable[[T], Any]) -> 'MapperBuilder[S, T]':
        """配置自定义反向映射函数

        Args:
            source_path: 源对象属性路径
            mapping_func: 映射函数，接收目标对象作为参数，返回映射后的值

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        if not source_path or not callable(mapping_func):
            raise InfrastructureException(
                message="Source path cannot be empty and mapping function must be callable",
                code=MapperExceptionCode.MAPPER_REVERSE_CONFIG_INVALID,
                details={"source_path": source_path,
                         "mapping_func": str(mapping_func)}
            )

        self.reverse_mappings.append((source_path, mapping_func))
        return self

    def map_nested(self, source_path: str, target_path: str, mapper: Mapper) -> 'MapperBuilder[S, T]':
        """配置嵌套对象映射器

        Args:
            source_path: 源对象中嵌套对象的属性路径
            target_path: 目标对象中嵌套对象的属性路径
            mapper: 用于映射嵌套对象的映射器

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        if not source_path or not target_path or not mapper:
            raise InfrastructureException(
                message="Source path, target path and mapper cannot be empty",
                code=MapperExceptionCode.MAPPER_NESTED_CONFIG_INVALID,
                details={"source_path": source_path,
                         "target_path": target_path, "mapper": str(mapper)}
            )

        self.nested_mappings.append((source_path, target_path, mapper))
        return self

    def map_collection(self, source_path: str, target_path: str, mapper: Mapper) -> 'MapperBuilder[S, T]':
        """配置集合对象映射器

        Args:
            source_path: 源对象中集合的属性路径
            target_path: 目标对象中集合的属性路径
            mapper: 用于映射集合中元素的映射器

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        if not source_path or not target_path or not mapper:
            raise InfrastructureException(
                message="Source path, target path and mapper cannot be empty",
                code=MapperExceptionCode.MAPPER_COLLECTION_CONFIG_INVALID,
                details={"source_path": source_path,
                         "target_path": target_path, "mapper": str(mapper)}
            )

        self.collection_mappings.append((source_path, target_path, mapper))
        return self

    def auto_map(self, exclude_paths: Optional[List[str]] = None) -> 'MapperBuilder[S, T]':
        """启用自动映射

        Args:
            exclude_paths: 排除自动映射的属性路径列表

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        self.auto_mapping_enabled = True
        if exclude_paths:
            self.exclude_paths.extend(exclude_paths)
        return self

    def preserve_events(self, preserve: bool = True) -> 'MapperBuilder[S, T]':
        """设置是否保留领域事件

        Args:
            preserve: 是否保留领域事件

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        self.preserve_domain_events = preserve
        return self

    def configure_batch_mapping(self, batch_size_threshold: int = 100, max_workers: int = 10) -> 'MapperBuilder[S, T]':
        """配置批量映射参数

        Args:
            batch_size_threshold: 启用并行处理的批量大小阈值
            max_workers: 最大并行工作线程数

        Returns:
            MapperBuilder: 构建器实例，支持链式调用
        """
        if batch_size_threshold <= 0:
            raise InfrastructureException(
                message="Batch size threshold must be greater than 0",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"batch_size_threshold": batch_size_threshold}
            )

        if max_workers <= 0:
            raise InfrastructureException(
                message="Max workers must be greater than 0",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"max_workers": max_workers}
            )

        self.batch_size_threshold = batch_size_threshold
        self.max_workers = max_workers
        return self

    def build(self) -> Mapper[S, T]:
        """构建映射器

        Returns:
            Mapper[S, T]: 构建的映射器实例
        """
        try:
            # 验证映射配置
            self._validate_mapping_configuration()

            # 创建映射策略
            to_target_strategy = ExplicitMappingStrategy[S, T]()
            to_source_strategy = ExplicitMappingStrategy[T, S]()

            # 配置属性映射
            for source_path, target_path in self.property_mappings:
                to_target_strategy.add_property_mapping(
                    source_path, target_path)
                to_source_strategy.add_property_mapping(
                    target_path, source_path)

            # 配置自定义映射
            for target_path, mapping_func in self.custom_mappings:
                to_target_strategy.add_custom_mapping(
                    target_path, mapping_func)

            # 配置自定义反向映射
            for source_path, mapping_func in self.reverse_mappings:
                to_source_strategy.add_custom_mapping(
                    source_path, mapping_func)

            # 配置嵌套映射
            for source_path, target_path, mapper in self.nested_mappings:
                to_target_strategy.add_nested_mapping(
                    source_path, target_path, mapper)
                to_source_strategy.add_nested_mapping(
                    target_path, source_path, mapper)

            # 配置集合映射
            for source_path, target_path, mapper in self.collection_mappings:
                to_target_strategy.add_collection_mapping(
                    source_path, target_path, mapper)
                to_source_strategy.add_collection_mapping(
                    target_path, source_path, mapper)

            # 如果启用自动映射，添加自动映射策略
            if self.auto_mapping_enabled:
                auto_target_strategy = AutoMappingStrategy(
                    self.source_type, self.target_type, self.exclude_paths)
                auto_source_strategy = AutoMappingStrategy(
                    self.target_type, self.source_type, self.exclude_paths)

                composite_target_strategy = CompositeMappingStrategy([
                    auto_target_strategy,
                    to_target_strategy
                ])

                composite_source_strategy = CompositeMappingStrategy([
                    auto_source_strategy,
                    to_source_strategy
                ])
            else:
                composite_target_strategy = to_target_strategy
                composite_source_strategy = to_source_strategy

            # 创建映射器
            mapper = BidirectionalMapperImpl(
                self.source_type,
                self.target_type,
                composite_target_strategy,
                composite_source_strategy,
                self.preserve_domain_events,
                self.batch_size_threshold,
                self.max_workers
            )

            return mapper
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to build mapper: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": self.source_type.__name__,
                         "target_type": self.target_type.__name__},
                cause=e
            )

    def _validate_mapping_configuration(self) -> None:
        """验证映射配置

        检查映射配置是否有效，包括：
        1. 检查必需字段是否已映射
        2. 检查映射路径是否有效
        3. 检查类型兼容性

        Raises:
            Exception: 如果映射配置无效
        """
        # 检查源类型和目标类型
        if not self.source_type or not self.target_type:
            raise InfrastructureException(
                message="Source type and target type cannot be None",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": str(
                    self.source_type), "target_type": str(self.target_type)}
            )

        # 检查必需字段是否已映射
        self._validate_required_fields()

        # 检查映射路径是否有效
        self._validate_mapping_paths()

        # 检查类型兼容性
        self._validate_type_compatibility()

    def _validate_required_fields(self) -> None:
        """验证必需字段是否已映射

        检查目标类型的必需字段是否已通过显式映射或自动映射进行映射。

        Raises:
            Exception: 如果有必需字段未映射
        """
        # 获取目标类型的必需字段
        required_fields = self._get_required_fields(self.target_type)
        if not required_fields:
            return

        # 获取已映射的目标字段
        mapped_fields = set()

        # 添加显式映射的字段
        for _, target_path in self.property_mappings:
            mapped_fields.add(target_path.split('.')[0])

        # 添加自定义映射的字段
        for target_path, _ in self.custom_mappings:
            mapped_fields.add(target_path.split('.')[0])

        # 添加嵌套映射的字段
        for _, target_path, _ in self.nested_mappings:
            mapped_fields.add(target_path.split('.')[0])

        # 添加集合映射的字段
        for _, target_path, _ in self.collection_mappings:
            mapped_fields.add(target_path.split('.')[0])

        # 如果启用自动映射，添加可自动映射的字段
        if self.auto_mapping_enabled:
            source_fields = self._get_all_fields(self.source_type)
            target_fields = self._get_all_fields(self.target_type)

            for field in source_fields:
                if field in target_fields and field not in self.exclude_paths:
                    mapped_fields.add(field)

        # 检查是否有未映射的必需字段
        unmapped_required_fields = required_fields - mapped_fields
        if unmapped_required_fields:
            print('Mapper unmapped_fields:', unmapped_required_fields)
            raise InfrastructureException(
                message="Required fields are not mapped",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"unmapped_fields": list(unmapped_required_fields)}
            )

    def _validate_mapping_paths(self) -> None:
        """验证映射路径是否有效

        检查所有映射路径是否存在于源类型和目标类型中。

        Raises:
            Exception: 如果有无效的映射路径
        """
        source_fields = self._get_all_fields(self.source_type)
        target_fields = self._get_all_fields(self.target_type)

        # 验证属性映射路径
        for source_path, target_path in self.property_mappings:
            if not self._is_valid_path(source_path, source_fields):
                print('Mapper invalid mapping path (property):', locals())
                raise InfrastructureException(
                    message=f"Invalid source path: {source_path}",
                    code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                    details={"source_path": source_path,
                             "available_fields": list(source_fields)}
                )

            if not self._is_valid_path(target_path, target_fields):
                print('Mapper invalid mapping path (property):', locals())
                raise InfrastructureException(
                    message=f"Invalid target path: {target_path}",
                    code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                    details={"target_path": target_path,
                             "available_fields": list(target_fields)}
                )

        # 验证自定义映射路径
        for target_path, _ in self.custom_mappings:
            if not self._is_valid_path(target_path, target_fields):
                print('Mapper invalid mapping path (custom):', locals())
                raise InfrastructureException(
                    message=f"Invalid target path in custom mapping: {target_path}",
                    code=MapperExceptionCode.MAPPER_CUSTOM_CONFIG_INVALID,
                    details={"target_path": target_path,
                             "available_fields": list(target_fields)}
                )

        # 验证自定义反向映射路径
        for source_path, _ in self.reverse_mappings:
            if not self._is_valid_path(source_path, source_fields):
                raise InfrastructureException(
                    message=f"Invalid source path in reverse mapping: {source_path}",
                    code=MapperExceptionCode.MAPPER_REVERSE_CONFIG_INVALID,
                    details={"source_path": source_path,
                             "available_fields": list(source_fields)}
                )

        # 验证嵌套映射路径
        for source_path, target_path, _ in self.nested_mappings:
            if not self._is_valid_path(source_path, source_fields):
                print('Mapper invalid mapping path:', locals())
                raise InfrastructureException(
                    message=f"Invalid source path in nested mapping: {source_path}",
                    code=MapperExceptionCode.MAPPER_NESTED_CONFIG_INVALID,
                    details={"source_path": source_path,
                             "available_fields": list(source_fields)}
                )

            if not self._is_valid_path(target_path, target_fields):
                print('Mapper invalid mapping path:', locals())
                raise InfrastructureException(
                    message=f"Invalid target path in nested mapping: {target_path}",
                    code=MapperExceptionCode.MAPPER_NESTED_CONFIG_INVALID,
                    details={"target_path": target_path,
                             "available_fields": list(target_fields)}
                )

        # 验证集合映射路径
        for source_path, target_path, _ in self.collection_mappings:
            if not self._is_valid_path(source_path, source_fields):
                print('Mapper invalid mapping path:', locals())
                raise InfrastructureException(
                    message=f"Invalid source path in collection mapping: {source_path}",
                    code=MapperExceptionCode.MAPPER_COLLECTION_CONFIG_INVALID,
                    details={"source_path": source_path,
                             "available_fields": list(source_fields)}
                )

            if not self._is_valid_path(target_path, target_fields):
                print('Mapper invalid mapping path:', locals())
                raise InfrastructureException(
                    message=f"Invalid target path in collection mapping: {target_path}",
                    code=MapperExceptionCode.MAPPER_COLLECTION_CONFIG_INVALID,
                    details={"target_path": target_path,
                             "available_fields": list(target_fields)}
                )

    def _validate_type_compatibility(self) -> None:
        """验证类型兼容性

        检查映射的源类型和目标类型是否兼容。

        Raises:
            Exception: 如果有类型不兼容的映射
        """
        source_type_hints = self._get_type_hints(self.source_type)
        target_type_hints = self._get_type_hints(self.target_type)

        # 验证属性映射类型兼容性
        for source_path, target_path in self.property_mappings:
            source_type = self._get_path_type(source_path, source_type_hints)
            target_type = self._get_path_type(target_path, target_type_hints)

            if source_type and target_type and not self._is_type_compatible(source_type, target_type):
                # 检查是否可以通过类型转换器进行转换
                if not type_converter_registry.can_convert(source_type, target_type):
                    print('Mapper type mismatch:', {
                        "source_path": source_path,
                        "source_type": source_type,
                        "target_path": target_path,
                        "target_type": target_type
                    })
                    raise InfrastructureException(
                        message=f"Type mismatch in property mapping: {source_path} -> {target_path}",
                        code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                        details={
                            "source_path": source_path,
                            "source_type": str(source_type),
                            "target_path": target_path,
                            "target_type": str(target_type)
                        }
                    )

    def _get_required_fields(self, cls: Type) -> Set[str]:
        """获取类的必需字段

        Args:
            cls: 类型

        Returns:
            Set[str]: 必需字段集合
        """
        required_fields = set()
        try:
            signature = inspect.signature(cls.__init__)
            for name, param in signature.parameters.items():
                if name == 'self':
                    continue
                if param.kind == inspect.Parameter.VAR_KEYWORD:  # 跳过 **kwargs
                    continue
                if param.default is inspect.Parameter.empty:
                    required_fields.add(name)
        except (TypeError, ValueError):
            pass
        return required_fields

    def _get_all_fields(self, cls: Type) -> Set[str]:
        """获取类的所有字段

        Args:
            cls: 类型

        Returns:
            Set[str]: 所有字段集合
        """
        fields = set()

        # 获取类型注解（包括下划线字段）
        type_hints = self._get_type_hints(cls)
        for name in type_hints:
            fields.add(name)  # 不再过滤下划线

        # 获取属性
        for name in dir(cls):
            if not name.startswith('_') and name not in fields:
                attr = getattr(cls, name, None)
                if isinstance(attr, property):
                    fields.add(name)

        return fields

    def _get_type_hints(self, cls: Type) -> Dict[str, Type]:
        """获取类的类型注解

        Args:
            cls: 类型

        Returns:
            Dict[str, Type]: 类型注解字典
        """
        try:
            return get_type_hints(cls)
        except (TypeError, NameError):
            # 如果无法获取类型注解，则返回空字典
            return {}

    def _get_path_type(self, path: str, type_hints: Dict[str, Type]) -> Optional[Type]:
        """获取路径的类型

        Args:
            path: 属性路径
            type_hints: 类型注解字典

        Returns:
            Optional[Type]: 路径的类型
        """
        if not path or not type_hints:
            return None

        parts = path.split('.')
        current_type = None

        # 获取第一部分的类型
        if parts[0] in type_hints:
            current_type = type_hints[parts[0]]
        else:
            return None

        # 处理嵌套路径
        for i in range(1, len(parts)):
            # 处理Optional类型
            origin = getattr(current_type, '__origin__', None)
            if origin is Union:
                args = getattr(current_type, '__args__', ())
                if type(None) in args:
                    # 找到非None的类型
                    for arg in args:
                        if arg is not type(None):
                            current_type = arg
                            break

            # 获取嵌套类型的类型注解
            nested_type_hints = self._get_type_hints(current_type)
            if parts[i] in nested_type_hints:
                current_type = nested_type_hints[parts[i]]
            else:
                return None

        return current_type

    def _is_valid_path(self, path: str, fields: Set[str]) -> bool:
        """检查路径是否有效

        Args:
            path: 属性路径
            fields: 字段集合

        Returns:
            bool: 路径是否有效
        """
        if not path:
            return False

        # 简单路径直接检查
        if '.' not in path:
            return path in fields

        # 嵌套路径只检查第一部分
        first_part = path.split('.')[0]
        return first_part in fields

    def _is_type_compatible(self, source_type: Type, target_type: Type) -> bool:
        """检查类型是否兼容

        Args:
            source_type: 源类型
            target_type: 目标类型

        Returns:
            bool: 类型是否兼容
        """
        # 处理Optional类型
        source_origin = getattr(source_type, '__origin__', None)
        if source_origin is Union:
            source_args = getattr(source_type, '__args__', ())
            if type(None) in source_args:
                for arg in source_args:
                    if arg is not type(None):
                        source_type = arg
                        break

        target_origin = getattr(target_type, '__origin__', None)
        if target_origin is Union:
            target_args = getattr(target_type, '__args__', ())
            if type(None) in target_args:
                for arg in target_args:
                    if arg is not type(None):
                        target_type = arg
                        break

        # 处理 SQLAlchemy Mapped[T]
        if hasattr(target_type, '__origin__') and getattr(target_type, '__origin__', None).__name__ == 'Mapped':
            mapped_args = getattr(target_type, '__args__', ())
            if mapped_args:
                target_type = mapped_args[0]

        # 检查类型兼容性
        try:
            # 如果源类型是目标类型的子类，则兼容
            if issubclass(source_type, target_type):
                return True

            # 检查基本类型兼容性
            if source_type in (int, float) and target_type in (int, float):
                return True

            if source_type is str and target_type in (str, int, float, bool):
                return True

            if source_type is bool and target_type in (bool, int):
                return True

            # 检查集合类型兼容性
            source_origin = getattr(source_type, '__origin__', None)
            target_origin = getattr(target_type, '__origin__', None)

            if source_origin and target_origin:
                # 检查列表兼容性
                if source_origin in (list, List) and target_origin in (list, List):
                    source_args = getattr(source_type, '__args__', ())
                    target_args = getattr(target_type, '__args__', ())

                    if not source_args or not target_args:
                        return True

                    return self._is_type_compatible(source_args[0], target_args[0])

                # 检查字典兼容性
                if source_origin in (dict, Dict) and target_origin in (dict, Dict):
                    source_args = getattr(source_type, '__args__', ())
                    target_args = getattr(target_type, '__args__', ())

                    if not source_args or not target_args:
                        return True

                    return (self._is_type_compatible(source_args[0], target_args[0]) and
                            self._is_type_compatible(source_args[1], target_args[1]))

            return False
        except TypeError:
            # 如果类型检查失败，则假设不兼容
            return False


class BidirectionalMapperImpl(BidirectionalMapper[S, T], Generic[S, T]):
    """双向映射器实现

    支持源对象到目标对象的映射，以及目标对象到源对象的反向映射。
    """

    def __init__(
        self,
        source_type: Type[S],
        target_type: Type[T],
        to_target_strategy: MappingStrategy[S, T],
        to_source_strategy: MappingStrategy[T, S],
        preserve_domain_events: bool = True,
        batch_size_threshold: int = 100,
        max_workers: int = 10
    ):
        """初始化双向映射器

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            to_target_strategy: 源到目标的映射策略
            to_source_strategy: 目标到源的映射策略
            preserve_domain_events: 是否保留领域事件
            batch_size_threshold: 启用并行处理的批量大小阈值
            max_workers: 最大并行工作线程数
        """
        self.source_type = source_type
        self.target_type = target_type
        self.to_target_strategy = to_target_strategy
        self.to_source_strategy = to_source_strategy
        self.preserve_domain_events = preserve_domain_events
        self.batch_size_threshold = batch_size_threshold
        self.max_workers = max_workers

        # 创建正向和反向映射器
        self.to_target_mapper = GenericMapper(
            source_type, target_type, to_target_strategy)
        self.to_source_mapper = GenericMapper(
            target_type, source_type, to_source_strategy)

    def map(self, source: S) -> T:
        """将源对象映射到目标类型的新实例

        Args:
            source: 源对象

        Returns:
            T: 映射后的目标对象
        """
        if source is None:
            return None

        # 创建映射上下文
        context = MappingContext()
        return self.map_with_context(source, context)

    def map_with_context(self, source: S, context: MappingContext) -> T:
        """将源对象映射到目标类型的新实例，使用映射上下文

        Args:
            source: 源对象
            context: 映射上下文

        Returns:
            T: 映射后的目标对象
        """
        target = self.to_target_mapper.map_with_context(source, context)

        # 处理领域事件
        if self.preserve_domain_events:
            self._preserve_domain_events(source, target)

        return target

    def map_to_target(self, source: S, target: T) -> None:
        """将源对象映射到已存在的目标对象

        Args:
            source: 源对象
            target: 目标对象
        """
        if source is None or target is None:
            return

        # 创建映射上下文
        context = MappingContext()
        self.map_to_target_with_context(source, target, context)

    def map_to_target_with_context(self, source: S, target: T, context: MappingContext) -> None:
        """将源对象映射到已存在的目标对象，使用映射上下文

        Args:
            source: 源对象
            target: 目标对象
            context: 映射上下文
        """
        self.to_target_mapper.map_to_target_with_context(
            source, target, context)

        # 处理领域事件
        if self.preserve_domain_events:
            self._preserve_domain_events(source, target)

    def map_to_source(self, target: T) -> S:
        """将目标对象映射回源类型的新实例

        Args:
            target: 目标对象

        Returns:
            S: 映射后的源对象
        """
        if target is None:
            return None

        # 创建映射上下文
        context = MappingContext()
        return self.map_to_source_with_context(target, context)

    def map_to_source_with_context(self, target: T, context: MappingContext) -> S:
        """将目标对象映射回源类型的新实例，使用映射上下文

        Args:
            target: 目标对象
            context: 映射上下文

        Returns:
            S: 映射后的源对象
        """
        source = self.to_source_mapper.map_with_context(target, context)

        # 处理领域事件
        if self.preserve_domain_events:
            self._preserve_domain_events(target, source)

        return source

    def map_to_existing_source(self, target: T, source: S) -> None:
        """将目标对象映射到已存在的源对象

        Args:
            target: 目标对象
            source: 源对象
        """
        if target is None or source is None:
            return

        # 创建映射上下文
        context = MappingContext()
        self.map_to_existing_source_with_context(target, source, context)

    def map_to_existing_source_with_context(self, target: T, source: S, context: MappingContext) -> None:
        """将目标对象映射到已存在的源对象，使用映射上下文

        Args:
            target: 目标对象
            source: 源对象
            context: 映射上下文
        """
        self.to_source_mapper.map_to_target_with_context(
            target, source, context)

        # 处理领域事件
        if self.preserve_domain_events:
            self._preserve_domain_events(target, source)

    def map_list(self, source_list: List[S]) -> List[T]:
        """将源对象列表映射到目标类型的新实例列表

        Args:
            source_list: 源对象列表

        Returns:
            List[T]: 映射后的目标对象列表
        """
        if source_list is None:
            return None

        # 创建映射上下文
        context = MappingContext()
        return self.map_list_with_context(source_list, context)

    def map_list_with_context(self, source_list: List[S], context: MappingContext) -> List[T]:
        """将源对象列表映射到目标类型的新实例列表，使用映射上下文

        Args:
            source_list: 源对象列表
            context: 映射上下文

        Returns:
            List[T]: 映射后的目标对象列表
        """
        if source_list is None:
            return None

        # 小批量使用串行处理
        if len(source_list) < self.batch_size_threshold:
            result = []
            for source in source_list:
                target = self.map_with_context(source, context)
                result.append(target)
            return result

        # 大批量使用并行处理
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 为每个线程创建独立的映射上下文
                futures = []
                for source in source_list:
                    if source is not None:
                        # 创建新的上下文以避免线程安全问题
                        thread_context = MappingContext()
                        future = executor.submit(
                            self.map_with_context, source, thread_context)
                        futures.append(future)

                # 收集结果
                result = []
                for future in concurrent.futures.as_completed(futures):
                    target = future.result()
                    if target is not None:
                        result.append(target)

                return result
        except Exception as e:
            raise InfrastructureException(
                message=f"Batch mapping operation failed: {str(e)}",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"source_type": self.source_type.__name__,
                         "target_type": self.target_type.__name__, "batch_size": len(source_list)},
                cause=e
            )

    def map_to_source_list(self, target_list: List[T]) -> List[S]:
        """将目标对象列表映射回源类型的新实例列表

        Args:
            target_list: 目标对象列表

        Returns:
            List[S]: 映射后的源对象列表
        """
        if target_list is None:
            return None

        # 创建映射上下文
        context = MappingContext()
        return self.map_to_source_list_with_context(target_list, context)

    def map_to_source_list_with_context(self, target_list: List[T], context: MappingContext) -> List[S]:
        """将目标对象列表映射回源类型的新实例列表，使用映射上下文

        Args:
            target_list: 目标对象列表
            context: 映射上下文

        Returns:
            List[S]: 映射后的源对象列表
        """
        if target_list is None:
            return None

        # 小批量使用串行处理
        if len(target_list) < self.batch_size_threshold:
            result = []
            for target in target_list:
                source = self.map_to_source_with_context(target, context)
                result.append(source)
            return result

        # 大批量使用并行处理
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 为每个线程创建独立的映射上下文
                futures = []
                for target in target_list:
                    if target is not None:
                        # 创建新的上下文以避免线程安全问题
                        thread_context = MappingContext()
                        future = executor.submit(
                            self.map_to_source_with_context, target, thread_context)
                        futures.append(future)

                # 收集结果
                result = []
                for future in concurrent.futures.as_completed(futures):
                    source = future.result()
                    if source is not None:
                        result.append(source)

                return result
        except Exception as e:
            raise InfrastructureException(
                message=f"Batch reverse mapping operation failed: {str(e)}",
                code=MapperExceptionCode.MAPPER_BATCH_PROCESSING_FAILED,
                details={"target_type": self.target_type.__name__,
                         "source_type": self.source_type.__name__, "batch_size": len(target_list)},
                cause=e
            )

    def _preserve_domain_events(self, source: Any, target: Any) -> None:
        """保留领域事件

        如果源对象和目标对象都支持领域事件，则将源对象的领域事件复制到目标对象。

        Args:
            source: 源对象
            target: 目标对象
        """
        try:
            # 检查源对象和目标对象是否都支持领域事件
            if hasattr(source, 'domain_events') and hasattr(target, 'domain_events'):
                # 复制领域事件
                if hasattr(source.domain_events, 'copy'):
                    target.domain_events = source.domain_events.copy()
                else:
                    # 如果不支持copy方法，则尝试直接赋值
                    target.domain_events = source.domain_events
        except Exception as e:
            # 领域事件处理失败不应该中断映射过程，但应该记录错误
            logging.warning(f"Failed to preserve domain events: {str(e)}")
