"""数据库引擎实现模块"""

from typing import Dict, Type

from .base import BaseDatabaseEngine
from .mysql import MySQLDatabase
from .postgres import PostgreSQLDatabase
from .sqlite import SQLiteDatabase


def get_engines() -> Dict[str, Type[BaseDatabaseEngine]]:
    """获取所有可用的数据库引擎实现

    Returns:
        Dict[str, Type[BaseDatabaseEngine]]: 数据库引擎类型映射
    """
    return {
        'mysql': MySQLDatabase,
        'postgresql': PostgreSQLDatabase,
        'sqlite': SQLiteDatabase
    }


__all__ = [
    'BaseDatabaseEngine',
    'MySQLDatabase',
    'PostgreSQLDatabase',
    'SQLiteDatabase',
    'get_engines'
]
