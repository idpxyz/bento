from typing import List, Optional

from idp.projects.godata.master_data.domain.aggregate.tiangan import Tiangan
from idp.projects.godata.master_data.domain.repository.tiangan_repository import (
    TianganRepository,
)
from idp.projects.godata.master_data.domain.value_objects.tiangan_combination import (
    TianganCombination,
    WuXing,
)


class TianganService:
    """天干应用服务 - 遵循单一职责原则和开闭原则"""

    def __init__(self, tiangan_repository: TianganRepository):
        """依赖注入 - 遵循依赖倒置原则"""
        self._repository = tiangan_repository

    async def get_tiangan_by_name(self, name: str) -> Optional[Tiangan]:
        """根据名称获取天干"""
        return await self._repository.get_by_name(name)

    async def get_tiangan_by_order(self, order: int) -> Optional[Tiangan]:
        """根据序号获取天干"""
        return await self._repository.get_by_order(order)

    async def get_all_tiangans(self) -> List[Tiangan]:
        """获取所有天干"""
        return await self._repository.get_all()

    async def get_tiangans_by_wuxing(self, wu_xing: str) -> List[Tiangan]:
        """根据五行属性获取天干列表"""
        return await self._repository.get_by_wuxing(wu_xing)

    async def get_yang_tiangans(self) -> List[Tiangan]:
        """获取所有阳干"""
        return await self._repository.get_by_yin_yang('阳')

    async def get_yin_tiangans(self) -> List[Tiangan]:
        """获取所有阴干"""
        return await self._repository.get_by_yin_yang('阴')

    async def create_tiangan(self, name: str, order: int, yin_yang: str,
                             wu_xing: str, na_yin: str, description: str,
                             direction: Optional[str] = None, season: Optional[str] = None,
                             color: Optional[str] = None, taste: Optional[str] = None,
                             emotion: Optional[str] = None, organ: Optional[str] = None,
                             body_part: Optional[str] = None, sound: Optional[str] = None) -> Tiangan:
        """创建新的天干"""
        tiangan = Tiangan(
            id=f"tiangan_{order}",
            name=name,
            order=order,
            yin_yang=yin_yang,
            wu_xing=wu_xing,
            na_yin=na_yin,
            description=description,
            direction=direction,
            season=season,
            color=color,
            taste=taste,
            emotion=emotion,
            organ=organ,
            body_part=body_part,
            sound=sound
        )
        return await self._repository.save(tiangan)

    async def check_combination(self, tiangan1_name: str, tiangan2_name: str) -> Optional[TianganCombination]:
        """检查两个天干是否可以合化"""
        try:
            return TianganCombination.create(tiangan1_name, tiangan2_name)
        except ValueError:
            return None

    async def get_next_tiangan_cycle(self, current_tiangan_name: str, steps: int = 1) -> Optional[Tiangan]:
        """获取指定步数后的天干（循环）"""
        current_tiangan = await self._repository.get_by_name(current_tiangan_name)
        if not current_tiangan:
            return None

        target_order = ((current_tiangan.order - 1 + steps) % 10) + 1
        return await self._repository.get_by_order(target_order)

    async def get_compatible_tiangans(self, tiangan_name: str) -> List[Tiangan]:
        """获取与指定天干相合的天干列表"""
        target_tiangan = await self._repository.get_by_name(tiangan_name)
        if not target_tiangan:
            return []

        all_tiangans = await self._repository.get_all()
        compatible = []

        for tiangan in all_tiangans:
            if tiangan.is_compatible_with(target_tiangan):
                compatible.append(tiangan)

        return compatible
