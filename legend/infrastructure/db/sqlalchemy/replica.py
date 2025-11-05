"""SQLAlchemy副本管理器实现"""

import asyncio
import random
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.database import DatabaseErrorCode
from idp.framework.infrastructure.db.config import DatabaseConfig
from idp.framework.infrastructure.db.core.interfaces import ReplicaManager
from idp.framework.infrastructure.db.sqlalchemy.connection import (
    SQLAlchemyConnectionManager,
)
from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)


class SQLAlchemyReplicaManager(ReplicaManager):
    """SQLAlchemy副本管理器"""

    def __init__(
        self,
        config: DatabaseConfig,
        connection_manager: SQLAlchemyConnectionManager
    ) -> None:
        """初始化副本管理器

        Args:
            config: 数据库配置
            connection_manager: 主数据库连接管理器
        """
        self._config = config
        self._connection_manager = connection_manager
        self._replica_engines: List[AsyncEngine] = []
        self._replica_factories: List[async_sessionmaker[AsyncSession]] = []
        self._replica_stats: Dict[int, Dict[str, float]] = {}
        self._health_check_lock = asyncio.Lock()
        self._current_replica_index = -1  # 用于round_robin策略
        self._connection_counts: Dict[int, int] = {}  # 用于least_connections策略

    async def initialize_replicas(self) -> None:
        """初始化副本"""
        if not self._config.read_write.enable_read_write_split:
            logger.info(
                "Read-write split is disabled, skipping replica initialization")
            return

        if not self._config.read_write.read_replicas:
            logger.warning("No read replicas configured")
            return

        try:
            for i, replica_config in enumerate(self._config.read_write.read_replicas):
                # create_async_engine 返回同步对象，不需要 await
                engine = self._create_replica_engine(replica_config)
                self._replica_engines.append(engine)

                session_factory = async_sessionmaker(
                    bind=engine,
                    expire_on_commit=False,
                    class_=AsyncSession
                )
                self._replica_factories.append(session_factory)

                # 初始化副本统计信息
                self._replica_stats[i] = {
                    "response_time": 0.0,
                    "error_rate": 0.0,
                    "last_success": 0.0
                }

                # 初始化连接计数
                self._connection_counts[i] = 0

            logger.info(
                f"Initialized {len(self._replica_engines)} read replicas")

            # 启动健康检查任务
            asyncio.create_task(self._health_check_loop())

        except Exception as e:
            logger.error(f"Failed to initialize replicas: {e}")
            raise InfrastructureException(
                code=DatabaseErrorCode.REPLICA_INITIALIZATION_ERROR,
                details={"message": f"Failed to initialize replicas: {str(e)}"}
            )

    @asynccontextmanager
    async def get_replica_session(self, index: int) -> AsyncGenerator[AsyncSession, None]:
        """获取副本会话

        Args:
            index: 副本索引

        Yields:
            AsyncSession: 副本会话

        Raises:
            InfrastructureException: 当副本不可用时
        """
        if not (0 <= index < len(self._replica_factories)):
            raise InfrastructureException(
                code=DatabaseErrorCode.INVALID_REPLICA,
                details={"message": f"Invalid replica index: {index}"}
            )

        session_factory = self._replica_factories[index]
        session = session_factory()

        # 增加连接计数
        self._connection_counts[index] += 1

        try:
            # 确保会话开始时处于干净状态
            await session.rollback()
            yield session
        finally:
            try:
                # 确保会话结束时处于干净状态
                await session.rollback()
            except Exception as e:
                logger.warning(f"Error rolling back session: {e}")
            finally:
                await session.close()
                # 减少连接计数
                self._connection_counts[index] = max(
                    0, self._connection_counts[index] - 1)

    async def select_replica(self) -> Optional[int]:
        """选择可用副本

        Returns:
            Optional[int]: 健康的副本索引，如果没有可用的副本则返回None
        """
        if not self._replica_engines:
            return None

        # 获取所有健康的副本
        healthy_replicas = []
        async with self._health_check_lock:
            for i in range(len(self._replica_engines)):
                if await self._check_replica_health(i):
                    healthy_replicas.append(i)

        if not healthy_replicas:
            logger.warning("No healthy replicas available")
            return None

        # 根据配置的负载均衡策略选择副本
        strategy = self._config.read_write.load_balance_strategy

        if strategy == "round_robin":
            return await self._select_replica_round_robin(healthy_replicas)
        elif strategy == "random":
            return await self._select_replica_random(healthy_replicas)
        elif strategy == "least_connections":
            return await self._select_replica_least_connections(healthy_replicas)
        else:
            # 默认使用加权轮询
            return await self._select_replica_weighted(healthy_replicas)

    async def _select_replica_round_robin(self, healthy_replicas: List[int]) -> int:
        """使用轮询策略选择副本

        Args:
            healthy_replicas: 健康的副本索引列表

        Returns:
            int: 选择的副本索引
        """
        self._current_replica_index = (
            self._current_replica_index + 1) % len(healthy_replicas)
        return healthy_replicas[self._current_replica_index]

    async def _select_replica_random(self, healthy_replicas: List[int]) -> int:
        """使用随机策略选择副本

        Args:
            healthy_replicas: 健康的副本索引列表

        Returns:
            int: 选择的副本索引
        """
        return random.choice(healthy_replicas)

    async def _select_replica_least_connections(self, healthy_replicas: List[int]) -> int:
        """使用最少连接策略选择副本

        Args:
            healthy_replicas: 健康的副本索引列表

        Returns:
            int: 选择的副本索引
        """
        min_connections = float('inf')
        selected_replica = healthy_replicas[0]

        for replica_index in healthy_replicas:
            connections = self._connection_counts.get(replica_index, 0)
            if connections < min_connections:
                min_connections = connections
                selected_replica = replica_index

        return selected_replica

    async def _select_replica_weighted(self, healthy_replicas: List[int]) -> int:
        """使用加权算法选择副本

        加权因素包括:
        1. 响应时间
        2. 错误率
        3. 最后一次成功时间

        Args:
            healthy_replicas: 健康的副本索引列表

        Returns:
            int: 选择的副本索引
        """
        replica_scores = [(i, self._calculate_replica_score(i))
                          for i in healthy_replicas]
        replica_scores.sort(key=lambda x: x[1], reverse=True)
        return replica_scores[0][0]

    def _create_replica_engine(self, replica_config: Any) -> AsyncEngine:
        """创建副本引擎

        Args:
            replica_config: 副本配置

        Returns:
            AsyncEngine: 副本引擎
        """
        # 创建连接池配置
        pool_config = {
            "pool_size": self._config.pool.min_size,
            "max_overflow": self._config.pool.max_overflow,
            "pool_timeout": self._config.pool.timeout,
            "pool_recycle": self._config.pool.recycle,
            "pool_pre_ping": self._config.pool.pre_ping,
            "echo": self._config.pool.echo
        }

        # 获取连接参数
        connect_args = replica_config.get_connect_args()

        # 直接使用 create_async_engine 创建引擎，将连接池配置和连接参数作为关键字参数传递
        return create_async_engine(
            replica_config.get_url(),
            pool_size=pool_config["pool_size"],
            max_overflow=pool_config["max_overflow"],
            pool_timeout=pool_config["pool_timeout"],
            pool_recycle=pool_config["pool_recycle"],
            pool_pre_ping=pool_config["pool_pre_ping"],
            echo=pool_config["echo"],
            connect_args=connect_args  # 将连接参数作为 connect_args 传递
        )

    async def _check_replica_health(self, index: int) -> bool:
        """检查副本健康状态

        Args:
            index: 副本索引

        Returns:
            bool: 健康状态
        """
        if not (0 <= index < len(self._replica_engines)):
            return False

        try:
            start_time = asyncio.get_event_loop().time()
            async with self.get_replica_session(index) as session:
                # 确保在健康检查前回滚任何未完成的事务
                await session.rollback()
                # 执行简单的健康检查查询
                await session.execute(text("SELECT 1"))
                # 确保事务被提交
                await session.commit()

            # 更新统计信息
            elapsed = asyncio.get_event_loop().time() - start_time
            self._update_replica_stats(index, elapsed, True)
            return True

        except Exception as e:
            logger.warning(f"Replica {index} health check failed: {e}")
            self._update_replica_stats(index, 0.0, False)
            return False

    def _calculate_replica_score(self, index: int) -> float:
        """计算副本得分

        Args:
            index: 副本索引

        Returns:
            float: 副本得分
        """
        stats = self._replica_stats[index]
        response_time_weight = 0.4
        error_rate_weight = 0.4
        last_success_weight = 0.2

        response_time_score = 1.0 / (1.0 + stats["response_time"])
        error_rate_score = 1.0 - stats["error_rate"]
        last_success_score = 1.0 / \
            (1.0 + asyncio.get_event_loop().time() - stats["last_success"])

        return (
            response_time_weight * response_time_score +
            error_rate_weight * error_rate_score +
            last_success_weight * last_success_score
        )

    def _update_replica_stats(self, index: int, response_time: float, success: bool) -> None:
        """更新副本统计信息

        Args:
            index: 副本索引
            response_time: 响应时间
            success: 是否成功
        """
        stats = self._replica_stats[index]
        alpha = 0.2  # 平滑因子

        if success:
            stats["response_time"] = (
                1 - alpha) * stats["response_time"] + alpha * response_time
            stats["error_rate"] = (1 - alpha) * stats["error_rate"]
            stats["last_success"] = asyncio.get_event_loop().time()
        else:
            stats["error_rate"] = (1 - alpha) * stats["error_rate"] + alpha

    async def _health_check_loop(self) -> None:
        """副本健康检查循环"""
        while True:
            try:
                async with self._health_check_lock:
                    for i in range(len(self._replica_engines)):
                        await self._check_replica_health(i)

                # 等待下一次检查
                await asyncio.sleep(self._config.read_write.health_check_interval)

            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(1.0)  # 错误后短暂等待
