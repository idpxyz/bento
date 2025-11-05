from typing import Type, Dict, Any, Optional, List
import json
import uuid
from datetime import datetime

from idp.framework.domain.event.base import DomainEvent
from idp.framework.infrastructure.messaging import MessageEvent
from idp.framework.infrastructure.mapper import MapperBuilder, Mapper
from idp.framework.infrastructure.mapper.core.context import MappingContext

# 自定义JSON编码器，处理datetime对象
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class DomainEventMessageMapper:
    """
    领域事件和消息事件之间的映射器
    
    负责将领域事件转换为消息事件，以及将消息事件转换回领域事件。
    这个映射器确保了领域层和基础设施层之间的数据转换一致性。
    
    注意：虽然项目推荐使用MapperBuilder框架，但在这个特定场景中，直接实现映射逻辑更加合适，原因如下：
    1. 领域事件和消息事件之间的映射比较特殊，涉及到一些自定义逻辑和特殊处理
    2. MapperBuilder在验证映射配置时要求所有必需字段都被映射，但在这个场景中，
       我们需要更灵活的映射方式，例如动态获取事件类型和负载
    3. 领域事件的结构可能各不相同，难以用通用的映射规则处理
    4. 需要处理一些特殊情况，如datetime序列化和额外属性设置
    
    在更简单、更标准化的对象映射场景中，MapperBuilder仍然是一个很好的选择。
    """
    
    # 缓存已创建的映射器
    _domain_to_message_mappers: Dict[Type[DomainEvent], Mapper] = {}
    _message_to_domain_mappers: Dict[Type[DomainEvent], Mapper] = {}
    
    @classmethod
    def _create_domain_to_message_mapper(cls, domain_event_class: Type[DomainEvent]) -> Mapper:
        """
        创建领域事件到消息事件的映射器
        
        Args:
            domain_event_class: 领域事件类
            
        Returns:
            Mapper: 领域事件到消息事件的映射器
        """
        # 创建自定义映射函数
        def map_event_id(event: DomainEvent) -> str:
            return getattr(event, "event_id", str(uuid.uuid4()))
            
        def map_event_type(event: DomainEvent) -> str:
            return event.event_type
            
        def map_aggregate_id(event: DomainEvent) -> Optional[str]:
            return getattr(event, "aggregate_id", None)
            
        def map_timestamp(event: DomainEvent) -> datetime:
            return getattr(event, "timestamp", datetime.now())
            
        def map_payload(event: DomainEvent) -> Dict[str, Any]:
            return event.payload
            
        def map_metadata(event: DomainEvent) -> Dict[str, Any]:
            return getattr(event, "metadata", {})
        
        # 使用MapperBuilder创建映射器
        mapper = (MapperBuilder.for_types(domain_event_class, MessageEvent)
            .map_custom("event_id", map_event_id)
            .map_custom("event_type", map_event_type)
            .map_custom("aggregate_id", map_aggregate_id)
            .map_custom("timestamp", map_timestamp)
            .map_custom("payload", map_payload)
            .map_custom("metadata", map_metadata)
            .build())
            
        return mapper
    
    @classmethod
    def _create_message_to_domain_mapper(cls, event_class: Type[DomainEvent]) -> Mapper:
        """
        创建消息事件到领域事件的映射器
        
        Args:
            event_class: 领域事件类
            
        Returns:
            Mapper: 消息事件到领域事件的映射器
        """
        # 创建自定义映射函数
        def create_domain_event(message: MessageEvent) -> DomainEvent:
            # 提取领域事件所需的数据
            payload = message.payload
            
            # 创建领域事件实例
            # 尝试使用from_payload方法创建，如果不存在则使用构造函数
            if hasattr(event_class, 'from_payload') and callable(getattr(event_class, 'from_payload')):
                domain_event = event_class.from_payload(payload)
            else:
                # 从payload中提取构造函数所需的参数
                # 这里假设payload中的字段与构造函数参数匹配
                domain_event = event_class(**payload)
            
            # 设置额外属性
            if hasattr(domain_event, "event_id"):
                domain_event._event_id = message.event_id
            
            if hasattr(domain_event, "metadata"):
                domain_event._metadata = message.metadata
            
            if hasattr(domain_event, "timestamp") and hasattr(message, "timestamp"):
                domain_event._timestamp = message.timestamp
                
            return domain_event
        
        # 使用MapperBuilder创建映射器
        # 由于领域事件的创建比较特殊，我们使用一个自定义映射函数来创建整个领域事件
        mapper = (MapperBuilder.for_types(MessageEvent, event_class)
            .map_custom("", create_domain_event)  # 空字符串表示映射到整个对象
            .build())
            
        return mapper
    
    @classmethod
    def _get_domain_to_message_mapper(cls, domain_event_class: Type[DomainEvent]) -> Mapper:
        """
        获取领域事件到消息事件的映射器
        
        Args:
            domain_event_class: 领域事件类
            
        Returns:
            Mapper: 领域事件到消息事件的映射器
        """
        if domain_event_class not in cls._domain_to_message_mappers:
            cls._domain_to_message_mappers[domain_event_class] = cls._create_domain_to_message_mapper(domain_event_class)
        return cls._domain_to_message_mappers[domain_event_class]
    
    @classmethod
    def _get_message_to_domain_mapper(cls, event_class: Type[DomainEvent]) -> Mapper:
        """
        获取消息事件到领域事件的映射器
        
        Args:
            event_class: 领域事件类
            
        Returns:
            Mapper: 消息事件到领域事件的映射器
        """
        if event_class not in cls._message_to_domain_mappers:
            cls._message_to_domain_mappers[event_class] = cls._create_message_to_domain_mapper(event_class)
        return cls._message_to_domain_mappers[event_class]
    
    @staticmethod
    def to_message_event(domain_event: DomainEvent) -> MessageEvent:
        """
        将领域事件转换为消息事件
        
        Args:
            domain_event: 领域事件
            
        Returns:
            对应的消息事件
        """
        # 获取事件ID，如果没有则生成新的
        event_id = getattr(domain_event, "event_id", str(uuid.uuid4()))
        
        # 获取聚合根ID
        aggregate_id = getattr(domain_event, "aggregate_id", None)
        
        # 获取事件类型
        event_type = domain_event.event_type
        
        # 获取事件负载
        payload = domain_event.payload
        
        # 获取元数据
        metadata = getattr(domain_event, "metadata", {})
        
        # 获取时间戳
        timestamp = getattr(domain_event, "timestamp", datetime.now())
        
        # 创建消息事件
        return MessageEvent(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            timestamp=timestamp,
            payload=payload,
            metadata=metadata
        )
    
    @staticmethod
    def to_domain_event(message_event: MessageEvent, event_class: Type[DomainEvent]) -> DomainEvent:
        """
        将消息事件转换为领域事件
        
        Args:
            message_event: 消息事件
            event_class: 领域事件类
            
        Returns:
            对应的领域事件
        """
        # 提取领域事件所需的数据
        payload = message_event.payload
        metadata = message_event.metadata
        
        # 创建领域事件实例
        # 尝试使用from_payload方法创建，如果不存在则使用构造函数
        if hasattr(event_class, 'from_payload') and callable(getattr(event_class, 'from_payload')):
            domain_event = event_class.from_payload(payload)
        else:
            # 从payload中提取构造函数所需的参数
            # 这里假设payload中的字段与构造函数参数匹配
            domain_event = event_class(**payload)
        
        # 设置额外属性
        if hasattr(domain_event, "event_id"):
            domain_event._event_id = message_event.event_id
        
        if hasattr(domain_event, "metadata") and metadata:
            domain_event._metadata = metadata
        
        if hasattr(domain_event, "timestamp") and hasattr(message_event, "timestamp"):
            domain_event._timestamp = message_event.timestamp
        
        return domain_event
    
    @staticmethod
    def to_domain_events(message_events: List[MessageEvent], event_class: Type[DomainEvent]) -> List[DomainEvent]:
        """
        将多个消息事件转换为领域事件
        
        Args:
            message_events: 消息事件列表
            event_class: 领域事件类
            
        Returns:
            领域事件列表
        """
        return [DomainEventMessageMapper.to_domain_event(msg, event_class) for msg in message_events]
    
    @staticmethod
    def to_message_events(domain_events: List[DomainEvent]) -> List[MessageEvent]:
        """
        将多个领域事件转换为消息事件
        
        Args:
            domain_events: 领域事件列表
            
        Returns:
            消息事件列表
        """
        return [DomainEventMessageMapper.to_message_event(event) for event in domain_events]
    
    @classmethod
    def register_event_mapper(cls, event_class: Type[DomainEvent], 
                              to_message_mapper: Optional[Mapper] = None,
                              to_domain_mapper: Optional[Mapper] = None) -> None:
        """
        注册自定义映射器
        
        Args:
            event_class: 领域事件类
            to_message_mapper: 领域事件到消息事件的映射器
            to_domain_mapper: 消息事件到领域事件的映射器
        """
        if to_message_mapper:
            cls._domain_to_message_mappers[event_class] = to_message_mapper
        
        if to_domain_mapper:
            cls._message_to_domain_mappers[event_class] = to_domain_mapper 