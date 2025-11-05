"""
指标记录基类实现
"""
import asyncio
import logging
import time
import traceback
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from ..core import (
    METRIC_DROPPED_METRICS,
    METRIC_METRICS_PROCESSING_DURATION,
    IMetricsRecorder,
    MetricMetadata,
    MetricType,
    StandardMetrics,
)

logger = logging.getLogger(__name__)

class BaseMetricsRecorder(IMetricsRecorder, ABC):
    """指标记录器基类"""

    def __init__(self, prefix: str = "", default_labels: Optional[Dict[str, str]] = None):
        """初始化记录器
        
        Args:
            prefix: 指标名称前缀
            default_labels: 默认标签
        """
        self.prefix = prefix
        self.default_labels = default_labels or {}
        self._metrics_cache: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._max_cache_size = 100  # 默认缓存大小
        self._flush_interval = 15.0  # 默认刷新间隔(秒)
        self._is_flushing = False
        self._dropped_metrics = 0
        
        # Initialize standard metrics registration in the initialize method instead
        self._standard_metrics_registered = False
    
    @abstractmethod
    async def _register_metric(self, metadata: MetricMetadata) -> None:
        """注册指标
        
        Args:
            metadata: 指标元信息
        """
        pass
    
    async def _register_standard_metrics(self) -> None:
        """注册所有标准指标"""
        if self._standard_metrics_registered:
            return
            
        for metric in StandardMetrics.get_all_metrics():
            try:
                await self._register_metric(metric)
            except Exception as e:
                logger.warning(f"Failed to register metric {metric.name}: {e}")
        
        self._standard_metrics_registered = True
    
    def _get_full_name(self, name: str) -> str:
        """获取带前缀的完整指标名称
        
        Args:
            name: 原始指标名称
            
        Returns:
            str: 带前缀的完整指标名称
        """
        if not self.prefix:
            return name
        return f"{self.prefix}_{name}"
    
    def _merge_labels(self, labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        """合并默认标签和自定义标签
        
        Args:
            labels: 自定义标签
            
        Returns:
            Dict[str, str]: 合并后的标签
        """
        if not labels:
            return self.default_labels.copy()
        
        result = self.default_labels.copy()
        result.update(labels)
        return result
    
    async def start_periodic_flush(self, interval: float = 15.0) -> None:
        """启动定期刷新任务
        
        Args:
            interval: 刷新间隔(秒)
        """
        self._flush_interval = interval
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def _periodic_flush(self) -> None:
        """定期刷新缓存的指标"""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
                await asyncio.sleep(1.0)  # 错误后短暂暂停
    
    @asynccontextmanager
    async def _measure_processing_time(self):
        """测量指标处理时间的上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            # 使用同步直接记录以避免递归调用
            try:
                await self._record_processing_duration(duration)
            except Exception as e:
                logger.debug(f"Failed to record metrics processing time: {e}")
    
    async def _record_processing_duration(self, duration: float) -> None:
        """记录指标处理时间
        
        Args:
            duration: 处理时间(秒)
        """
        # 将在子类中实现
        pass
    
    async def _record_dropped_metrics(self, count: int = 1) -> None:
        """记录丢弃的指标数量
        
        Args:
            count: 丢弃的数量
        """
        # 将在子类中实现
        pass
    
    def _add_to_cache(self, metric_data: Dict[str, Any]) -> bool:
        """添加指标数据到缓存
        
        Args:
            metric_data: 指标数据
            
        Returns:
            bool: 是否添加成功
        """
        if len(self._metrics_cache) >= self._max_cache_size:
            self._dropped_metrics += 1
            return False
        
        self._metrics_cache.append(metric_data)
        return True
    
    async def flush(self) -> None:
        """刷新缓存的指标"""
        if not self._metrics_cache or self._is_flushing:
            return
        
        async with self._lock:
            if not self._metrics_cache or self._is_flushing:
                return
            
            self._is_flushing = True
            try:
                metrics_to_flush = self._metrics_cache.copy()
                self._metrics_cache.clear()
                
                if self._dropped_metrics > 0:
                    await self._record_dropped_metrics(self._dropped_metrics)
                    self._dropped_metrics = 0
                
                await self._flush_metrics(metrics_to_flush)
            except Exception as e:
                logger.error(f"Error flushing metrics: {e}")
                # 失败时将指标放回缓存
                self._metrics_cache.extend(metrics_to_flush)
            finally:
                self._is_flushing = False
    
    @abstractmethod
    async def _flush_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """刷新指标到后端存储
        
        Args:
            metrics: 指标数据列表
        """
        pass
    
    async def increment_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """增加计数器值
        
        Args:
            name: 指标名称
            value: 增加的值，默认为1.0
            labels: 标签字典，默认为None
        """
        async with self._measure_processing_time():
            metric_data = {
                "name": name,
                "type": MetricType.COUNTER,
                "value": value,
                "labels": self._merge_labels(labels)
            }
            
            if not self._add_to_cache(metric_data):
                # 如果缓存已满，尝试立即刷新
                await self.flush()
                if not self._add_to_cache(metric_data):
                    await self._record_dropped_metrics()
    
    async def observe_histogram(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """观察直方图值
        
        Args:
            name: 指标名称
            value: 观察到的值
            labels: 标签字典，默认为None
        """
        async with self._measure_processing_time():
            metric_data = {
                "name": name,
                "type": MetricType.HISTOGRAM,
                "value": value,
                "labels": self._merge_labels(labels)
            }
            
            if not self._add_to_cache(metric_data):
                # 如果缓存已满，尝试立即刷新
                await self.flush()
                if not self._add_to_cache(metric_data):
                    await self._record_dropped_metrics()
    
    async def set_gauge(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """设置仪表盘值
        
        Args:
            name: 指标名称
            value: 设置的值
            labels: 标签字典，默认为None
        """
        async with self._measure_processing_time():
            metric_data = {
                "name": name,
                "type": MetricType.GAUGE,
                "value": value,
                "labels": self._merge_labels(labels)
            }
            
            if not self._add_to_cache(metric_data):
                # 如果缓存已满，尝试立即刷新
                await self.flush()
                if not self._add_to_cache(metric_data):
                    await self._record_dropped_metrics()
    
    async def batch_record(
        self,
        metrics: List[Dict[str, Any]]
    ) -> None:
        """批量记录多个指标
        
        Args:
            metrics: 指标列表，每个指标为包含name, type, value, labels的字典
        """
        async with self._measure_processing_time():
            for metric in metrics:
                if "labels" in metric:
                    metric["labels"] = self._merge_labels(metric["labels"])
                else:
                    metric["labels"] = self.default_labels.copy()
                
                if not self._add_to_cache(metric):
                    await self._record_dropped_metrics()
            
            # 如果缓存超过一半容量，尝试立即刷新
            if len(self._metrics_cache) > self._max_cache_size / 2:
                await self.flush()
    
    async def health_check(self) -> bool:
        """健康检查
        
        Returns:
            bool: 健康状态
        """
        try:
            # 如果有过多丢弃的指标，健康状态为False
            if self._dropped_metrics > StandardMetrics.DROPPED_METRICS.alert_threshold:
                return False
            
            # 如果缓存过多，健康状态为False
            if len(self._metrics_cache) >= self._max_cache_size:
                return False
            
            # 执行具体实现的健康检查
            return await self._check_health()
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    @abstractmethod
    async def _check_health(self) -> bool:
        """实际健康检查逻辑
        
        Returns:
            bool: 健康状态
        """
        pass 