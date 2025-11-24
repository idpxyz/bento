"""Connection draining for graceful shutdown.

This module provides utilities for gracefully draining database connections
during application shutdown, particularly useful in Kubernetes/Docker environments.
"""

import asyncio
import logging
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class DrainingMode(Enum):
    """Connection draining modes."""

    GRACEFUL = "graceful"  # Wait for connections to complete
    IMMEDIATE = "immediate"  # Close connections immediately
    FORCE = "force"  # Forcefully close all connections


class ConnectionDrainer:
    """Manages graceful connection draining during shutdown.

    This class helps applications shut down cleanly by:
    1. Stopping acceptance of new connections
    2. Waiting for active connections to complete
    3. Forcefully closing connections after timeout
    """

    def __init__(
        self,
        engine: AsyncEngine,
        timeout: float = 30.0,
        mode: DrainingMode = DrainingMode.GRACEFUL,
        check_interval: float = 0.5,
    ):
        """Initialize connection drainer.

        Args:
            engine: SQLAlchemy async engine
            timeout: Maximum time to wait for connections to drain (seconds)
            mode: Draining mode (graceful, immediate, or force)
            check_interval: Interval for checking connection status (seconds)
        """
        self.engine = engine
        self.timeout = timeout
        self.mode = mode
        self.check_interval = check_interval
        self._is_draining = False

    async def drain(self) -> dict[str, Any]:
        """Drain all database connections.

        Returns:
            Dictionary with draining statistics:
            - mode: Draining mode used
            - timeout: Timeout value
            - connections_at_start: Connections when draining started
            - connections_at_end: Connections after draining
            - time_taken: Time taken to drain
            - success: Whether draining was successful

        Example:
            ```python
            drainer = ConnectionDrainer(engine, timeout=30.0)
            stats = await drainer.drain()
            print(
                f"Drained {stats['connections_at_start']} connections "
                f"in {stats['time_taken']:.2f}s"
            )
            ```
        """
        if self._is_draining:
            logger.warning("Connection draining already in progress")
            return {"success": False, "reason": "already_draining"}

        self._is_draining = True
        start_time = asyncio.get_event_loop().time()

        try:
            logger.info(
                f"Starting connection draining (mode={self.mode.value}, timeout={self.timeout}s)"
            )

            # Get initial connection count
            initial_connections = await self._get_connection_count()
            logger.info(f"Active connections at start: {initial_connections}")

            # Execute draining based on mode
            if self.mode == DrainingMode.IMMEDIATE:
                await self._drain_immediate()
            elif self.mode == DrainingMode.FORCE:
                await self._drain_force()
            else:  # GRACEFUL
                await self._drain_graceful()

            # Get final connection count
            final_connections = await self._get_connection_count()
            time_taken = asyncio.get_event_loop().time() - start_time

            logger.info(
                f"Connection draining completed in {time_taken:.2f}s "
                f"({initial_connections} -> {final_connections} connections)"
            )

            return {
                "success": True,
                "mode": self.mode.value,
                "timeout": self.timeout,
                "connections_at_start": initial_connections,
                "connections_at_end": final_connections,
                "time_taken": time_taken,
            }

        except Exception as e:
            logger.error(f"Error during connection draining: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "mode": self.mode.value,
            }
        finally:
            self._is_draining = False

    async def _drain_graceful(self) -> None:
        """Gracefully drain connections by waiting for them to complete."""
        elapsed = 0.0

        while elapsed < self.timeout:
            connections = await self._get_connection_count()

            if connections == 0:
                logger.info("All connections drained gracefully")
                break

            logger.debug(
                f"Waiting for {connections} connections to complete "
                f"({elapsed:.1f}s / {self.timeout}s)"
            )

            await asyncio.sleep(self.check_interval)
            elapsed += self.check_interval

        # If timeout reached, dispose the pool
        if elapsed >= self.timeout:
            logger.warning(f"Graceful draining timeout reached ({self.timeout}s), disposing pool")
            await self.engine.dispose()

    async def _drain_immediate(self) -> None:
        """Immediately close the connection pool without waiting."""
        logger.info("Disposing connection pool immediately")
        await self.engine.dispose()

    async def _drain_force(self) -> None:
        """Forcefully close all connections."""
        logger.warning("Forcefully closing all database connections")
        await self.engine.dispose()

    async def _get_connection_count(self) -> int:
        """Get the number of active connections.

        Returns:
            Number of active connections, or 0 if unable to determine
        """
        try:
            pool = self.engine.pool
            # checkedout is a method, not an attribute
            # Note: Only available on QueuePool and AsyncAdaptedQueuePool, not StaticPool
            if hasattr(pool, "checkedout") and callable(pool.checkedout):  # type: ignore[attr-defined]
                count = pool.checkedout()  # type: ignore[attr-defined]
                return int(count)  # type: ignore[arg-type]
            else:
                # Pool doesn't support connection tracking (e.g., StaticPool for SQLite)
                return 0
        except Exception as e:
            logger.debug(f"Unable to get connection count: {e}")
            return 0


async def drain_connections(
    engine: AsyncEngine,
    timeout: float = 30.0,
    mode: DrainingMode = DrainingMode.GRACEFUL,
) -> dict[str, Any]:
    """Convenience function to drain database connections.

    Args:
        engine: SQLAlchemy async engine
        timeout: Maximum time to wait (seconds)
        mode: Draining mode

    Returns:
        Dictionary with draining statistics

    Example:
        ```python
        # In application shutdown
        await drain_connections(engine, timeout=30.0)
        ```
    """
    drainer = ConnectionDrainer(engine, timeout=timeout, mode=mode)
    return await drainer.drain()


async def drain_with_signal_handler(
    engine: AsyncEngine,
    timeout: float = 30.0,
) -> None:
    """Drain connections when receiving SIGTERM/SIGINT.

    This function is useful for Kubernetes/Docker deployments
    where graceful shutdown is triggered by signals.

    Args:
        engine: SQLAlchemy async engine
        timeout: Maximum time to wait (seconds)

    Example:
        ```python
        # Setup signal handlers
        import signal

        async def shutdown():
            await drain_with_signal_handler(engine)

        # Register handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        ```
    """
    logger.info("Received shutdown signal, draining connections...")
    stats = await drain_connections(engine, timeout=timeout)

    if stats.get("success"):
        logger.info(f"Shutdown complete: {stats}")
    else:
        logger.error(f"Shutdown failed: {stats}")
