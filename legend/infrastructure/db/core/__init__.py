"""数据库核心模块"""

# 从接口模块导出 Database 类和其他接口
# 导出连接追踪器
from .connection_draining import connection_tracker

# 从上下文模块导出上下文变量
from .context import in_transaction, request_id, session_id
from .interfaces import (
    ConnectionManager,
    Database,
    DatabaseMetrics,
    QueryBuilder,
    QueryExecutor,
    ReplicaManager,
    SessionManager,
    TransactionManager,
    UnitOfWork,
)

__all__ = [
    "ConnectionManager",
    "Database",
    "DatabaseMetrics",
    "QueryBuilder",
    "QueryExecutor",
    "ReplicaManager",
    "SessionManager",
    "TransactionManager",
    "UnitOfWork",
]
