"""类型转换器模块。

提供类型转换功能，用于在映射过程中处理不同类型之间的转换。

Key Components:
- TypeConverter: 类型转换器接口
- TypeConverterRegistry: 类型转换器注册表，用于管理和查找类型转换器
"""

import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.mapper import MapperExceptionCode

# 类型变量
S = TypeVar('S')  # 源类型
T = TypeVar('T')  # 目标类型


class TypeConverter(ABC):
    """类型转换器接口

    定义类型转换器的基本接口。
    """

    @abstractmethod
    def can_convert(self, source_type: Type, target_type: Type) -> bool:
        """检查是否可以将源类型转换为目标类型

        Args:
            source_type: 源类型
            target_type: 目标类型

        Returns:
            bool: 如果可以转换，则返回True，否则返回False
        """
        pass

    @abstractmethod
    def convert(self, value: Any, target_type: Type) -> Any:
        """将值转换为目标类型

        Args:
            value: 要转换的值
            target_type: 目标类型

        Returns:
            Any: 转换后的值

        Raises:
            Exception: 如果转换失败
        """
        pass


def extract_python_type(typ: Type) -> Type:
    """递归剥离 SQLAlchemy Mapped[T]、InstrumentedAttribute 等包装类型，返回实际 Python 类型"""
    # 处理 SQLAlchemy Mapped[T]
    origin = getattr(typ, '__origin__', None)
    if origin and origin.__name__ == 'Mapped':
        args = getattr(typ, '__args__', ())
        if args:
            return extract_python_type(args[0])
    # 处理 InstrumentedAttribute（只要不是基础类型且有 .property 属性）
    if hasattr(typ, '__name__') and typ.__name__ == 'InstrumentedAttribute':
        return object  # 或直接返回 object，表示跳过类型检查
    return typ


class TypeConverterRegistry:
    """类型转换器注册表

    管理和查找类型转换器。
    """

    _converters: Dict[Tuple[Type, Type], Callable[[Any], Any]] = {}
    _instance = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(TypeConverterRegistry, cls).__new__(cls)
            cls._instance._initialize_default_converters()
        return cls._instance

    def _initialize_default_converters(self):
        """初始化默认转换器"""
        # 字符串转换
        self.register_converter(str, int, lambda s: int(s))
        self.register_converter(str, float, lambda s: float(s))
        self.register_converter(
            str, bool, lambda s: s.lower() in ('true', 'yes', '1', 'y'))
        self.register_converter(str, Decimal, lambda s: Decimal(s))
        self.register_converter(str, uuid.UUID, lambda s: uuid.UUID(s))
        self.register_converter(
            str, datetime, lambda s: datetime.fromisoformat(s))
        self.register_converter(str, date, lambda s: date.fromisoformat(s))

        # 数值转换
        self.register_converter(int, str, lambda i: str(i))
        self.register_converter(int, float, lambda i: float(i))
        self.register_converter(int, bool, lambda i: bool(i))
        self.register_converter(int, Decimal, lambda i: Decimal(i))

        self.register_converter(float, str, lambda f: str(f))
        self.register_converter(float, int, lambda f: int(f))
        self.register_converter(float, Decimal, lambda f: Decimal(str(f)))

        self.register_converter(Decimal, str, lambda d: str(d))
        self.register_converter(Decimal, float, lambda d: float(d))
        self.register_converter(Decimal, int, lambda d: int(d))

        # 布尔值转换
        self.register_converter(bool, str, lambda b: str(b))
        self.register_converter(bool, int, lambda b: 1 if b else 0)

        # UUID转换
        self.register_converter(uuid.UUID, str, lambda u: str(u))

        # 日期时间转换
        self.register_converter(datetime, str, lambda dt: dt.isoformat())
        self.register_converter(datetime, date, lambda dt: dt.date())
        self.register_converter(datetime, int, lambda dt: int(dt.timestamp()))

        self.register_converter(date, str, lambda d: d.isoformat())
        self.register_converter(
            date, datetime, lambda d: datetime.combine(d, time()))

        # 枚举转换
        self.register_converter(Enum, str, lambda e: e.name)
        self.register_converter(Enum, int, lambda e: e.value if isinstance(
            e.value, int) else int(e.value))

    def register_converter(self, source_type: Type, target_type: Type, converter_func: Callable[[Any], Any]) -> None:
        """注册类型转换器

        Args:
            source_type: 源类型
            target_type: 目标类型
            converter_func: 转换函数，接收源类型的值，返回目标类型的值
        """
        self._converters[(source_type, target_type)] = converter_func

    def can_convert(self, source_type: Type, target_type: Type) -> bool:
        """检查是否可以将源类型转换为目标类型

        Args:
            source_type: 源类型
            target_type: 目标类型

        Returns:
            bool: 如果可以转换，则返回True，否则返回False
        """
        # 处理None类型
        if source_type is None or target_type is None:
            return False

        # 相同类型可以直接转换
        if source_type == target_type:
            return True

        # 处理typing类型
        if hasattr(source_type, "__origin__") or hasattr(target_type, "__origin__"):
            # 对于typing类型，只检查是否有直接的转换器
            return (source_type, target_type) in self._converters

        # 检查继承关系
        try:
            if issubclass(source_type, target_type):
                return True
        except TypeError:
            # 如果类型不是类，忽略错误
            pass

        # 检查是否有直接的转换器
        if (source_type, target_type) in self._converters:
            return True

        # 检查枚举类型
        try:
            if issubclass(source_type, Enum) and (
                (Enum, target_type) in self._converters or
                target_type in (str, int)
            ):
                return True
        except TypeError:
            # 如果类型不是类，忽略错误
            pass

        # 检查Optional类型
        target_origin = get_origin(target_type)
        if target_origin is Union:
            target_args = get_args(target_type)
            # 如果是Optional[T]，则检查是否可以转换为T
            if len(target_args) == 2 and type(None) in target_args:
                actual_target_type = target_args[0] if target_args[1] is type(
                    None) else target_args[1]
                return self.can_convert(source_type, actual_target_type)

        return False

    def convert(self, value: Any, target_type: Type) -> Any:
        """将值转换为目标类型

        Args:
            value: 要转换的值
            target_type: 目标类型

        Returns:
            Any: 转换后的值

        Raises:
            Exception: 如果转换失败
        """
        if value is None:
            return None

        source_type = type(value)
        target_type = extract_python_type(target_type)

        # 处理 NoneType 目标类型
        if target_type is type(None):
            return None if value in (None, '', 'null') else value

        if isinstance(value, target_type):
            return value

        # 处理Optional类型
        target_origin = get_origin(target_type)
        if target_origin is Union:
            target_args = get_args(target_type)
            # 如果是Optional[T]，则尝试转换为T
            if len(target_args) == 2 and type(None) in target_args:
                actual_target_type = target_args[0] if target_args[1] is type(
                    None) else target_args[1]
                return self.convert(value, actual_target_type)

        # 处理枚举类型
        if issubclass(source_type, Enum):
            if target_type is str:
                return value.name
            elif target_type is int and isinstance(value.value, int):
                return value.value
            elif (Enum, target_type) in self._converters:
                return self._converters[(Enum, target_type)](value)

        # 查找直接转换器
        if (source_type, target_type) in self._converters:
            try:
                return self._converters[(source_type, target_type)](value)
            except Exception as e:
                raise InfrastructureException(
                    message=f"Type conversion failed: {source_type.__name__} to {target_type.__name__}",
                    code=MapperExceptionCode.MAPPER_TYPE_CONVERSION_FAILED,
                    details={"source_type": source_type.__name__,
                             "target_type": target_type.__name__, "value": str(value)},
                    cause=e
                )

        # 如果目标类型是源类型的父类，则可以直接转换
        if issubclass(source_type, target_type):
            return value

        # 没有找到合适的转换器
        print('Type conversion failed:', {
            'value': value,
            'value_type': type(value),
            'target_type': target_type
        })
        raise InfrastructureException(
            message=f"No converter registered for {source_type.__name__} to {target_type.__name__}",
            code=MapperExceptionCode.MAPPER_TYPE_CONVERSION_FAILED,
            details={"source_type": source_type.__name__,
                     "target_type": target_type.__name__, "value": str(value)}
        )


# 全局类型转换器注册表实例
type_converter_registry = TypeConverterRegistry()
