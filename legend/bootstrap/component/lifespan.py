"""生命周期管理组件

提供统一的应用生命周期管理，包括：
1. 组件初始化
2. 资源清理
3. 健康检查
4. 状态管理
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI

from idp.framework.bootstrap.component.db_setup import (
    cleanup_database,
    db_setup,
    get_db_stats,
)
from idp.framework.bootstrap.component.logger_setup import logger_setup
from idp.framework.bootstrap.component.setting.app import setup_app_config
from idp.framework.infrastructure.db.database import get_database
from idp.framework.infrastructure.logger import logger_manager
from idp.framework.infrastructure.projection.projector import OutboxProjector

logger = logger_manager.get_logger(__name__)


class LifespanManager:
    """生命周期管理器

    统一管理所有需要生命周期控制的组件，包括：
    1. 数据库组件
    2. 缓存组件（未来扩展）
    3. 消息队列组件（未来扩展）
    等
    """

    def __init__(self):
        """初始化生命周期管理器"""
        self._initialized = False
        self._config_dir = None  # 移除默认配置目录
        self._app: Optional[FastAPI] = None
        self._projector_task: Optional[asyncio.Task] = None
        logger.debug("初始化生命周期管理器")

    def set_config_dir(self, config_dir: str) -> None:
        """设置配置目录

        Args:
            config_dir: 配置目录路径
        """
        if config_dir:
            self._config_dir = config_dir
            logger.debug(f"更新配置目录: {self._config_dir}")

    def set_app(self, app: FastAPI) -> None:
        """设置 FastAPI 应用实例

        Args:
            app: FastAPI 应用实例
        """
        self._app = app

    async def initialize(self, env_name: Optional[str] = None) -> None:
        """初始化应用

        Args:
            env_name: 环境名称
        """
        # ① 已初始化直接返回
        if self._initialized:
            logger.warning("应用已经初始化")
            return

        # ② _app 必须先设置
        if not self._app:
            raise RuntimeError("FastAPI 应用实例未设置")

        # ③ 初始化日志（最早捕获后续日志）
        await logger_setup(env_name=env_name, config_dir=self._config_dir)
        logger.info("✅ 日志组件初始化成功")

        try:
            logger.info(
                f"🚀 正在初始化应用... (环境: {env_name or 'dev'}, 配置目录: {self._config_dir})"
            )

            # ④ 应用配置（如果已在 create_app 中加载，则复用）
            if hasattr(self._app.state, "settings") and self._app.state.settings:
                # type: ignore[attr-defined]
                app_config = self._app.state.settings
                logger.debug("复用已加载的应用配置")
            else:
                app_config = await setup_app_config(
                    env_name=env_name, config_dir=self._config_dir
                )
                self._app.state.settings = app_config

            # ⑤ 数据库
            await db_setup(
                app=self._app, env_name=env_name, config_dir=self._config_dir
            )
            logger.info("✅ 数据库初始化成功")

            # ⑥ 健康检查
            db = getattr(self._app.state, "db", None)
            if not db or not await db.health_check():
                raise RuntimeError("Database health check failed")

            # ⑦ 初始化 OutboxProjector
            if hasattr(self._app.state, "event_bus"):
                # 获取数据库工厂的会话管理器
                session_manager = db._factory.session_manager
                if not session_manager:
                    raise RuntimeError("Session manager not initialized")

                # 确保 session_factory 已绑定到正确的引擎
                if not session_manager._session_factory:
                    raise RuntimeError("Session factory not initialized")

                # 获取数据库引擎
                engine = db._factory.connection_manager.engine
                if not engine:
                    raise RuntimeError("Database engine not initialized")

                # 获取 SQLAlchemy AsyncEngine
                from sqlalchemy.ext.asyncio import AsyncEngine
                if not isinstance(engine, AsyncEngine):
                    # 如果 engine 不是 AsyncEngine，尝试获取底层的 engine
                    if hasattr(engine, '_engine'):
                        engine = engine._engine
                    else:
                        raise RuntimeError(
                            f"Expected AsyncEngine, got {type(engine)}")

                # 创建新的 session_factory 并绑定到引擎
                from sqlalchemy.ext.asyncio import async_sessionmaker
                session_factory = async_sessionmaker(
                    bind=engine,
                    expire_on_commit=False
                )

                # 保存 session_factory 到应用状态
                self._app.state.session_factory = session_factory

                projector = OutboxProjector(
                    sf=session_factory,  # 使用新创建的 session_factory
                    bus=self._app.state.event_bus,
                    tenant_id="default",
                    batch_size=100,
                )
                # 异步任务，不阻塞主线程
                self._projector_task = asyncio.create_task(
                    projector.run_forever())
                logger.info("✅ OutboxProjector started for tenant=default")

            self._initialized = True
            logger.info("✅ 应用初始化完成")

        except Exception as e:
            logger.error(f"❌ 应用初始化失败: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        """清理所有组件资源"""
        if not self._initialized:
            return

        try:
            logger.info("正在清理组件资源...")

            # 1. 停止 OutboxProjector
            if self._projector_task and not self._projector_task.done():
                self._projector_task.cancel()
                try:
                    await self._projector_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ OutboxProjector stopped")

            # 2. 清理数据库组件
            await cleanup_database()

            # 3. 清理日志组件
            try:
                # 首先尝试停止所有处理器
                for processor in logger_manager._processors:
                    if hasattr(processor, 'stop'):
                        await processor.stop()
                    elif hasattr(processor, 'cleanup'):
                        await processor.cleanup()

                # 然后停止logger_manager
                if hasattr(logger_manager, 'stop'):
                    await logger_manager.stop()

            except Exception as e:
                logger.warning(f"清理日志组件时发生警告: {e}")

            self._initialized = False
            logger.info("✅ 所有组件资源清理完成")

        except Exception as e:
            logger.error(f"❌ 组件资源清理失败: {e}")
            raise

    async def get_health_status(self) -> Dict:
        """获取健康状态

        Returns:
            Dict: 健康状态信息
        """
        status = {
            "status": "healthy" if self._initialized else "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "components": {
                "app": {
                    "status": "healthy" if self._initialized else "unhealthy",
                    "initialized": self._initialized,
                    "config_dir": self._config_dir
                }
            }
        }

        # 添加数据库状态
        try:
            db_stats = await get_db_stats()
            status["components"]["database"] = {
                "status": "healthy" if db_stats.get("healthy_instances", 0) > 0 else "unhealthy",
                "details": db_stats
            }
        except Exception as e:
            status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        return status


# 全局生命周期管理器实例
lifespan_manager = LifespanManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器

    Args:
        app: FastAPI 应用实例
    """
    # 设置应用实例
    lifespan_manager.set_app(app)

    try:
        # 启动
        if hasattr(app.state, "env") and app.state.env:
            env_name = app.state.env
        elif hasattr(app.state, "settings") and hasattr(app.state.settings, "env"):
            env_name = app.state.settings.env  # type: ignore[attr-defined]
        else:
            env_name = None

        # 如果应用状态中有配置目录，则使用它
        if hasattr(app.state, "config_dir"):
            lifespan_manager.set_config_dir(app.state.config_dir)

        await lifespan_manager.initialize(env_name=env_name)
        yield
    finally:
        # 清理
        await lifespan_manager.cleanup()
