from typing import Awaitable, Callable, Dict

import redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from idp.framework.infrastructure.database.session import engine, read_engine

# ✅ 插件式探针注册表
health_probes: Dict[str, Callable[[], Awaitable[tuple[bool, str]]]] = {}


# ── 主库探针 ─────────────────────────────
async def check_database_main() -> tuple[bool, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "connected"
    except SQLAlchemyError as e:
        return False, f"DB error: {e}"


# ── 只读库探针 ──────────────────────────
async def check_database_read() -> tuple[bool, str]:
    if read_engine is None:
        return True, "not configured"
    try:
        async with read_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "connected"
    except SQLAlchemyError as e:
        return False, f"Read DB error: {e}"


async def check_redis() -> tuple[bool, str]:
    try:
        await redis.ping()
        return True, "connected"
    except Exception as e:
        return False, str(e)

health_probes["redis"] = check_redis


# ── 注册探针 ─────────────────────────────
health_probes["database_main"] = check_database_main
health_probes["database_read"] = check_database_read

# 可后续添加:
# health_probes["redis"] = check_redis
# health_probes["kafka"] = check_kafka
