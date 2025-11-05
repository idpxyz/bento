from enum import Enum
from typing import Any, AsyncContextManager, Dict, Optional, Protocol


class SpanKind(str, Enum):
    """Span类型枚举"""
    INTERNAL = "internal"  # 内部操作
    SERVER = "server"      # 服务端处理
    CLIENT = "client"      # 客户端调用
    PRODUCER = "producer"  # 消息生产者
    CONSUMER = "consumer"  # 消息消费者

class Span(Protocol):
    """Span接口"""
    @property
    def trace_id(self) -> str:
        """获取trace_id"""
        ...
    
    @property
    def span_id(self) -> str:
        """获取span_id"""
        ...
    
    def set_attribute(self, key: str, value: Any) -> None:
        """设置Span属性"""
        ...
    
    def record_exception(self, exception: Exception) -> None:
        """记录异常"""
        ...

class IMetricsRecorder(Protocol):
    """指标记录器接口"""
    async def increment_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        增加计数器值
        
        Args:
            name: 指标名称
            value: 增加的值，默认为1.0
            labels: 标签字典，默认为None
        """
        ...
    
    async def observe_histogram(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        观察直方图值
        
        Args:
            name: 指标名称
            value: 观察到的值
            labels: 标签字典，默认为None
        """
        ...
    
    async def set_gauge(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        设置仪表盘值
        
        Args:
            name: 指标名称
            value: 设置的值
            labels: 标签字典，默认为None
        """
        ...
    
    async def batch_record(
        self,
        metrics: list[dict]
    ) -> None:
        """
        批量记录多个指标
        
        Args:
            metrics: 指标列表，每个指标为包含name, type, value, labels的字典
        """
        ...
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 健康状态
        """
        ...

class ITracer(Protocol):
    """链路追踪接口"""
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, str]] = None
    ) -> AsyncContextManager[Span]:
        """
        开始一个新的Span
        
        Args:
            name: Span名称
            kind: Span类型，默认为INTERNAL
            attributes: Span属性字典，默认为None
            
        Returns:
            AsyncContextManager[Span]: Span上下文管理器
        """
        ...
    
    def inject_context(
        self,
        carrier: Dict[str, str]
    ) -> None:
        """
        将当前的追踪上下文注入到载体中
        
        Args:
            carrier: 要注入的载体，例如HTTP请求头
        """
        ...
    
    def extract_context(
        self,
        carrier: Dict[str, str]
    ) -> None:
        """
        从载体中提取追踪上下文
        
        Args:
            carrier: 包含追踪信息的载体，例如HTTP请求头
        """
        ...
    
    def get_current_span(self) -> Optional[Span]:
        """
        获取当前活动的Span
        
        Returns:
            Optional[Span]: 当前活动的Span，如果不存在则返回None
        """
        ... 