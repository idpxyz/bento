"""异步处理器基类模块"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

import structlog
from structlog.types import BindableLogger
from structlog.types import Processor as StructlogProcessor

from ..models import BaseHandlerConfig

ConfigT = TypeVar('ConfigT', bound=BaseHandlerConfig)

class AsyncProcessor(ABC, Generic[ConfigT]):
    """异步处理器基类
    
    Args:
        config: 处理器配置对象
    """
    
    def __init__(self, config: ConfigT):
        self._config = config
        self._queue: Optional[asyncio.Queue] = None
        self._worker_task = None
        self._running = False
         
        # 设置日志级别
        import logging
        self.level = getattr(logging, config.level.upper())
        
        # 添加处理器名称和标准日志记录器
        self._name = self.__class__.__name__
        self._logger = logging.getLogger(__name__)

    @property
    def config(self) -> ConfigT:
        """获取处理器配置"""
        return self._config

    async def start(self) -> None:
        """启动异步处理器"""
        if not self._config.enabled or self._running:
            return
        
        try:
            await self.setup()
            self._queue = asyncio.Queue(maxsize=self._config.queue_size)
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
        except Exception as e:
            self._logger.error(f"Error starting processor: {e}")
            self._running = False

    async def stop(self, timeout: float = 5.0) -> None:
        """停止异步处理器，带超时机制
        
        Args:
            timeout: 等待队列清空的最大时间（秒）
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._queue:
            try:
                # 添加一个超时机制，避免永久等待
                # 使用asyncio.wait_for添加超时
                try:
                    # 创建一个任务来等待队列
                    await asyncio.wait_for(self._queue.join(), timeout)
                except asyncio.TimeoutError:
                    self._logger.warning(f"Queue processing timed out after {timeout}s")
            except Exception as e:
                self._logger.error(f"Error waiting for queue: {e}")
        
        if self._worker_task:
            try:
                self._worker_task.cancel()
                await asyncio.wait_for(asyncio.shield(self._worker_task), 1.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                self._logger.warning("Worker task cancellation timed out")
            except Exception as e:
                self._logger.error(f"Error cancelling worker task: {e}")
        
        try:
            await self.cleanup()
        except Exception as e:
            self._logger.error(f"Error cleaning up processor: {e}")

    async def _worker(self) -> None:
        """工作线程，处理队列中的日志事件"""
        while self._running:
            try:
                if not self._queue:
                    # 如果队列不存在，等待一下再重试
                    await asyncio.sleep(0.1)
                    continue
                    
                # 获取日志事件，超时处理
                try:
                    event = await asyncio.wait_for(self._queue.get(), 0.5)
                except asyncio.TimeoutError:
                    # 超时继续循环，检查running状态
                    continue
                
                try:
                    # 检查日志级别
                    logger, method_name, event_dict = event
                    import logging
                    if logging._nameToLevel.get(method_name.upper(), 0) >= self.level:
                        # 处理日志事件
                        await self.process_event_async(logger, method_name, event_dict)
                except Exception as e:
                    # 处理错误但不中断工作线程
                    self._logger.error(f"Error processing log event: {e}")
                finally:
                    if self._queue:  # 再次检查队列是否存在
                        self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Worker error: {e}")
                await asyncio.sleep(0.5)  # 避免过快重试

    def __call__(self, logger: structlog.types.BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """将日志事件放入队列"""
        if not self._config.enabled:
            return event_dict
            
        if self._queue and not self._queue.full() and self._running:
            try:
                # 使用 try_put 避免阻塞
                self._queue.put_nowait((logger, method_name, event_dict))
            except asyncio.QueueFull:
                self._logger.warning("Log queue is full, dropping message")
            except Exception as e:
                self._logger.error(f"Error putting event in queue: {e}")
        return event_dict

    @abstractmethod
    async def setup(self) -> None:
        """异步初始化处理器"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """异步清理处理器"""
        pass

    @abstractmethod
    async def process_event_async(self, logger: structlog.types.BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> None:
        """异步处理日志事件"""
        pass

    def get_renderer(self) -> Optional[StructlogProcessor]:
        """获取渲染器，如果有的话"""
        return None
