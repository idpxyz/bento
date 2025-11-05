"""站点仓储接口"""
from abc import ABC, abstractmethod
from typing import List, Optional

from idp.framework.domain.repository import AbstractRepository
from idp.framework.examples.domain.entity.stop import Stop


class AbstractStopRepository(AbstractRepository[Stop, str]):
    """站点仓储接口"""

    @abstractmethod
    async def get_by_id(self, stop_id: str) -> Optional[Stop]:
        """根据ID获取站点

        Args:
            stop_id: 站点ID

        Returns:
            Optional[Stop]: 站点，如果不存在则返回 None
        """
        pass

    @abstractmethod
    async def get_all(self) -> List[Stop]:
        """获取所有站点

        Returns:
            List[Stop]: 站点列表
        """
        pass

    @abstractmethod
    async def save(self, stop: Stop) -> None:
        """保存站点

        Args:
            stop: 站点
        """
        pass

    @abstractmethod
    async def delete(self, stop_id: str) -> None:
        """删除站点

        Args:
            stop_id: 站点ID
        """
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> List[Stop]:
        """根据名称获取站点

        Args:
            name: 站点名称

        Returns:
            List[Stop]: 站点列表
        """
        pass

    @abstractmethod
    async def get_by_address(self, address: str) -> List[Stop]:
        """根据地址获取站点

        Args:
            address: 站点地址

        Returns:
            List[Stop]: 站点列表
        """
        pass
