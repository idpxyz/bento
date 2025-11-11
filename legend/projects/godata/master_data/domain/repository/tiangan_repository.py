from abc import ABC, abstractmethod
from typing import List, Optional

from idp.projects.godata.master_data.domain.aggregate.tiangan import Tiangan


class TianganRepository(ABC):
    """天干仓储接口 - 遵循依赖倒置原则"""

    @abstractmethod
    async def get_by_id(self, tiangan_id: str) -> Optional[Tiangan]:
        """根据ID获取天干"""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Tiangan]:
        """根据名称获取天干"""
        pass

    @abstractmethod
    async def get_by_order(self, order: int) -> Optional[Tiangan]:
        """根据序号获取天干"""
        pass

    @abstractmethod
    async def get_all(self) -> List[Tiangan]:
        """获取所有天干"""
        pass

    @abstractmethod
    async def get_by_wuxing(self, wu_xing: str) -> List[Tiangan]:
        """根据五行属性获取天干列表"""
        pass

    @abstractmethod
    async def get_by_yin_yang(self, yin_yang: str) -> List[Tiangan]:
        """根据阴阳属性获取天干列表"""
        pass

    @abstractmethod
    async def save(self, tiangan: Tiangan) -> Tiangan:
        """保存天干"""
        pass

    @abstractmethod
    async def delete(self, tiangan_id: str) -> bool:
        """删除天干"""
        pass
