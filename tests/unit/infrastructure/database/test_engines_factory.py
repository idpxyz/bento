from __future__ import annotations

import pytest

from bento.infrastructure.database.config import DatabaseConfig
from bento.infrastructure.database.engines.base import get_engine_for_config


def test_get_engine_for_sqlite_and_kwargs():
    cfg = DatabaseConfig(url="sqlite+aiosqlite:///./app.db", echo=True)
    eng = get_engine_for_config(cfg)
    # SQLite engine specifics
    from sqlalchemy.pool import NullPool

    from bento.infrastructure.database.engines.sqlite import SQLiteEngine

    assert isinstance(eng, SQLiteEngine)
    kwargs = eng.get_engine_kwargs()
    assert kwargs.get("echo") is True and kwargs.get("poolclass") is NullPool
    assert eng.json_column_type == "JSON"


def test_get_engine_for_postgres_and_mysql_not_implemented():
    cfg_pg = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/db")
    eng = get_engine_for_config(cfg_pg)
    from bento.infrastructure.database.engines.postgres import PostgreSQLEngine

    assert isinstance(eng, PostgreSQLEngine)

    cfg_mysql = DatabaseConfig(url="mysql+pymysql://user:pass@localhost/db")
    with pytest.raises(NotImplementedError):
        _ = get_engine_for_config(cfg_mysql)
