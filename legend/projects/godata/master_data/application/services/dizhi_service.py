from typing import List, Optional

from idp.projects.godata.master_data.domain.aggregate.dizhi import Dizhi
from idp.projects.godata.master_data.domain.repository.dizhi_repository import (
    DizhiRepository,
)
from idp.projects.godata.master_data.domain.value_objects.dizhi_combination import (
    DizhiCombination,
    DizhiCombinationFactory,
    DizhiRelationType,
    SanHeGroup,
)


class DizhiService:
    """地支应用服务 - 遵循单一职责原则和开闭原则"""

    def __init__(self, dizhi_repository: DizhiRepository):
        """依赖注入 - 遵循依赖倒置原则"""
        self._repository = dizhi_repository

    async def get_dizhi_by_name(self, name: str) -> Optional[Dizhi]:
        """根据名称获取地支"""
        return await self._repository.get_by_name(name)

    async def get_dizhi_by_order(self, order: int) -> Optional[Dizhi]:
        """根据序号获取地支"""
        return await self._repository.get_by_order(order)

    async def get_all_dizhis(self) -> List[Dizhi]:
        """获取所有地支"""
        return await self._repository.get_all()

    async def get_dizhis_by_wuxing(self, wu_xing: str) -> List[Dizhi]:
        """根据五行属性获取地支列表"""
        return await self._repository.get_by_wuxing(wu_xing)

    async def get_yang_dizhis(self) -> List[Dizhi]:
        """获取所有阳支"""
        return await self._repository.get_by_yin_yang('阳')

    async def get_yin_dizhis(self) -> List[Dizhi]:
        """获取所有阴支"""
        return await self._repository.get_by_yin_yang('阴')

    async def get_dizhis_by_animal(self, animal: str) -> List[Dizhi]:
        """根据生肖获取地支列表"""
        return await self._repository.get_by_animal(animal)

    async def create_dizhi(self, name: str, order: int, animal: str, yin_yang: str,
                           wu_xing: str, na_yin: str, description: str,
                           cang_gan: Optional[List[str]] = None, direction: Optional[str] = None,
                           time_period: Optional[str] = None, month: Optional[str] = None,
                           season: Optional[str] = None, color: Optional[str] = None,
                           taste: Optional[str] = None, emotion: Optional[str] = None,
                           organ: Optional[str] = None, body_part: Optional[str] = None,
                           sound: Optional[str] = None, element_strength: Optional[str] = None) -> Dizhi:
        """创建新的地支"""
        dizhi = Dizhi(
            id=f"dizhi_{order}",
            name=name,
            order=order,
            animal=animal,
            yin_yang=yin_yang,
            wu_xing=wu_xing,
            na_yin=na_yin,
            description=description,
            cang_gan=cang_gan or [],
            direction=direction,
            time_period=time_period,
            month=month,
            season=season,
            color=color,
            taste=taste,
            emotion=emotion,
            organ=organ,
            body_part=body_part,
            sound=sound,
            element_strength=element_strength
        )
        return await self._repository.save(dizhi)

    async def check_liu_he(self, dizhi1_name: str, dizhi2_name: str) -> Optional[DizhiCombination]:
        """检查两个地支是否六合"""
        try:
            return DizhiCombinationFactory.create_liu_he(dizhi1_name, dizhi2_name)
        except ValueError:
            return None

    async def check_liu_chong(self, dizhi1_name: str, dizhi2_name: str) -> Optional[DizhiCombination]:
        """检查两个地支是否六冲"""
        try:
            return DizhiCombinationFactory.create_liu_chong(dizhi1_name, dizhi2_name)
        except ValueError:
            return None

    async def check_san_he(self, dizhi1_name: str, dizhi2_name: str) -> Optional[DizhiCombination]:
        """检查两个地支是否三合"""
        try:
            return DizhiCombinationFactory.create_san_he(dizhi1_name, dizhi2_name)
        except ValueError:
            return None

    async def create_san_he_group(self, dizhi1_name: str, dizhi2_name: str, dizhi3_name: str) -> Optional[SanHeGroup]:
        """创建三合局"""
        try:
            return SanHeGroup.create(dizhi1_name, dizhi2_name, dizhi3_name)
        except ValueError:
            return None

    async def get_liu_he_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支六合的地支列表"""
        return await self._repository.get_liu_he_partners(dizhi_name)

    async def get_liu_chong_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支六冲的地支列表"""
        return await self._repository.get_liu_chong_partners(dizhi_name)

    async def get_san_he_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支三合的地支列表"""
        return await self._repository.get_san_he_partners(dizhi_name)

    async def get_next_dizhi_cycle(self, current_dizhi_name: str, steps: int = 1) -> Optional[Dizhi]:
        """获取指定步数后的地支（循环）"""
        current_dizhi = await self._repository.get_by_name(current_dizhi_name)
        if not current_dizhi:
            return None

        target_order = ((current_dizhi.order - 1 + steps) % 12) + 1
        return await self._repository.get_by_order(target_order)

    async def get_all_san_he_groups(self) -> List[SanHeGroup]:
        """获取所有三合局"""
        san_he_groups = [
            ('寅', '午', '戌'),  # 火局
            ('亥', '卯', '未'),  # 木局
            ('巳', '酉', '丑'),  # 金局
            ('申', '子', '辰')   # 水局
        ]

        groups = []
        for group in san_he_groups:
            try:
                print(f"尝试创建三合局: {group}")  # 调试信息
                san_he_group = SanHeGroup.create(group[0], group[1], group[2])
                groups.append(san_he_group)
                print(f"成功创建三合局: {san_he_group.get_description()}")  # 调试信息
            except ValueError as e:
                print(f"创建三合局失败: {group}, 错误: {e}")  # 调试信息
                continue

        print(f"总共创建了 {len(groups)} 个三合局")  # 调试信息
        return groups

    async def get_dizhi_relationships(self, dizhi_name: str) -> dict:
        """获取指定地支的所有关系"""
        dizhi = await self._repository.get_by_name(dizhi_name)
        if not dizhi:
            return {}

        liu_he_partners = await self.get_liu_he_partners(dizhi_name)
        liu_chong_partners = await self.get_liu_chong_partners(dizhi_name)
        san_he_partners = await self.get_san_he_partners(dizhi_name)

        return {
            "dizhi": dizhi,
            "liu_he_partners": liu_he_partners,
            "liu_chong_partners": liu_chong_partners,
            "san_he_partners": san_he_partners,
            "san_he_element": dizhi.get_san_he_element()
        }
