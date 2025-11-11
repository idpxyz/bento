from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class DizhiRelationType(Enum):
    """地支关系类型枚举"""
    LIU_HE = "六合"
    LIU_CHONG = "六冲"
    SAN_HE = "三合"


class WuXing(Enum):
    """五行枚举"""
    JIN = "金"
    MU = "木"
    SHUI = "水"
    HUO = "火"
    TU = "土"


@dataclass(frozen=True)
class DizhiCombination:
    """地支组合值对象 - 表示地支之间的关系"""

    first_dizhi: str
    second_dizhi: str
    relation_type: DizhiRelationType
    description: str

    def __post_init__(self):
        """验证组合的有效性"""
        if not self._is_valid_combination():
            raise ValueError(
                f"无效的地支组合: {self.first_dizhi} + {self.second_dizhi}")

    def _is_valid_combination(self) -> bool:
        """验证组合是否有效"""
        if self.relation_type == DizhiRelationType.LIU_HE:
            return self._is_valid_liu_he()
        elif self.relation_type == DizhiRelationType.LIU_CHONG:
            return self._is_valid_liu_chong()
        elif self.relation_type == DizhiRelationType.SAN_HE:
            return self._is_valid_san_he()
        return False

    def _is_valid_liu_he(self) -> bool:
        """验证六合关系"""
        liu_he_pairs = {
            ('子', '丑'), ('寅', '亥'), ('卯', '戌'),
            ('辰', '酉'), ('巳', '申'), ('午', '未')
        }
        combination = tuple(sorted([self.first_dizhi, self.second_dizhi]))
        return combination in liu_he_pairs

    def _is_valid_liu_chong(self) -> bool:
        """验证六冲关系"""
        liu_chong_pairs = {
            ('子', '午'), ('丑', '未'), ('寅', '申'),
            ('卯', '酉'), ('辰', '戌'), ('巳', '亥')
        }
        combination = tuple(sorted([self.first_dizhi, self.second_dizhi]))
        return combination in liu_chong_pairs

    def _is_valid_san_he(self) -> bool:
        """验证三合关系"""
        san_he_groups = [
            ['寅', '午', '戌'],  # 火局
            ['亥', '卯', '未'],  # 木局
            ['巳', '酉', '丑'],  # 金局
            ['申', '子', '辰']   # 水局
        ]

        for group in san_he_groups:
            if self.first_dizhi in group and self.second_dizhi in group:
                return True
        return False


@dataclass(frozen=True)
class SanHeGroup:
    """三合局值对象"""

    dizhis: Tuple[str, str, str]
    element: WuXing
    description: str

    def __post_init__(self):
        """验证三合局的有效性"""
        if not self._is_valid_san_he_group():
            raise ValueError(f"无效的三合局: {self.dizhis}")

    def _is_valid_san_he_group(self) -> bool:
        """验证三合局是否有效"""
        valid_groups = [
            ('寅', '午', '戌'),  # 火局
            ('亥', '卯', '未'),  # 木局
            ('巳', '酉', '丑'),  # 金局
            ('申', '子', '辰')   # 水局
        ]

        sorted_dizhis = tuple(sorted(self.dizhis))
        for valid_group in valid_groups:
            if tuple(sorted(valid_group)) == sorted_dizhis:
                return True
        return False

    @classmethod
    def create(cls, dizhi1: str, dizhi2: str, dizhi3: str) -> 'SanHeGroup':
        """创建三合局"""
        # 修复element_map，使用正确的排序顺序
        element_map = {
            ('午', '寅', '戌'): WuXing.HUO,   # 火局 - 排序后是午寅戌
            ('亥', '卯', '未'): WuXing.MU,    # 木局 - 排序后是亥卯未
            ('丑', '巳', '酉'): WuXing.JIN,   # 金局 - 排序后是丑巳酉
            ('子', '申', '辰'): WuXing.SHUI   # 水局 - 排序后是子申辰
        }

        sorted_dizhis = tuple(sorted([dizhi1, dizhi2, dizhi3]))
        print(f"排序后的地支: {sorted_dizhis}")  # 调试信息
        print(f"element_map的键: {list(element_map.keys())}")  # 调试信息

        element = element_map.get(sorted_dizhis)

        if not element:
            raise ValueError(f"无效的三合局: {dizhi1} + {dizhi2} + {dizhi3}")

        description_map = {
            WuXing.HUO: "火局",
            WuXing.MU: "木局",
            WuXing.JIN: "金局",
            WuXing.SHUI: "水局"
        }

        return cls(
            dizhis=(dizhi1, dizhi2, dizhi3),
            element=element,
            description=description_map[element]
        )

    def get_description(self) -> str:
        """获取三合局描述"""
        return f"{self.dizhis[0]}{self.dizhis[1]}{self.dizhis[2]}三合{self.element.value}局"


class DizhiCombinationFactory:
    """地支组合工厂类"""

    @staticmethod
    def create_liu_he(dizhi1: str, dizhi2: str) -> DizhiCombination:
        """创建六合关系"""
        liu_he_descriptions = {
            ('子', '丑'): "子丑合土",
            ('寅', '亥'): "寅亥合木",
            ('卯', '戌'): "卯戌合火",
            ('辰', '酉'): "辰酉合金",
            ('巳', '申'): "巳申合水",
            ('午', '未'): "午未合土"
        }

        combination = tuple(sorted([dizhi1, dizhi2]))
        description = liu_he_descriptions.get(combination)

        if not description:
            raise ValueError(f"无效的六合组合: {dizhi1} + {dizhi2}")

        return DizhiCombination(
            first_dizhi=dizhi1,
            second_dizhi=dizhi2,
            relation_type=DizhiRelationType.LIU_HE,
            description=description
        )

    @staticmethod
    def create_liu_chong(dizhi1: str, dizhi2: str) -> DizhiCombination:
        """创建六冲关系"""
        liu_chong_descriptions = {
            ('子', '午'): "子午相冲",
            ('丑', '未'): "丑未相冲",
            ('寅', '申'): "寅申相冲",
            ('卯', '酉'): "卯酉相冲",
            ('辰', '戌'): "辰戌相冲",
            ('巳', '亥'): "巳亥相冲"
        }

        combination = tuple(sorted([dizhi1, dizhi2]))
        description = liu_chong_descriptions.get(combination)

        if not description:
            raise ValueError(f"无效的六冲组合: {dizhi1} + {dizhi2}")

        return DizhiCombination(
            first_dizhi=dizhi1,
            second_dizhi=dizhi2,
            relation_type=DizhiRelationType.LIU_CHONG,
            description=description
        )

    @staticmethod
    def create_san_he(dizhi1: str, dizhi2: str) -> DizhiCombination:
        """创建三合关系"""
        return DizhiCombination(
            first_dizhi=dizhi1,
            second_dizhi=dizhi2,
            relation_type=DizhiRelationType.SAN_HE,
            description=f"{dizhi1}与{dizhi2}三合"
        )
