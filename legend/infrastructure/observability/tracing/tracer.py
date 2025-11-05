"""
链路追踪基类实现
"""
import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, Dict, Optional

from ..core import (
    REQUEST_ID_HEADER_NAME,
    SPAN_HEADER_NAME,
    TRACE_HEADER_NAME,
    ITracer,
    Span,
    SpanKind,
)

logger = logging.getLogger(__name__)

class BaseSpan(ABC):
    """基础Span实现"""
    
    def __init__(self, name: str, trace_id: str = None, parent_span_id: str = None):
        """初始化Span
        
        Args:
            name: Span名称
            trace_id: 追踪ID，如果为None则生成新的
            parent_span_id: 父Span ID，如果为None则为根Span
        """
        self._name = name
        self._trace_id = trace_id or str(uuid.uuid4())
        self._span_id = str(uuid.uuid4())
        self._parent_span_id = parent_span_id
        self._start_time = asyncio.get_event_loop().time()
        self._end_time: Optional[float] = None
        self._attributes: Dict[str, Any] = {}
        self._events: list = []
        self._status = "OK"
        self._status_message = ""
    
    @property
    def name(self) -> str:
        """获取Span名称"""
        return self._name
    
    @property
    def trace_id(self) -> str:
        """获取trace_id"""
        return self._trace_id
    
    @property
    def span_id(self) -> str:
        """获取span_id"""
        return self._span_id
    
    @property
    def parent_span_id(self) -> Optional[str]:
        """获取parent_span_id"""
        return self._parent_span_id
    
    @property
    def duration(self) -> Optional[float]:
        """获取持续时间(秒)"""
        if self._end_time is None:
            return None
        return self._end_time - self._start_time
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """获取属性字典"""
        return self._attributes.copy()
    
    def set_attribute(self, key: str, value: Any) -> None:
        """设置Span属性
        
        Args:
            key: 属性名
            value: 属性值
        """
        self._attributes[key] = value
    
    def record_exception(self, exception: Exception) -> None:
        """记录异常
        
        Args:
            exception: 异常对象
        """
        self._status = "ERROR"
        self._status_message = str(exception)
        self._events.append({
            "name": "exception",
            "timestamp": asyncio.get_event_loop().time(),
            "attributes": {
                "exception.type": exception.__class__.__name__,
                "exception.message": str(exception)
            }
        })
    
    def end(self) -> None:
        """结束Span"""
        if self._end_time is None:
            self._end_time = asyncio.get_event_loop().time()
    
    @abstractmethod
    def _export(self) -> None:
        """导出Span到后端"""
        pass

class BaseTracer(ITracer, ABC):
    """追踪器基类"""
    
    def __init__(self, service_name: str, sample_rate: float = 1.0):
        """初始化追踪器
        
        Args:
            service_name: 服务名称
            sample_rate: 采样率(0.0-1.0)
        """
        self.service_name = service_name
        self.sample_rate = max(0.0, min(1.0, sample_rate))  # 确保在0.0-1.0之间
        self._current_span_stack: list = []
    
    @property
    def current_span(self) -> Optional[Span]:
        """获取当前活动的Span"""
        if not self._current_span_stack:
            return None
        return self._current_span_stack[-1]
    
    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, str]] = None
    ) -> AsyncContextManager[Span]:
        """开始一个新的Span
        
        Args:
            name: Span名称
            kind: Span类型，默认为INTERNAL
            attributes: Span属性字典，默认为None
            
        Returns:
            AsyncContextManager[Span]: Span上下文管理器
        """
        # 确定是否应该采样
        should_sample = await self._should_sample()
        if not should_sample:
            # 返回一个空的上下文管理器
            try:
                yield None
            finally:
                pass
            return
        
        parent_span = self.get_current_span()
        parent_span_id = parent_span.span_id if parent_span else None
        trace_id = parent_span.trace_id if parent_span else None
        
        span = await self._create_span(name, kind, trace_id, parent_span_id)
        
        # 添加基本属性
        span.set_attribute("service.name", self.service_name)
        span.set_attribute("span.kind", kind.value)
        
        # 添加自定义属性
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        # 推入当前Span栈
        self._current_span_stack.append(span)
        
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            # 从Span栈中移除
            if self._current_span_stack and self._current_span_stack[-1] == span:
                self._current_span_stack.pop()
            
            # 结束并导出Span
            await self._end_span(span)
    
    def inject_context(
        self,
        carrier: Dict[str, str]
    ) -> None:
        """将当前的追踪上下文注入到载体中
        
        Args:
            carrier: 要注入的载体，例如HTTP请求头
        """
        span = self.get_current_span()
        if span:
            carrier[TRACE_HEADER_NAME] = span.trace_id
            carrier[SPAN_HEADER_NAME] = span.span_id
            # 如果有请求ID，也一并注入
            request_id = span.attributes.get("request.id")
            if request_id:
                carrier[REQUEST_ID_HEADER_NAME] = request_id
    
    def extract_context(
        self,
        carrier: Dict[str, str]
    ) -> None:
        """从载体中提取追踪上下文
        
        Args:
            carrier: 包含追踪信息的载体，例如HTTP请求头
        """
        trace_id = carrier.get(TRACE_HEADER_NAME)
        span_id = carrier.get(SPAN_HEADER_NAME)
        
        if trace_id:
            # 存储提取的上下文，供下一个span使用
            self._extracted_context = {
                "trace_id": trace_id,
                "parent_span_id": span_id
            }
        else:
            self._extracted_context = None
    
    def get_current_span(self) -> Optional[Span]:
        """获取当前活动的Span
        
        Returns:
            Optional[Span]: 当前活动的Span，如果不存在则返回None
        """
        if not self._current_span_stack:
            return None
        return self._current_span_stack[-1]
    
    async def _should_sample(self) -> bool:
        """确定是否应该采样
        
        Returns:
            bool: 是否应该采样
        """
        if self.sample_rate >= 1.0:
            return True
        if self.sample_rate <= 0.0:
            return False
        
        import random
        return random.random() < self.sample_rate
    
    @abstractmethod
    async def _create_span(
        self, 
        name: str, 
        kind: SpanKind,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> Span:
        """创建新的Span
        
        Args:
            name: Span名称
            kind: Span类型
            trace_id: 追踪ID，如果为None则创建新的
            parent_span_id: 父Span ID，如果为None则为根Span
            
        Returns:
            Span: 创建的Span
        """
        pass
    
    @abstractmethod
    async def _end_span(self, span: Span) -> None:
        """结束并处理Span
        
        Args:
            span: 要结束的Span
        """
        pass 