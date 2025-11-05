"""领域事件基础模块。

定义了领域事件的基础类和相关工具，用于表示领域中发生的事实。
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar('T', bound='DomainEvent')


class DomainEvent(ABC):
    """领域事件基类

    领域事件表示在领域模型中发生的事实。
    它们是不可变的，并且包含事件发生时的完整上下文。

    特性:
    1. 唯一标识(字符串类型)
    2. 时间戳(统一使用UTC时区)
       - 确保事件的全局有序性
       - 便于跨时区/跨系统的事件处理
       - 避免夏令时等时区转换问题
    3. 事件版本
    4. 事件元数据
    5. 不可变性
    """

    # 是否已冻结（不可变）
    _frozen: bool = False

    # 事件属性
    _aggregate_id: Optional[str] = None
    _event_id: str
    _timestamp: datetime
    _version: int
    _metadata: Dict[str, Any]

    @classmethod
    def _generate_id(cls) -> str:
        """Generate a new event ID."""
        return str(uuid4())

    def __init__(
        self,
        aggregate_id: Optional[str] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        version: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """初始化领域事件

        Args:
            aggregate_id: 聚合根ID，可选
            event_id: 事件ID，如果不提供则自动生成
            timestamp: 事件时间戳，如果不提供则使用当前时间
            version: 事件版本号，默认为1
            metadata: 事件元数据，可选
        """
        # 设置事件属性
        self._aggregate_id = aggregate_id
        self._event_id = event_id if event_id else self._generate_id()

        # 确保时间戳使用UTC时区
        if timestamp is None:
            self._timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None:
            # 如果没有时区信息，假定为UTC
            self._timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            # 如果有时区信息，转换为UTC
            self._timestamp = timestamp.astimezone(timezone.utc)

        self._version = version
        self._metadata = metadata or {}

        # 设置为不可变
        self._frozen = True

    @property
    def aggregate_id(self) -> Optional[str]:
        """获取聚合根ID

        Returns:
            聚合根ID，如果没有则返回None
        """
        return self._aggregate_id

    @property
    def event_id(self) -> str:
        """获取事件ID

        Returns:
            事件ID
        """
        return self._event_id

    @property
    def timestamp(self) -> datetime:
        """获取事件时间戳

        Returns:
            事件时间戳（UTC时区）
        """
        return self._timestamp

    @property
    def version(self) -> int:
        """获取事件版本号

        Returns:
            事件版本号
        """
        return self._version

    @property
    def metadata(self) -> Dict[str, Any]:
        """获取事件元数据

        Returns:
            事件元数据的副本
        """
        return self._metadata.copy()

    @property
    def event_type(self) -> str:
        """获取事件类型

        Returns:
            事件类型名称
        """
        return self.__class__.__name__

    def __setattr__(self, name, value):
        """重写属性设置方法，实现不可变性

        Args:
            name: 属性名
            value: 属性值

        Raises:
            AttributeError: 如果对象已冻结且尝试修改非内部属性
        """
        if self._frozen and not name.startswith('_'):
            raise AttributeError(
                f"Cannot modify immutable event: {self.event_type}")
        super().__setattr__(name, value)

    def with_aggregate_id(self, aggregate_id: str) -> 'DomainEvent':
        """创建一个带有新聚合根ID的事件副本

        Args:
            aggregate_id: 新的聚合根ID

        Returns:
            新的事件实例
        """
        # 创建新实例
        return self.__class__(
            aggregate_id=aggregate_id,
            event_id=self._event_id,
            timestamp=self._timestamp,
            version=self._version,
            metadata=self._metadata.copy()
        )

    def with_metadata(self, key: str, value: Any) -> 'DomainEvent':
        """创建一个带有新元数据的事件副本

        Args:
            key: 元数据键
            value: 元数据值

        Returns:
            新的事件实例
        """
        # 复制元数据并添加新值
        metadata = self._metadata.copy()
        metadata[key] = value

        # 创建新实例
        return self.__class__(
            aggregate_id=self._aggregate_id,
            event_id=self._event_id,
            timestamp=self._timestamp,
            version=self._version,
            metadata=metadata
        )

    def with_version(self, version: int) -> 'DomainEvent':
        """创建一个带有新版本号的事件副本

        Args:
            version: 新的版本号

        Returns:
            新的事件实例
        """
        # 创建新实例
        return self.__class__(
            aggregate_id=self._aggregate_id,
            event_id=self._event_id,
            timestamp=self._timestamp,
            version=version,
            metadata=self._metadata.copy()
        )

    def to_dict(self) -> Dict[str, Any]:
        """将事件转换为字典

        Returns:
            包含事件所有属性的字典
        """
        # 基本属性
        result = {
            "event_type": self.event_type,
            "event_id": self._event_id,
            "timestamp": self._timestamp.isoformat(),
            "version": self._version,
            "metadata": self._metadata
        }

        # 添加聚合根ID（如果有）
        if self._aggregate_id is not None:
            result["aggregate_id"] = self._aggregate_id

        # 添加事件特定的负载
        result["payload"] = self.get_payload()

        return result

    @abstractmethod
    def get_payload(self) -> Dict[str, Any]:
        """获取事件负载

        此方法必须由子类实现，返回事件特定的数据。

        Returns:
            事件负载字典
        """
        pass

    def __eq__(self, other):
        """比较两个事件是否相等

        Args:
            other: 另一个事件

        Returns:
            如果事件ID相同则返回True
        """
        if not isinstance(other, DomainEvent):
            return False
        return self._event_id == other.event_id


class EventMetadata(BaseModel):
    """事件元数据模型

    用于标准化事件元数据的结构
    """
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    source: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    custom_data: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            元数据字典
        """
        result = self.model_dump(exclude_none=True)
        return result


class EventSerializer:
    """事件序列化器

    提供领域事件的序列化和反序列化功能
    """

    @staticmethod
    def serialize(event: DomainEvent) -> Dict[str, Any]:
        """序列化领域事件为字典

        Args:
            event: 要序列化的领域事件

        Returns:
            序列化后的字典
        """
        return event.to_dict()

    @staticmethod
    def deserialize(data: Dict[str, Any], event_types: Dict[str, Type[DomainEvent]]) -> DomainEvent:
        """反序列化字典为领域事件

        Args:
            data: 序列化的事件数据
            event_types: 事件类型映射表，键为事件类型名称，值为事件类

        Returns:
            反序列化后的领域事件

        Raises:
            ValueError: 如果事件类型未注册或数据格式无效
        """
        # 验证基本字段
        if "event_type" not in data:
            raise ValueError("Missing event_type in event data")

        event_type_name = data["event_type"]

        # 查找事件类
        if event_type_name not in event_types:
            raise ValueError(f"Unknown event type: {event_type_name}")

        event_class = event_types[event_type_name]

        # 提取基本属性
        try:
            event_id = data.get("event_id")
            timestamp_str = data.get("timestamp")
            timestamp = datetime.fromisoformat(
                timestamp_str) if timestamp_str else None
            version = data.get("version", 1)
            metadata = data.get("metadata", {})
            aggregate_id = data.get("aggregate_id")
            payload = data.get("payload", {})

            # 创建事件实例
            if hasattr(event_class, "from_dict"):
                # 如果事件类提供了自定义的反序列化方法
                return event_class.from_dict(data)
            else:
                # 使用默认方式创建实例
                # 注意：这要求事件类的__init__方法接受payload中的所有字段作为关键字参数
                return event_class(
                    aggregate_id=aggregate_id,
                    event_id=event_id,
                    timestamp=timestamp,
                    version=version,
                    metadata=metadata,
                    **payload
                )

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid event data: {str(e)}")


class EventStore(Generic[T]):
    """事件存储接口

    定义了事件持久化的抽象接口
    """

    @abstractmethod
    async def append(self, event: T) -> None:
        """添加事件到存储

        Args:
            event: 要存储的事件

        Raises:
            Exception: 如果存储失败
        """
        pass

    @abstractmethod
    async def append_batch(self, events: List[T]) -> None:
        """批量添加事件到存储

        Args:
            events: 要存储的事件列表

        Raises:
            Exception: 如果存储失败
        """
        pass

    @abstractmethod
    async def get_by_id(self, event_id: str) -> Optional[T]:
        """根据ID获取事件

        Args:
            event_id: 事件ID

        Returns:
            找到的事件，如果不存在则返回None

        Raises:
            Exception: 如果查询失败
        """
        pass

    @abstractmethod
    async def get_by_aggregate_id(self, aggregate_id: str) -> List[T]:
        """获取聚合根的所有事件

        Args:
            aggregate_id: 聚合根ID

        Returns:
            事件列表，按时间戳排序

        Raises:
            Exception: 如果查询失败
        """
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """获取所有事件

        Returns:
            所有事件的列表，按时间戳排序

        Raises:
            Exception: 如果查询失败
        """
        pass
