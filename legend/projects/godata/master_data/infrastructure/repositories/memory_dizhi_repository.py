from typing import Dict, List, Optional

from idp.projects.godata.master_data.domain.aggregate.dizhi import Dizhi
from idp.projects.godata.master_data.domain.repository.dizhi_repository import (
    DizhiRepository,
)


class MemoryDizhiRepository(DizhiRepository):
    """地支内存仓储实现 - 用于演示和测试"""

    def __init__(self):
        self._dizhis: Dict[str, Dizhi] = {}
        self._name_to_id: Dict[str, str] = {}
        self._order_to_id: Dict[int, str] = {}
        self._animal_to_ids: Dict[str, List[str]] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        """初始化默认的地支数据"""
        default_dizhis = [
            {
                "id": "dizhi_1", "name": "子", "order": 1, "animal": "鼠", "yin_yang": "阳",
                "wu_xing": "水", "na_yin": "海中金",
                "description": "子水，阳水，代表冬季的开始，象征智慧和潜藏",
                "cang_gan": ["癸"],
                "direction": "北",
                "time_period": "23:00-01:00",
                "month": "十一月",
                "season": "冬",
                "color": "黑",
                "taste": "咸",
                "emotion": "恐",
                "organ": "肾膀胱",
                "body_part": "骨",
                "sound": "羽",
                "element_strength": "旺",
                "he_luo_number": 9
            },
            {
                "id": "dizhi_2", "name": "丑", "order": 2, "animal": "牛", "yin_yang": "阴",
                "wu_xing": "土", "na_yin": "海中金",
                "description": "丑土，阴土，代表冬季的延续，象征包容和滋养",
                "cang_gan": ["己", "辛", "癸"],
                "direction": "东北",
                "time_period": "01:00-03:00",
                "month": "十二月",
                "season": "冬",
                "color": "黄",
                "taste": "甘",
                "emotion": "思",
                "organ": "脾胃",
                "body_part": "肉",
                "sound": "宫",
                "element_strength": "相",
                "he_luo_number": 8
            },
            {
                "id": "dizhi_3", "name": "寅", "order": 3, "animal": "虎", "yin_yang": "阳",
                "wu_xing": "木", "na_yin": "炉中火",
                "description": "寅木，阳木，代表春季的开始，象征新生和成长",
                "cang_gan": ["甲", "丙", "戊"],
                "direction": "东北",
                "time_period": "03:00-05:00",
                "month": "正月",
                "season": "春",
                "color": "青",
                "taste": "酸",
                "emotion": "怒",
                "organ": "肝胆",
                "body_part": "筋",
                "sound": "角",
                "element_strength": "旺",
                "he_luo_number": 7
            },
            {
                "id": "dizhi_4", "name": "卯", "order": 4, "animal": "兔", "yin_yang": "阴",
                "wu_xing": "木", "na_yin": "炉中火",
                "description": "卯木，阴木，代表春季的延续，象征柔韧和适应",
                "cang_gan": ["乙"],
                "direction": "东",
                "time_period": "05:00-07:00",
                "month": "二月",
                "season": "春",
                "color": "青",
                "taste": "酸",
                "emotion": "怒",
                "organ": "肝胆",
                "body_part": "筋",
                "sound": "角",
                "element_strength": "相",
                "he_luo_number": 6
            },
            {
                "id": "dizhi_5", "name": "辰", "order": 5, "animal": "龙", "yin_yang": "阳",
                "wu_xing": "土", "na_yin": "白蜡金",
                "description": "辰土，阳土，代表长夏的开始，象征稳定和承载",
                "cang_gan": ["戊", "乙", "癸"],
                "direction": "东南",
                "time_period": "07:00-09:00",
                "month": "三月",
                "season": "长夏",
                "color": "黄",
                "taste": "甘",
                "emotion": "思",
                "organ": "脾胃",
                "body_part": "肉",
                "sound": "宫",
                "element_strength": "旺",
                "he_luo_number": 5
            },
            {
                "id": "dizhi_6", "name": "巳", "order": 6, "animal": "蛇", "yin_yang": "阴",
                "wu_xing": "火", "na_yin": "白蜡金",
                "description": "巳火，阴火，代表夏季的开始，象征热情和活力",
                "cang_gan": ["丙", "庚", "戊"],
                "direction": "东南",
                "time_period": "09:00-11:00",
                "month": "四月",
                "season": "夏",
                "color": "红",
                "taste": "苦",
                "emotion": "喜",
                "organ": "心小肠",
                "body_part": "脉",
                "sound": "徵",
                "element_strength": "旺",
                "he_luo_number": 4
            },
            {
                "id": "dizhi_7", "name": "午", "order": 7, "animal": "马", "yin_yang": "阳",
                "wu_xing": "火", "na_yin": "杨柳木",
                "description": "午火，阳火，代表夏季的延续，象征温暖和光明",
                "cang_gan": ["丁", "己"],
                "direction": "南",
                "time_period": "11:00-13:00",
                "month": "五月",
                "season": "夏",
                "color": "红",
                "taste": "苦",
                "emotion": "喜",
                "organ": "心小肠",
                "body_part": "脉",
                "sound": "徵",
                "element_strength": "相",
                "he_luo_number": 9
            },
            {
                "id": "dizhi_8", "name": "未", "order": 8, "animal": "羊", "yin_yang": "阴",
                "wu_xing": "土", "na_yin": "杨柳木",
                "description": "未土，阴土，代表长夏的延续，象征包容和滋养",
                "cang_gan": ["己", "丁", "乙"],
                "direction": "西南",
                "time_period": "13:00-15:00",
                "month": "六月",
                "season": "长夏",
                "color": "黄",
                "taste": "甘",
                "emotion": "思",
                "organ": "脾胃",
                "body_part": "肉",
                "sound": "宫",
                "element_strength": "相",
                "he_luo_number": 8
            },
            {
                "id": "dizhi_9", "name": "申", "order": 9, "animal": "猴", "yin_yang": "阳",
                "wu_xing": "金", "na_yin": "井泉水",
                "description": "申金，阳金，代表秋季的开始，象征收获和坚韧",
                "cang_gan": ["庚", "壬", "戊"],
                "direction": "西南",
                "time_period": "15:00-17:00",
                "month": "七月",
                "season": "秋",
                "color": "白",
                "taste": "辛",
                "emotion": "悲",
                "organ": "肺大肠",
                "body_part": "皮毛",
                "sound": "商",
                "element_strength": "旺",
                "he_luo_number": 7
            },
            {
                "id": "dizhi_10", "name": "酉", "order": 10, "animal": "鸡", "yin_yang": "阴",
                "wu_xing": "金", "na_yin": "井泉水",
                "description": "酉金，阴金，代表秋季的延续，象征精致和贵重",
                "cang_gan": ["辛"],
                "direction": "西",
                "time_period": "17:00-19:00",
                "month": "八月",
                "season": "秋",
                "color": "白",
                "taste": "辛",
                "emotion": "悲",
                "organ": "肺大肠",
                "body_part": "皮毛",
                "sound": "商",
                "element_strength": "相",
                "he_luo_number": 6
            },
            {
                "id": "dizhi_11", "name": "戌", "order": 11, "animal": "狗", "yin_yang": "阳",
                "wu_xing": "土", "na_yin": "平地木",
                "description": "戌土，阳土，代表长夏的结束，象征稳定和承载",
                "cang_gan": ["戊", "辛", "丁"],
                "direction": "西北",
                "time_period": "19:00-21:00",
                "month": "九月",
                "season": "长夏",
                "color": "黄",
                "taste": "甘",
                "emotion": "思",
                "organ": "脾胃",
                "body_part": "肉",
                "sound": "宫",
                "element_strength": "休",
                "he_luo_number": 5
            },
            {
                "id": "dizhi_12", "name": "亥", "order": 12, "animal": "猪", "yin_yang": "阴",
                "wu_xing": "水", "na_yin": "平地木",
                "description": "亥水，阴水，代表冬季的结束，象征智慧和流动",
                "cang_gan": ["壬", "甲"],
                "direction": "西北",
                "time_period": "21:00-23:00",
                "month": "十月",
                "season": "冬",
                "color": "黑",
                "taste": "咸",
                "emotion": "恐",
                "organ": "肾膀胱",
                "body_part": "骨",
                "sound": "羽",
                "element_strength": "相",
                "he_luo_number": 4
            }
        ]

        for data in default_dizhis:
            dizhi = Dizhi(**data)
            self._dizhis[dizhi.id] = dizhi
            self._name_to_id[dizhi.name] = dizhi.id
            self._order_to_id[dizhi.order] = dizhi.id

            # 建立生肖到ID的映射
            if dizhi.animal not in self._animal_to_ids:
                self._animal_to_ids[dizhi.animal] = []
            self._animal_to_ids[dizhi.animal].append(dizhi.id)

    async def get_by_id(self, dizhi_id: str) -> Optional[Dizhi]:
        """根据ID获取地支"""
        return self._dizhis.get(dizhi_id)

    async def get_by_name(self, name: str) -> Optional[Dizhi]:
        """根据名称获取地支"""
        dizhi_id = self._name_to_id.get(name)
        return self._dizhis.get(dizhi_id) if dizhi_id else None

    async def get_by_order(self, order: int) -> Optional[Dizhi]:
        """根据序号获取地支"""
        dizhi_id = self._order_to_id.get(order)
        return self._dizhis.get(dizhi_id) if dizhi_id else None

    async def get_all(self) -> List[Dizhi]:
        """获取所有地支"""
        return list(self._dizhis.values())

    async def get_by_wuxing(self, wu_xing: str) -> List[Dizhi]:
        """根据五行属性获取地支列表"""
        return [dizhi for dizhi in self._dizhis.values()
                if dizhi.wu_xing == wu_xing]

    async def get_by_yin_yang(self, yin_yang: str) -> List[Dizhi]:
        """根据阴阳属性获取地支列表"""
        return [dizhi for dizhi in self._dizhis.values()
                if dizhi.yin_yang == yin_yang]

    async def get_by_animal(self, animal: str) -> List[Dizhi]:
        """根据生肖获取地支列表"""
        dizhi_ids = self._animal_to_ids.get(animal, [])
        return [self._dizhis[dizhi_id] for dizhi_id in dizhi_ids
                if dizhi_id in self._dizhis]

    async def get_liu_he_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支六合的地支列表"""
        dizhi = await self.get_by_name(dizhi_name)
        if not dizhi:
            return []

        liu_he_partner_name = dizhi.get_liu_he_partner()
        if liu_he_partner_name:
            partner = await self.get_by_name(liu_he_partner_name)
            return [partner] if partner else []
        return []

    async def get_liu_chong_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支六冲的地支列表"""
        dizhi = await self.get_by_name(dizhi_name)
        if not dizhi:
            return []

        liu_chong_partner_name = dizhi.get_liu_chong_partner()
        if liu_chong_partner_name:
            partner = await self.get_by_name(liu_chong_partner_name)
            return [partner] if partner else []
        return []

    async def get_san_he_partners(self, dizhi_name: str) -> List[Dizhi]:
        """获取与指定地支三合的地支列表"""
        dizhi = await self.get_by_name(dizhi_name)
        if not dizhi:
            return []

        san_he_partner_names = dizhi.get_san_he_partners()
        partners = []
        for partner_name in san_he_partner_names:
            partner = await self.get_by_name(partner_name)
            if partner:
                partners.append(partner)

        return partners

    async def save(self, dizhi: Dizhi) -> Dizhi:
        """保存地支"""
        self._dizhis[dizhi.id] = dizhi
        self._name_to_id[dizhi.name] = dizhi.id
        self._order_to_id[dizhi.order] = dizhi.id

        # 更新生肖映射
        if dizhi.animal not in self._animal_to_ids:
            self._animal_to_ids[dizhi.animal] = []
        if dizhi.id not in self._animal_to_ids[dizhi.animal]:
            self._animal_to_ids[dizhi.animal].append(dizhi.id)

        return dizhi

    async def delete(self, dizhi_id: str) -> bool:
        """删除地支"""
        if dizhi_id not in self._dizhis:
            return False

        dizhi = self._dizhis[dizhi_id]
        del self._dizhis[dizhi_id]
        del self._name_to_id[dizhi.name]
        del self._order_to_id[dizhi.order]

        # 更新生肖映射
        if dizhi.animal in self._animal_to_ids:
            self._animal_to_ids[dizhi.animal] = [
                id for id in self._animal_to_ids[dizhi.animal] if id != dizhi_id
            ]

        return True
