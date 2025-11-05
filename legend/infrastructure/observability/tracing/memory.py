"""
内存追踪器实现
用于开发和测试环境
"""
import asyncio
import json
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

from ..core import Span, SpanKind
from .tracer import BaseSpan, BaseTracer

logger = logging.getLogger(__name__)

class MemorySpan(BaseSpan):
    """内存Span实现"""
    
    def _export(self) -> None:
        """导出Span到内存
        这个方法在内存追踪器中不需要实际实现，
        因为Span已经在内存中，只需要在父类中结束
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "duration": self.duration,
            "attributes": self.attributes,
            "events": self._events,
            "status": self._status,
            "status_message": self._status_message
        }
    
    def __str__(self) -> str:
        """字符串表示
        
        Returns:
            str: 字符串表示
        """
        duration = f"{self.duration*1000:.2f}ms" if self.duration is not None else "unfinished"
        result = f"Span[{self.name}] trace={self.trace_id[:8]}... span={self.span_id[:8]}... duration={duration}"
        
        if self.parent_span_id:
            result += f" parent={self.parent_span_id[:8]}..."
        
        if self._status != "OK":
            result += f" status={self._status}"
        
        attributes = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        if attributes:
            result += f" attrs=[{attributes}]"
        
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串
        
        Returns:
            str: JSON字符串
        """
        return json.dumps(self.to_dict(), default=str)

class MemoryTracer(BaseTracer):
    """内存追踪器实现"""
    
    def __init__(self, service_name: str, sample_rate: float = 1.0, max_spans: int = 1000):
        """初始化内存追踪器
        
        Args:
            service_name: 服务名称
            sample_rate: 采样率(0.0-1.0)
            max_spans: 最大保存的span数量
        """
        super().__init__(service_name, sample_rate)
        self._spans: deque = deque(maxlen=max_spans)
        self._extracted_context: Optional[Dict[str, str]] = None
    
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
        # 如果有提取的上下文，并且没有指定trace_id，则使用提取的上下文
        if self._extracted_context and not trace_id:
            trace_id = self._extracted_context.get("trace_id")
            parent_span_id = self._extracted_context.get("parent_span_id")
            # 使用后清除
            self._extracted_context = None
        
        return MemorySpan(name, trace_id, parent_span_id)
    
    async def _end_span(self, span: MemorySpan) -> None:
        """结束并处理Span
        
        Args:
            span: 要结束的Span
        """
        span.end()
        
        # 添加到内存中
        self._spans.append(span)
        
        # 记录日志
        duration_ms = span.duration * 1000 if span.duration is not None else 0
        logger.debug(f"Span {span.name} completed in {duration_ms:.2f}ms [trace={span.trace_id[:8]}...]")
    
    def get_spans(self) -> List[MemorySpan]:
        """获取所有记录的Span
        
        Returns:
            List[MemorySpan]: Span列表
        """
        return list(self._spans)
    
    def get_trace(self, trace_id: str) -> List[MemorySpan]:
        """获取指定追踪的所有Span
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            List[MemorySpan]: 同一追踪的Span列表
        """
        return [span for span in self._spans if span.trace_id == trace_id]
    
    def clear(self) -> None:
        """清空所有记录的Span"""
        self._spans.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取追踪统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self._spans:
            return {
                "total_spans": 0,
                "total_traces": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0
            }
        
        # 只统计已完成的span
        completed_spans = [span for span in self._spans if span.duration is not None]
        if not completed_spans:
            return {
                "total_spans": len(self._spans),
                "total_traces": len(set(span.trace_id for span in self._spans)),
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
                "completed_spans": 0,
                "error_spans": len([span for span in self._spans if span._status == "ERROR"])
            }
        
        durations = [span.duration * 1000 for span in completed_spans]
        
        return {
            "total_spans": len(self._spans),
            "total_traces": len(set(span.trace_id for span in self._spans)),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "completed_spans": len(completed_spans),
            "error_spans": len([span for span in self._spans if span._status == "ERROR"])
        } 