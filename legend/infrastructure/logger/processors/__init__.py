"""日志处理器模块

提供各种异步日志处理器的实现：
- 控制台处理器：支持彩色输出和JSON格式
- 文件处理器：支持异步文件轮转
- Sentry处理器：错误跟踪和监控
- Logstash处理器：集中式日志收集
- Kafka处理器：事件流处理
"""

from .base import AsyncProcessor
from .console import ConsoleProcessor
from .file import FileProcessor
from .sentry import SentryProcessor
from .logstash import LogstashProcessor
from .kafka import KafkaProcessor

__all__ = [
    'AsyncProcessor',
    'ConsoleProcessor',
    'FileProcessor',
    'SentryProcessor',
    'LogstashProcessor',
    'KafkaProcessor',
] 