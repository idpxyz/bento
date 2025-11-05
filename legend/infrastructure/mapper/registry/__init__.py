"""映射器注册表模块。

提供映射器注册表的实现和管理。

Key Components:
- MapperRegistryImpl: 映射器注册表基础实现
- POMapperRegistry: 持久化对象映射器注册表
- DTOMapperRegistry: 数据传输对象映射器注册表
- VOMapperRegistry: 值对象映射器注册表
"""

from .base import MapperRegistryImpl
from .po import POMapperRegistry
from .dto import DTOMapperRegistry
from .vo import VOMapperRegistry

# 全局映射器注册表实例
po_mapper_registry = POMapperRegistry()
dto_mapper_registry = DTOMapperRegistry()
vo_mapper_registry = VOMapperRegistry()

__all__ = [
    'MapperRegistryImpl',
    'POMapperRegistry',
    'DTOMapperRegistry',
    'VOMapperRegistry',
    'po_mapper_registry',
    'dto_mapper_registry',
    'vo_mapper_registry',
] 