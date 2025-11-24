from __future__ import annotations

from bento.infrastructure.database.config import DatabaseConfig, get_database_config


def test_database_config_flags_and_helper():
    # defaults -> sqlite
    cfg = DatabaseConfig()
    assert cfg.is_sqlite is True
    assert cfg.database_type == "sqlite"

    # postgres url
    cfg_pg = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/db")
    assert cfg_pg.is_postgres is True and cfg_pg.database_type == "postgres"

    # mysql url
    cfg_my = DatabaseConfig(url="mysql+pymysql://user:pass@localhost/db")
    assert cfg_my.is_mysql is True and cfg_my.database_type == "mysql"

    # helper with override
    cfg2 = get_database_config(url="sqlite+aiosqlite:///./app.db", pool_size=7)
    assert cfg2.is_sqlite and cfg2.pool_size == 7
