"""SQLAlchemy拦截器公共类型定义

定义拦截器系统共享的基础类型。
"""

from enum import Enum, IntEnum, auto
from typing import TypeVar

T = TypeVar('T')

class InterceptorPriority(IntEnum):
    """拦截器优先级定义
    
    数值越小优先级越高:
    - HIGHEST: 最高优先级，用于关键性操作（如事务）
    - HIGH: 高优先级，用于核心功能（如乐观锁）
    - NORMAL: 普通优先级，用于常规功能（如审计）
    - LOW: 低优先级，用于可选功能（如日志）
    - LOWEST: 最低优先级，用于次要功能
    """
    HIGHEST = 50
    HIGH = 100
    NORMAL = 200
    LOW = 300
    LOWEST = 400

class OperationType(Enum):
    """数据库操作类型"""
    CREATE = auto()
    READ = auto()
    GET = auto()
    FIND = auto()
    QUERY = auto()
    UPDATE = auto()
    DELETE = auto()
    BATCH_CREATE = auto()
    BATCH_UPDATE = auto()
    BATCH_DELETE = auto()
    COMMIT = auto()
    ROLLBACK = auto() 