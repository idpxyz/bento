"""SQLAlchemy 依赖注入

定义 SQLAlchemy 相关的依赖注入。
"""
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker

from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


async def get_uow(request: Request) -> AsyncGenerator[SqlAlchemyAsyncUoW, None]:
    """获取工作单元

    Args:
        request: FastAPI 请求对象

    Returns:
        AsyncGenerator[SqlAlchemyAsyncUoW, None]: 工作单元

    Note:
        需要在应用启动时设置以下状态：
        - app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
        - app.state.event_bus = event_bus
    """
    # (1) 获取 session_factory；如果缺失则尝试回退到 Database 实例动态创建
    sf: async_sessionmaker | None = getattr(
        # type: ignore[attr-defined]
        request.app.state, "session_factory", None)

    if sf is None:
        # 尝试从已初始化的 Database 获取引擎, 动态创建 session_factory
        from idp.framework.infrastructure.db.database import get_database  # 本地导入，避免循环依赖
        try:
            db = get_database()
            # pyright: ignore[reportGeneralTypeIssues]
            engine = db.connection_manager.engine

            # 若 engine 被包装，则取其底层 AsyncEngine
            from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

            if not isinstance(engine, AsyncEngine) and hasattr(engine, "_engine"):
                engine = engine._engine  # type: ignore[attr-defined]

            # type: ignore[assignment]
            sf = async_sessionmaker(bind=engine, expire_on_commit=False)
            # 缓存到 app.state，供后续请求复用
            # type: ignore[attr-defined]
            request.app.state.session_factory = sf
        except Exception as exc:  # pragma: no cover – 回退失败说明应用启动过程异常
            raise RuntimeError(
                "Session factory not initialized. Ensure application startup has correctly configured database and session_factory.") from exc

    # (2) 获取事件总线
    bus: AbstractEventBus | None = getattr(
        request.app.state, "event_bus", None)  # type: ignore[attr-defined]
    if bus is None:
        raise RuntimeError(
            "Event bus not initialized. Did you forget to attach it to app.state during startup?")

    # (3) 创建并 yield 工作单元
    uow = SqlAlchemyAsyncUoW(sf, bus)
    try:
        async with uow:
            yield uow
    finally:
        await uow.session.close()
