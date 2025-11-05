"""数据库连接耗尽模块"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Dict, Optional

from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)


class ConnectionDrainingError(Exception):
    """连接耗尽错误"""
    pass


class ActiveConnectionTracker:
    """活动连接追踪器

    用于追踪当前活动的数据库连接/事务，支持连接耗尽功能
    """

    def __init__(self):
        """初始化连接追踪器"""
        self._active_connections: Dict[str, dict] = {}  # 连接ID -> 连接详情
        self._shutdown_requested = False
        self._shutdown_complete = asyncio.Event()
        self._shutdown_complete.set()  # 初始状态为已完成
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def track_connection(self, connection_type: str = "session"):
        """追踪连接上下文管理器

        Args:
            connection_type: 连接类型，如'session'或'transaction'

        Yields:
            str: 连接ID

        Raises:
            ConnectionDrainingError: 当系统处于关闭状态且不接受新连接时
        """
        async with self._lock:
            # 如果系统正在关闭且不接受新连接，则拒绝创建新连接
            if self._shutdown_requested:
                raise ConnectionDrainingError(
                    "System is shutting down, not accepting new connections")

            # 生成连接ID
            connection_id = str(uuid.uuid4())

            # 记录连接信息
            self._active_connections[connection_id] = {
                "id": connection_id,
                "type": connection_type,
                "start_time": datetime.now(UTC),
                "timestamp": time.time()
            }
            self._shutdown_complete.clear()

        try:
            # 返回连接ID供上层使用
            yield connection_id
        finally:
            # 连接结束，从活动连接中移除
            async with self._lock:
                if connection_id in self._active_connections:
                    del self._active_connections[connection_id]

                # 如果已请求关闭且没有活动连接，则设置关闭完成事件
                if self._shutdown_requested and not self._active_connections:
                    self._shutdown_complete.set()

    async def begin_shutdown(self):
        """开始关闭过程，不再接受新连接"""
        async with self._lock:
            self._shutdown_requested = True
            logger.info(
                "Connection draining started, no new connections will be accepted")

            # 如果没有活动连接，立即设置关闭完成事件
            if not self._active_connections:
                self._shutdown_complete.set()
            else:
                active_count = len(self._active_connections)
                logger.info(
                    f"Waiting for {active_count} active connections to complete")

    async def wait_for_connections_to_close(self, timeout: Optional[float] = None) -> bool:
        """等待所有活动连接关闭

        Args:
            timeout: 等待超时时间（秒），None表示无限等待

        Returns:
            bool: 是否所有连接都已关闭
        """
        if not self._shutdown_requested:
            await self.begin_shutdown()

        try:
            # 等待关闭完成事件，或超时
            if timeout is not None:
                await asyncio.wait_for(self._shutdown_complete.wait(), timeout)
            else:
                await self._shutdown_complete.wait()
            return True
        except asyncio.TimeoutError:
            return False

    async def get_active_connections(self) -> Dict[str, dict]:
        """获取当前活动连接列表

        Returns:
            Dict[str, dict]: 活动连接字典，键为连接ID
        """
        async with self._lock:
            return self._active_connections.copy()

    async def get_connection_count(self) -> int:
        """获取当前活动连接数量

        Returns:
            int: 活动连接数量
        """
        async with self._lock:
            return len(self._active_connections)

    async def force_close_all(self):
        """强制关闭所有连接

        注意: 此方法不会实际关闭数据库连接，只是重置追踪状态
        应该只在紧急情况下使用
        """
        async with self._lock:
            connection_count = len(self._active_connections)
            self._active_connections.clear()
            self._shutdown_complete.set()
            logger.warning(
                f"Forced closure of {connection_count} active connections")

    async def reset(self):
        """重置追踪器状态

        用于测试或重新初始化系统
        """
        async with self._lock:
            self._active_connections.clear()
            self._shutdown_requested = False
            self._shutdown_complete.set()

    @property
    def is_shutting_down(self) -> bool:
        """系统是否正在关闭

        Returns:
            bool: 是否正在关闭
        """
        return self._shutdown_requested

    @property
    def is_shutdown_complete(self) -> bool:
        """关闭过程是否已完成

        Returns:
            bool: 是否已完成关闭
        """
        return self._shutdown_complete.is_set()


# 全局连接追踪器实例
connection_tracker = ActiveConnectionTracker()
