from pathlib import Path

from loms.shared.platform.runtime.settings import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def db_check(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def contracts_check() -> bool:
    return Path(settings.contracts.root_dir).exists()
