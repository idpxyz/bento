"""数据库接口定义"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
)

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from idp.framework.infrastructure.db.config import DatabaseConfig

T = TypeVar('T')
R = TypeVar('R')

class ConnectionManager(ABC):
    """连接管理器接口"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化连接"""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """清理连接资源"""
        pass
        
    @abstractmethod
    async def check_health(self) -> bool:
        """检查连接健康状态"""
        pass
        
    @abstractmethod
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[AsyncConnection, None]:
        """获取数据库连接
        
        Yields:
            AsyncConnection: 数据库连接
        """
        yield None

class SessionManager(ABC):
    """会话管理器接口
    
    负责创建和管理数据库会话，处理会话的生命周期和异常。
    """
    
    @abstractmethod
    @asynccontextmanager
    async def create_session(self) -> AsyncGenerator[AsyncSession, None]:
        """创建新的会话
        
        创建并返回一个新的数据库会话，处理会话生命周期和异常。
        
        Yields:
            AsyncSession: 数据库会话
        """
        yield None
        
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取会话统计信息
        
        Returns:
            Dict[str, Any]: 会话统计信息，包括总会话数、活动会话数等
        """
        pass

class QueryExecutor(Generic[T, R], ABC):
    """查询执行器接口"""
    
    @abstractmethod
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> R:
        """执行查询"""
        pass
        
    @abstractmethod
    async def execute_many(self, queries: List[str], params: Optional[List[Dict[str, Any]]] = None) -> List[R]:
        """批量执行查询"""
        pass

class TransactionManager(ABC):
    """事务管理器接口"""
    
    @abstractmethod
    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[AsyncSession, None]:
        """开始事务"""
        yield None
        
    @abstractmethod
    @asynccontextmanager
    async def begin_nested(self) -> AsyncGenerator[AsyncSession, None]:
        """开始嵌套事务"""
        yield None
        
    @abstractmethod
    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[str] = None
    ) -> AsyncGenerator[AsyncSession, None]:
        """在指定隔离级别下开始事务
        
        Args:
            isolation_level: 事务隔离级别
            
        Yields:
            AsyncSession: 数据库会话
        """
        yield None

class ReplicaManager(ABC):
    """副本管理器接口"""
    
    @abstractmethod
    async def initialize_replicas(self) -> None:
        """初始化副本"""
        pass
        
    @abstractmethod
    @asynccontextmanager
    async def get_replica_session(self, index: int) -> AsyncGenerator[AsyncSession, None]:
        """获取副本会话"""
        yield None
        
    @abstractmethod
    async def select_replica(self) -> Optional[int]:
        """选择可用副本"""
        pass

class UnitOfWork(ABC):
    """工作单元接口"""
    
    @abstractmethod
    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[None, None]:
        """开始工作单元"""
        yield None
        
    @abstractmethod
    async def commit(self) -> None:
        """提交更改"""
        pass
        
    @abstractmethod
    async def rollback(self) -> None:
        """回滚更改"""
        pass

class QueryBuilder(Generic[T], ABC):
    """查询构建器接口"""
    
    @abstractmethod
    def build(self, **kwargs: Any) -> str:
        """构建查询"""
        pass

class DatabaseMetrics(ABC):
    """数据库指标接口"""
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass
        
    @abstractmethod
    async def record_operation(self, operation: str, duration: float) -> None:
        """记录操作指标"""
        pass

class Database(ABC):
    """数据库抽象基类"""
    
    def __init__(self, config: DatabaseConfig):
        """初始化数据库实例
        
        Args:
            config: 数据库配置
        """
        self.config = config
        self._initialized = False
        
    @property
    def is_initialized(self) -> bool:
        """获取数据库是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._initialized
        
    @abstractmethod
    async def initialize(self) -> None:
        """初始化数据库连接"""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """清理数据库资源"""
        pass
        
    @abstractmethod
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        yield None
    
    @abstractmethod
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """获取数据库连接
        
        直接获取底层数据库连接，主要用于需要低级别访问的场景。
        大多数情况下应优先使用get_session方法获取会话。
        
        Yields:
            AsyncConnection: 数据库连接
        """
        yield None
        
    @abstractmethod
    async def check_health(self) -> bool:
        """检查数据库健康状态
        
        Returns:
            bool: 是否健康
        """
        pass
        
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        pass

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            Any: 查询结果
        """
        return await self._execute_query_impl(query, params)
        
    @abstractmethod
    async def _execute_query_impl(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """实际的查询执行实现
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            Any: 查询结果
        """
        pass
        
    async def execute_queries(self, queries: List[str], params: Optional[List[Dict[str, Any]]] = None) -> List[Any]:
        """批量执行SQL查询
        
        Args:
            queries: SQL查询语句列表
            params: 查询参数列表
            
        Returns:
            List[Any]: 查询结果列表
        """
        if params and len(queries) != len(params):
            raise ValueError("Queries and params must have the same length")
            
        results = []
        for i, query in enumerate(queries):
            param = params[i] if params else None
            result = await self.execute_query(query, param)
            results.append(result)
            
        return results 