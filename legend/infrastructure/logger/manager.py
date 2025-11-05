"""Logger manager module.

This module contains the main Logger class and global logger_manager instance.
It's separated to prevent circular imports.
"""

import uuid
from typing import Dict, List, Optional

import structlog
from structlog.types import Processor

from .processors import AsyncProcessor
from .processors.console import ConsoleProcessor


class Logger:
    """日志管理器"""

    def __init__(self):
        self._processors: List[AsyncProcessor] = []
        self._loggers: Dict[str, structlog.BoundLogger] = {}
        self._configured = False
        self._started = False

    def add_processor(self, processor: AsyncProcessor) -> None:
        """添加日志处理器"""
        self._processors.append(processor)
        self._configured = False  # 重置配置状态

    async def start(self) -> None:
        """启动所有异步处理器"""
        if self._started:
            return

        for processor in self._processors:
            await processor.start()

        self._started = True

    async def stop(self) -> None:
        """停止所有异步处理器"""
        if not self._started:
            return

        for processor in self._processors:
            await processor.stop()

        self._started = False

    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        """获取日志记录器"""
        if not self._configured:
            self._configure_structlog()

        if name in self._loggers:
            return self._loggers[name]

        logger = structlog.get_logger(name)
        self._loggers[name or ""] = logger
        return logger

    def _configure_structlog(self) -> None:
        """配置structlog"""
        # 基础处理器
        processors: List[Processor] = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

        # 添加自定义处理器
        processors.extend(self._processors)

        # 查找控制台处理器的渲染器
        console_renderer = None
        for processor in self._processors:
            if isinstance(processor, ConsoleProcessor):
                console_renderer = processor.get_renderer()
                break

        # 如果找到控制台渲染器就使用它，否则默认使用JSON
        if console_renderer:
            processors.append(console_renderer)
        else:
            processors.append(structlog.processors.JSONRenderer())

        # 配置structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        self._configured = True

    @staticmethod
    def bind_context(**kwargs) -> None:
        """绑定全局上下文"""
        structlog.contextvars.bind_contextvars(**kwargs)

    @staticmethod
    def clear_context() -> None:
        """清除全局上下文"""
        structlog.contextvars.clear_contextvars()

    def remove_processor(self, processor: AsyncProcessor) -> None:
        """移除处理器"""
        if processor in self._processors:
            self._processors.remove(processor)
            self._configured = False  # 重置配置状态
            
    def generate_error_id(self) -> str:
        """生成唯一的错误ID
        
        Returns:
            唯一的错误ID字符串
        """
        return str(uuid.uuid4())
    
    # 添加日志便捷方法
    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        logger = self.get_logger()
        logger.debug(message, **kwargs)
        
    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        logger = self.get_logger()
        logger.info(message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        logger = self.get_logger()
        logger.warning(message, **kwargs)
        
    def error(self, message: str, exc_info=None, **kwargs):
        """记录ERROR级别日志"""
        logger = self.get_logger()
        if exc_info:
            kwargs['exc_info'] = exc_info
        logger.error(message, **kwargs)
        
    def critical(self, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        logger = self.get_logger()
        logger.critical(message, **kwargs)


# 全局日志管理器实例
logger_manager = Logger() 

cleanup_logger = logger_manager.stop()
