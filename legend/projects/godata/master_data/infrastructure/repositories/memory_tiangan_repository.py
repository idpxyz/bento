from typing import Dict, List, Optional

from idp.projects.godata.master_data.domain.aggregate.tiangan import Tiangan
from idp.projects.godata.master_data.domain.repository.tiangan_repository import (
    TianganRepository,
)


class MemoryTianganRepository(TianganRepository):
    """天干内存仓储实现 - 用于演示和测试"""

    def __init__(self):
        self._tiangans: Dict[str, Tiangan] = {}
        self._name_to_id: Dict[str, str] = {}
        self._order_to_id: Dict[int, str] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        """初始化默认的天干数据"""
        default_tiangans = [
            {
                "id": "tiangan_1", "name": "甲", "order": 1, "yin_yang": "阳",
                "wu_xing": "木", "na_yin": "海中金",
                "description": "甲木，阳木，代表春季的开始，象征新生和成长",
                "he_hua": "甲己合土",
                "direction": "东",
                "season": "春",
                "color": "青",
                "taste": "酸",
                "emotion": "怒",
                "organ": "肝胆",
                "body_part": "筋",
                "sound": "角",
                "he_luo_number": 9
            },
            {
                "id": "tiangan_2", "name": "乙", "order": 2, "yin_yang": "阴",
                "wu_xing": "木", "na_yin": "炉中火",
                "description": "乙木，阴木，代表春季的延续，象征柔韧和适应",
                "he_hua": "乙庚合金",
                "direction": "东",
                "season": "春",
                "color": "青",
                "taste": "酸",
                "emotion": "怒",
                "organ": "肝胆",
                "body_part": "筋",
                "sound": "角",
                "he_luo_number": 8
            },
            {
                "id": "tiangan_3", "name": "丙", "order": 3, "yin_yang": "阳",
                "wu_xing": "火", "na_yin": "白蜡金",
                "description": "丙火，阳火，代表夏季的开始，象征热情和活力",
                "he_hua": "丙辛合水",
                "direction": "南",
                "season": "夏",
                "color": "红",
                "taste": "苦",
                "emotion": "喜",
                "organ": "心小肠",
                "body_part": "脉",
                "sound": "徵",
                "he_luo_number": 7
            },
            {
                "id": "tiangan_4", "name": "丁", "order": 4, "yin_yang": "阴",
                "wu_xing": "火", "na_yin": "杨柳木",
                "description": "丁火，阴火，代表夏季的延续，象征温暖和光明",
                "he_hua": "丁壬合木",
                "direction": "南",
                "season": "夏",
                "color": "红",
                "taste": "苦",
                "emotion": "喜",
                "organ": "心小肠",
                "body_part": "脉",
                "sound": "徵",
                "he_luo_number": 6
            },
            {
                "id": "tiangan_5", "name": "戊", "order": 5, "yin_yang": "阳",
                "wu_xing": "土", "na_yin": "井泉水",
                "description": "戊土，阳土，代表长夏，象征稳定和承载",
                "he_hua": "戊癸合火",
                "direction": "中",
                "season": "长夏",
                "color": "黄",
                "taste": "甘",
                "emotion": "思",
                "organ": "脾胃",
                "body_part": "肉",
                "sound": "宫",
                "he_luo_number": 5
            },
            {
                "id": "tiangan_6", "name": "己", "order": 6, "yin_yang": "阴",
                "wu_xing": "土", "na_yin": "海中金",
                "description": "己土，阴土，代表长夏的延续，象征包容和滋养",
                "he_hua": "甲己合土",
                "direction": "中",
                "season": "长夏",
                "color": "黄",
                "taste": "甘",
                "emotion": "思",
                "organ": "脾胃",
                "body_part": "肉",
                "sound": "宫",
                "he_luo_number": 9
            },
            {
                "id": "tiangan_7", "name": "庚", "order": 7, "yin_yang": "阳",
                "wu_xing": "金", "na_yin": "炉中火",
                "description": "庚金，阳金，代表秋季的开始，象征收获和坚韧",
                "he_hua": "乙庚合金",
                "direction": "西",
                "season": "秋",
                "color": "白",
                "taste": "辛",
                "emotion": "悲",
                "organ": "肺大肠",
                "body_part": "皮毛",
                "sound": "商",
                "he_luo_number": 8
            },
            {
                "id": "tiangan_8", "name": "辛", "order": 8, "yin_yang": "阴",
                "wu_xing": "金", "na_yin": "白蜡金",
                "description": "辛金，阴金，代表秋季的延续，象征精致和贵重",
                "he_hua": "丙辛合水",
                "direction": "西",
                "season": "秋",
                "color": "白",
                "taste": "辛",
                "emotion": "悲",
                "organ": "肺大肠",
                "body_part": "皮毛",
                "sound": "商",
                "he_luo_number": 7
            },
            {
                "id": "tiangan_9", "name": "壬", "order": 9, "yin_yang": "阳",
                "wu_xing": "水", "na_yin": "杨柳木",
                "description": "壬水，阳水，代表冬季的开始，象征智慧和流动",
                "he_hua": "丁壬合木",
                "direction": "北",
                "season": "冬",
                "color": "黑",
                "taste": "咸",
                "emotion": "恐",
                "organ": "肾膀胱",
                "body_part": "骨",
                "sound": "羽",
                "he_luo_number": 6
            },
            {
                "id": "tiangan_10", "name": "癸", "order": 10, "yin_yang": "阴",
                "wu_xing": "水", "na_yin": "井泉水",
                "description": "癸水，阴水，代表冬季的延续，象征潜藏和滋养",
                "he_hua": "戊癸合火",
                "direction": "北",
                "season": "冬",
                "color": "黑",
                "taste": "咸",
                "emotion": "恐",
                "organ": "肾膀胱",
                "body_part": "骨",
                "sound": "羽",
                "he_luo_number": 5
            }
        ]

        for data in default_tiangans:
            tiangan = Tiangan(**data)
            self._tiangans[tiangan.id] = tiangan
            self._name_to_id[tiangan.name] = tiangan.id
            self._order_to_id[tiangan.order] = tiangan.id

    async def get_by_id(self, tiangan_id: str) -> Optional[Tiangan]:
        """根据ID获取天干"""
        return self._tiangans.get(tiangan_id)

    async def get_by_name(self, name: str) -> Optional[Tiangan]:
        """根据名称获取天干"""
        tiangan_id = self._name_to_id.get(name)
        return self._tiangans.get(tiangan_id) if tiangan_id else None

    async def get_by_order(self, order: int) -> Optional[Tiangan]:
        """根据序号获取天干"""
        tiangan_id = self._order_to_id.get(order)
        return self._tiangans.get(tiangan_id) if tiangan_id else None

    async def get_all(self) -> List[Tiangan]:
        """获取所有天干"""
        return list(self._tiangans.values())

    async def get_by_wuxing(self, wu_xing: str) -> List[Tiangan]:
        """根据五行属性获取天干列表"""
        return [tiangan for tiangan in self._tiangans.values()
                if tiangan.wu_xing == wu_xing]

    async def get_by_yin_yang(self, yin_yang: str) -> List[Tiangan]:
        """根据阴阳属性获取天干列表"""
        return [tiangan for tiangan in self._tiangans.values()
                if tiangan.yin_yang == yin_yang]

    async def save(self, tiangan: Tiangan) -> Tiangan:
        """保存天干"""
        self._tiangans[tiangan.id] = tiangan
        self._name_to_id[tiangan.name] = tiangan.id
        self._order_to_id[tiangan.order] = tiangan.id
        return tiangan

    async def delete(self, tiangan_id: str) -> bool:
        """删除天干"""
        if tiangan_id not in self._tiangans:
            return False

        tiangan = self._tiangans[tiangan_id]
        del self._tiangans[tiangan_id]
        del self._name_to_id[tiangan.name]
        del self._order_to_id[tiangan.order]
        return True
