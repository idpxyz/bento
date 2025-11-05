"""日志模块

提供基于structlog的异步日志系统，支持多种输出目标：
- 控制台输出：支持彩色和JSON格式
- 文件输出：支持异步文件轮转
- Sentry错误跟踪：异步错误上报
- Logstash集中式日志：异步HTTP传输
- Kafka消息队列：异步批量处理
"""

# Import from the new module
from .manager import cleanup_logger, logger_manager
from .processors import (
    AsyncProcessor,
    ConsoleProcessor,
    FileProcessor,
    KafkaProcessor,
    LogstashProcessor,
    SentryProcessor,
)

__all__ = [
    'AsyncProcessor',
    'ConsoleProcessor',
    'FileProcessor',
    'SentryProcessor',
    'LogstashProcessor',
    'KafkaProcessor',
    'logger_manager',
    'cleanup_logger',
]
