from abc import ABC, abstractmethod
from typing import List, Optional

from idp.projects.godata.master_data.domain.aggregate.dizhi import Dizhi


class DizhiRepository(ABC):
    """地支仓储接口 - 遵循依赖倒置原则"""

    @abstractmethod
    async def get_by_id(self, dizhi_id: str) -> Optional[Dizhi]:
        """根据ID获取地支"""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Dizhi]:
        """根据名称获取地支"""
        pass

    @abstractmethod
    async def get_by_order(self, order: int) -> Optional[Dizhi]:
        """根据序号获取地支"""
        pass

    @abstractmethod
    async def get_all(self) -> List[Dizhi]:
        """获取所有地支"""
        pass

    @abstractmethod
    async def get_by_wuxing(self, wu_xing: str) -> List[Dizhi]:
        """根据五行属性获取地支列表"""
        pass

    @abstractmethod
    async def get_by_yin_yang(self, yin_yang: str) -> List[Dizhi]:
        """根据阴阳属性获取地支列表"""
        pass

    @abstractmethod
    async def get_by_animal(self, animal: str) -> List[Dizhi]:
        """根据生肖获取地支列表"""
        pass

    @abstractmethod
    async def get_liu_he_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支六合的地支列表"""
        pass

    @abstractmethod
    async def get_liu_chong_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支六冲的地支列表"""
        pass

    @abstractmethod
    async def get_san_he_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支三合的地支列表"""
        pass

    @abstractmethod
    async def save(self, dizhi: Dizhi) -> Dizhi:
        """保存地支"""
        pass

    @abstractmethod
    async def delete(self, dizhi_id: str) -> bool:
        """删除地支"""
        pass
