"""映射策略模块。

提供不同的映射策略实现，包括自动映射、显式映射、自定义映射等。

Key Components:
- PropertyMapping: 属性映射配置
- CustomMapping: 自定义映射配置
- NestedMapping: 嵌套对象映射配置
- CollectionMapping: 集合映射配置
- MappingStrategy: 映射策略基类
- AutoMappingStrategy: 自动映射策略
- ExplicitMappingStrategy: 显式映射策略
- CompositeMappingStrategy: 组合映射策略
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.mapper import MapperExceptionCode

from .context import MappingContext
from .converter import type_converter_registry
from .interfaces import Mapper

# 类型变量
S = TypeVar('S')  # 源类型
T = TypeVar('T')  # 目标类型


@dataclass
class PropertyMapping:
    """属性映射配置"""
    source_path: str
    target_path: str


@dataclass
class CustomMapping:
    """自定义映射配置"""
    target_path: str
    mapping_func: Callable[[Any], Any]


@dataclass
class NestedMapping:
    """嵌套对象映射配置"""
    source_path: str
    target_path: str
    mapper: Mapper


@dataclass
class CollectionMapping:
    """集合映射配置"""
    source_path: str
    target_path: str
    mapper: Mapper


class MappingStrategy(Generic[S, T], ABC):
    """映射策略基类

    定义映射策略的基本接口。
    """

    @abstractmethod
    def apply(self, source: S, target_type: Type[T]) -> T:
        """应用映射策略，将源对象映射到目标类型的新实例

        Args:
            source: 源对象
            target_type: 目标类型

        Returns:
            T: 映射后的目标对象
        """
        pass

    @abstractmethod
    def apply_to_existing(self, source: S, target: T) -> None:
        """应用映射策略，将源对象映射到已存在的目标对象

        Args:
            source: 源对象
            target: 目标对象
        """
        pass

    def apply_with_context(self, source: S, target: T, context: MappingContext) -> None:
        """应用映射策略，将源对象映射到已存在的目标对象，使用映射上下文

        Args:
            source: 源对象
            target: 目标对象
            context: 映射上下文
        """
        # 默认实现调用不带上下文的方法
        self.apply_to_existing(source, target)


class AutoMappingStrategy(MappingStrategy[S, T], Generic[S, T]):
    """自动映射策略

    基于属性名称自动映射源对象到目标对象。
    """

    def __init__(self, source_type: Type[S], target_type: Type[T], exclude_paths: Optional[List[str]] = None):
        """初始化自动映射策略

        Args:
            source_type: 源对象类型
            target_type: 目标对象类型
            exclude_paths: 排除自动映射的属性路径列表
        """
        self.source_type = source_type
        self.target_type = target_type
        self.exclude_paths = exclude_paths or []
        self.property_mappings = self._discover_mappable_properties()

    def _discover_mappable_properties(self) -> Dict[str, str]:
        """发现可映射的属性

        基于属性名称匹配发现可映射的属性。

        Returns:
            Dict[str, str]: 源属性路径到目标属性路径的映射
        """
        mappings = {}

        # 获取源类型和目标类型的所有属性
        source_attrs = self._get_all_attributes(self.source_type)
        target_attrs = self._get_all_attributes(self.target_type)

        # 查找名称匹配的属性
        for source_path, _ in source_attrs.items():
            # 如果属性路径在排除列表中，则跳过
            if source_path in self.exclude_paths:
                continue

            # 如果目标类型有同名属性，则添加映射
            if source_path in target_attrs:
                mappings[source_path] = source_path

        return mappings

    def _get_all_attributes(self, cls: Type) -> Dict[str, Type]:
        """获取类的所有属性

        Args:
            cls: 类型

        Returns:
            Dict[str, Type]: 属性路径到属性类型的映射
        """
        attrs = {}

        # 获取类型注解
        type_hints = get_type_hints(cls)
        for name, type_hint in type_hints.items():
            if not name.startswith('_'):
                attrs[name] = type_hint

        # 获取属性
        for name in dir(cls):
            if not name.startswith('_') and name not in attrs:
                attr = getattr(cls, name, None)
                if isinstance(attr, property):
                    attrs[name] = Any

        return attrs

    def _get_nested_attr(self, obj: Any, path: str) -> Any:
        """获取嵌套属性值

        Args:
            obj: 对象
            path: 属性路径，支持点号分隔的嵌套路径

        Returns:
            Any: 属性值

        Raises:
            Exception: 如果属性不存在
        """
        if not path:
            return obj

        parts = path.split('.')
        current = obj

        for part in parts:
            if current is None:
                return None

            try:
                current = getattr(current, part)
            except AttributeError:
                try:
                    # 尝试使用字典访问
                    current = current[part]
                except (TypeError, KeyError):
                    # 属性不存在，返回None
                    return None

        return current

    def _set_nested_attr(self, obj: Any, path: str, value: Any) -> None:
        """设置嵌套属性值

        Args:
            obj: 对象
            path: 属性路径，支持点号分隔的嵌套路径
            value: 属性值

        Raises:
            Exception: 如果属性不存在或无法设置
        """
        if not path:
            return

        parts = path.split('.')
        current = obj

        # 遍历除最后一部分外的所有部分
        for i, part in enumerate(parts[:-1]):
            try:
                next_obj = getattr(current, part)
                if next_obj is None:
                    # 如果嵌套对象为空，尝试创建新实例
                    # 获取属性类型
                    attr_type = None
                    try:
                        attr_type = type(getattr(type(current), part))
                    except AttributeError:
                        pass

                    if attr_type:
                        try:
                            next_obj = attr_type()
                            setattr(current, part, next_obj)
                        except Exception:
                            pass

                    if next_obj is None:
                        # 如果无法创建实例，则使用空字典
                        next_obj = {}
                        setattr(current, part, next_obj)

                current = next_obj
            except AttributeError:
                try:
                    # 尝试使用字典访问
                    next_obj = current[part]
                    if next_obj is None:
                        # 如果嵌套对象为空，使用空字典
                        next_obj = {}
                        current[part] = next_obj

                    current = next_obj
                except (TypeError, KeyError):
                    # 如果无法设置，则跳过
                    return

        # 设置最后一部分
        last_part = parts[-1]
        try:
            # 尝试获取属性类型
            attr_type = None
            try:
                attr_type = type(getattr(type(current), last_part))
            except AttributeError:
                pass

            # 如果有类型信息且值类型不匹配，尝试转换
            if attr_type and value is not None and not isinstance(value, attr_type):
                try:
                    # 使用类型转换器进行转换
                    value = type_converter_registry.convert(value, attr_type)
                except Exception:
                    # 如果转换失败，则跳过
                    return

            setattr(current, last_part, value)
        except AttributeError:
            try:
                # 尝试使用字典访问
                current[last_part] = value
            except (TypeError, KeyError):
                # 如果无法设置，则跳过
                return

    def apply(self, source: S, target_type: Type[T]) -> T:
        """应用自动映射策略，将源对象映射到目标类型的新实例

        Args:
            source: 源对象
            target_type: 目标类型

        Returns:
            T: 映射后的目标对象
        """
        if source is None:
            return None

        try:
            # 创建目标实例
            target = target_type()

            # 应用映射
            self.apply_to_existing(source, target)

            return target
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply auto mapping: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": target_type.__name__},
                cause=e
            )

    def apply_to_existing(self, source: S, target: T) -> None:
        """应用自动映射策略，将源对象映射到已存在的目标对象

        Args:
            source: 源对象
            target: 目标对象
        """
        if source is None or target is None:
            return

        try:
            # 应用所有属性映射
            for source_path, target_path in self.property_mappings.items():
                source_value = self._get_nested_attr(source, source_path)
                if source_value is not None:
                    self._set_nested_attr(target, target_path, source_value)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply auto mapping to existing target: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": type(target).__name__},
                cause=e
            )

    def apply_with_context(self, source: S, target: T, context: MappingContext) -> None:
        """应用自动映射策略，将源对象映射到已存在的目标对象，使用映射上下文

        Args:
            source: 源对象
            target: 目标对象
            context: 映射上下文
        """
        # 自动映射不需要使用上下文，直接调用不带上下文的方法
        self.apply_to_existing(source, target)


class ExplicitMappingStrategy(MappingStrategy[S, T], Generic[S, T]):
    """显式映射策略

    基于显式配置的映射策略。
    """

    def __init__(self):
        """初始化显式映射策略"""
        self.property_mappings: List[PropertyMapping] = []
        self.custom_mappings: List[CustomMapping] = []
        self.nested_mappings: List[NestedMapping] = []
        self.collection_mappings: List[CollectionMapping] = []

    def add_property_mapping(self, source_path: str, target_path: str) -> None:
        """添加属性映射

        Args:
            source_path: 源对象属性路径
            target_path: 目标对象属性路径
        """
        self.property_mappings.append(
            PropertyMapping(source_path, target_path))

    def add_custom_mapping(self, target_path: str, mapping_func: Callable[[Any], Any]) -> None:
        """添加自定义映射

        Args:
            target_path: 目标对象属性路径
            mapping_func: 映射函数，接收源对象作为参数，返回映射后的值
        """
        self.custom_mappings.append(CustomMapping(target_path, mapping_func))

    def add_nested_mapping(self, source_path: str, target_path: str, mapper: Mapper) -> None:
        """添加嵌套对象映射

        Args:
            source_path: 源对象中嵌套对象的属性路径
            target_path: 目标对象中嵌套对象的属性路径
            mapper: 用于映射嵌套对象的映射器
        """
        self.nested_mappings.append(
            NestedMapping(source_path, target_path, mapper))

    def add_collection_mapping(self, source_path: str, target_path: str, mapper: Mapper) -> None:
        """添加集合映射

        Args:
            source_path: 源对象中集合的属性路径
            target_path: 目标对象中集合的属性路径
            mapper: 用于映射集合中元素的映射器
        """
        self.collection_mappings.append(
            CollectionMapping(source_path, target_path, mapper))

    def _get_nested_attr(self, obj: Any, path: str) -> Any:
        """获取嵌套属性值

        Args:
            obj: 对象
            path: 属性路径，支持点号分隔的嵌套路径

        Returns:
            Any: 属性值

        Raises:
            Exception: 如果属性不存在
        """
        if not path:
            return obj

        parts = path.split('.')
        current = obj

        for part in parts:
            if current is None:
                return None

            try:
                current = getattr(current, part)
            except AttributeError:
                try:
                    # 尝试使用字典访问
                    current = current[part]
                except (TypeError, KeyError):
                    raise InfrastructureException(
                        message=f"Property not found: {path}",
                        code=MapperExceptionCode.MAPPER_PROPERTY_NOT_FOUND,
                        details={"object_type": type(
                            obj).__name__, "property_path": path}
                    )

        return current

    def _set_nested_attr(self, obj: Any, path: str, value: Any) -> None:
        """设置嵌套属性值

        Args:
            obj: 对象
            path: 属性路径，支持点号分隔的嵌套路径
            value: 属性值

        Raises:
            Exception: 如果属性不存在或无法设置
        """
        if not path:
            return

        parts = path.split('.')
        current = obj

        # 遍历除最后一部分外的所有部分
        for i, part in enumerate(parts[:-1]):
            try:
                next_obj = getattr(current, part)
                if next_obj is None:
                    # 如果嵌套对象为空，尝试创建新实例
                    # 获取属性类型
                    attr_type = None
                    try:
                        attr_type = type(getattr(type(current), part))
                    except AttributeError:
                        pass

                    if attr_type:
                        try:
                            next_obj = attr_type()
                            setattr(current, part, next_obj)
                        except Exception:
                            pass

                    if next_obj is None:
                        # 如果无法创建实例，则使用空字典
                        next_obj = {}
                        setattr(current, part, next_obj)

                current = next_obj
            except AttributeError:
                try:
                    # 尝试使用字典访问
                    next_obj = current[part]
                    if next_obj is None:
                        # 如果嵌套对象为空，使用空字典
                        next_obj = {}
                        current[part] = next_obj

                    current = next_obj
                except (TypeError, KeyError):
                    raise InfrastructureException(
                        message=f"Cannot set nested property: {path}",
                        code=MapperExceptionCode.MAPPER_PROPERTY_NOT_FOUND,
                        details={"object_type": type(
                            obj).__name__, "property_path": path}
                    )

        # 设置最后一部分
        last_part = parts[-1]
        try:
            # 尝试获取属性类型
            attr_type = None
            try:
                attr_type = type(getattr(type(current), last_part))
            except AttributeError:
                pass

            # 如果有类型信息且值类型不匹配，尝试转换
            if attr_type and value is not None and not isinstance(value, attr_type):
                try:
                    # 使用类型转换器进行转换
                    value = type_converter_registry.convert(value, attr_type)
                except Exception as e:
                    raise InfrastructureException(
                        message=f"Type conversion failed: {type(value).__name__} to {attr_type.__name__}",
                        code=MapperExceptionCode.MAPPER_TYPE_CONVERSION_FAILED,
                        details={"source_type": type(
                            value).__name__, "target_type": attr_type.__name__, "value": str(value)},
                        cause=e
                    )

            setattr(current, last_part, value)
        except AttributeError:
            try:
                # 尝试使用字典访问
                current[last_part] = value
            except (TypeError, KeyError):
                raise InfrastructureException(
                    message=f"Cannot set property: {path}",
                    code=MapperExceptionCode.MAPPER_PROPERTY_NOT_FOUND,
                    details={"object_type": type(
                        obj).__name__, "property_path": path}
                )

    def apply(self, source: S, target_type: Type[T]) -> T:
        """应用映射策略，将源对象映射到目标类型的新实例

        Args:
            source: 源对象
            target_type: 目标类型

        Returns:
            T: 映射后的目标对象
        """
        if source is None:
            return None

        try:
            # 创建目标实例
            target = target_type()

            # 应用映射
            self.apply_to_existing(source, target)

            return target
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply mapping: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": target_type.__name__},
                cause=e
            )

    def apply_to_existing(self, source: S, target: T) -> None:
        """应用映射策略，将源对象映射到已存在的目标对象

        Args:
            source: 源对象
            target: 目标对象
        """
        if source is None or target is None:
            return

        try:
            # 应用属性映射
            for mapping in self.property_mappings:
                source_value = self._get_nested_attr(
                    source, mapping.source_path)
                self._set_nested_attr(
                    target, mapping.target_path, source_value)

            # 应用自定义映射
            for mapping in self.custom_mappings:
                try:
                    mapped_value = mapping.mapping_func(source)
                    self._set_nested_attr(
                        target, mapping.target_path, mapped_value)
                except Exception as e:
                    raise InfrastructureException(
                        message=f"Custom mapping function failed for {mapping.target_path}: {str(e)}",
                        code=MapperExceptionCode.MAPPER_CUSTOM_CONFIG_INVALID,
                        details={"target_path": mapping.target_path},
                        cause=e
                    )

            # 应用嵌套对象映射
            for mapping in self.nested_mappings:
                source_value = self._get_nested_attr(
                    source, mapping.source_path)
                if source_value is not None:
                    try:
                        mapped_value = mapping.mapper.map_to_target(
                            source_value)
                        self._set_nested_attr(
                            target, mapping.target_path, mapped_value)
                    except Exception as e:
                        raise InfrastructureException(
                            message=f"Nested mapping failed for {mapping.source_path} -> {mapping.target_path}: {str(e)}",
                            code=MapperExceptionCode.MAPPER_NESTED_CONFIG_INVALID,
                            details={"source_path": mapping.source_path,
                                     "target_path": mapping.target_path},
                            cause=e
                        )

            # 应用集合映射
            for mapping in self.collection_mappings:
                source_collection = self._get_nested_attr(
                    source, mapping.source_path)
                if source_collection is not None:
                    try:
                        # 映射集合中的每个元素
                        mapped_collection = mapping.mapper.map_to_targets(
                            source_collection)
                        self._set_nested_attr(
                            target, mapping.target_path, mapped_collection)
                    except Exception as e:
                        raise InfrastructureException(
                            message=f"Collection mapping failed for {mapping.source_path} -> {mapping.target_path}: {str(e)}",
                            code=MapperExceptionCode.MAPPER_COLLECTION_CONFIG_INVALID,
                            details={"source_path": mapping.source_path,
                                     "target_path": mapping.target_path},
                            cause=e
                        )
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply mapping to existing target: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": type(target).__name__},
                cause=e
            )

    def apply_with_context(self, source: S, target: T, context: MappingContext) -> None:
        """应用映射策略，将源对象映射到已存在的目标对象，使用映射上下文

        Args:
            source: 源对象
            target: 目标对象
            context: 映射上下文
        """
        if source is None or target is None:
            return

        try:
            # 应用属性映射
            for mapping in self.property_mappings:
                source_value = self._get_nested_attr(
                    source, mapping.source_path)
                self._set_nested_attr(
                    target, mapping.target_path, source_value)

            # 应用自定义映射
            for mapping in self.custom_mappings:
                try:
                    mapped_value = mapping.mapping_func(source)
                    self._set_nested_attr(
                        target, mapping.target_path, mapped_value)
                except Exception as e:
                    raise InfrastructureException(
                        message=f"Custom mapping function failed for {mapping.target_path}: {str(e)}",
                        code=MapperExceptionCode.MAPPER_CUSTOM_CONFIG_INVALID,
                        details={"target_path": mapping.target_path},
                        cause=e
                    )

            # 应用嵌套对象映射
            for mapping in self.nested_mappings:
                source_value = self._get_nested_attr(
                    source, mapping.source_path)
                if source_value is not None:
                    try:
                        # 使用上下文进行嵌套映射，防止循环引用
                        mapped_value = mapping.mapper.map_to_target(
                            source_value, context)
                        self._set_nested_attr(
                            target, mapping.target_path, mapped_value)
                    except Exception as e:
                        raise InfrastructureException(
                            message=f"Nested mapping failed for {mapping.source_path} -> {mapping.target_path}: {str(e)}",
                            code=MapperExceptionCode.MAPPER_NESTED_CONFIG_INVALID,
                            details={"source_path": mapping.source_path,
                                     "target_path": mapping.target_path},
                            cause=e
                        )

            # 应用集合映射
            for mapping in self.collection_mappings:
                source_collection = self._get_nested_attr(
                    source, mapping.source_path)
                if source_collection is not None:
                    try:
                        # 映射集合中的每个元素，使用上下文
                        mapped_collection = []
                        for item in source_collection:
                            if item is not None:
                                mapped_item = mapping.mapper.map_to_target(
                                    item, context)
                                if mapped_item is not None:
                                    mapped_collection.append(mapped_item)

                        self._set_nested_attr(
                            target, mapping.target_path, mapped_collection)
                    except Exception as e:
                        raise InfrastructureException(
                            message=f"Collection mapping failed for {mapping.source_path} -> {mapping.target_path}: {str(e)}",
                            code=MapperExceptionCode.MAPPER_COLLECTION_CONFIG_INVALID,
                            details={"source_path": mapping.source_path,
                                     "target_path": mapping.target_path},
                            cause=e
                        )
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply mapping to existing target: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": type(target).__name__},
                cause=e
            )


class CompositeMappingStrategy(MappingStrategy[S, T], Generic[S, T]):
    """组合映射策略

    组合多个映射策略，按顺序应用。
    """

    def __init__(self, strategies: List[MappingStrategy[S, T]]):
        """初始化组合映射策略

        Args:
            strategies: 映射策略列表，按顺序应用
        """
        if not strategies:
            raise InfrastructureException(
                message="Strategies list cannot be empty",
                code=MapperExceptionCode.MAPPER_CONFIG_INVALID,
                details={"strategies": str(strategies)}
            )

        self.strategies = strategies

    def apply(self, source: S, target_type: Type[T]) -> T:
        """应用组合映射策略，将源对象映射到目标类型的新实例

        按顺序应用所有策略。

        Args:
            source: 源对象
            target_type: 目标类型

        Returns:
            T: 映射后的目标对象
        """
        if source is None:
            return None

        try:
            # 创建目标实例
            target = target_type()

            # 应用所有策略
            self.apply_to_existing(source, target)

            return target
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply composite mapping: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": target_type.__name__},
                cause=e
            )

    def apply_to_existing(self, source: S, target: T) -> None:
        """应用组合映射策略，将源对象映射到已存在的目标对象

        按顺序应用所有策略。

        Args:
            source: 源对象
            target: 目标对象
        """
        if source is None or target is None:
            return

        try:
            # 按顺序应用所有策略
            for strategy in self.strategies:
                strategy.apply_to_existing(source, target)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply composite mapping to existing target: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": type(target).__name__},
                cause=e
            )

    def apply_with_context(self, source: S, target: T, context: MappingContext) -> None:
        """应用组合映射策略，将源对象映射到已存在的目标对象，使用映射上下文

        按顺序应用所有策略。

        Args:
            source: 源对象
            target: 目标对象
            context: 映射上下文
        """
        if source is None or target is None:
            return

        try:
            # 按顺序应用所有策略
            for strategy in self.strategies:
                if hasattr(strategy, 'apply_with_context'):
                    strategy.apply_with_context(source, target, context)
                else:
                    # 兼容旧版本策略
                    strategy.apply_to_existing(source, target)
        except Exception as e:
            raise InfrastructureException(
                message=f"Failed to apply composite mapping to existing target: {str(e)}",
                code=MapperExceptionCode.MAPPER_TYPE_MISMATCH,
                details={"source_type": type(
                    source).__name__, "target_type": type(target).__name__},
                cause=e
            )
