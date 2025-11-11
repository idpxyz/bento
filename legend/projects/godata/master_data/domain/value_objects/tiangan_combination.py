from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class WuXing(Enum):
    """五行枚举"""
    JIN = "金"
    MU = "木"
    SHUI = "水"
    HUO = "火"
    TU = "土"


@dataclass(frozen=True)
class TianganCombination:
    """天干组合值对象 - 表示天干之间的合化关系"""

    first_tiangan: str
    second_tiangan: str
    he_hua_result: WuXing

    def __post_init__(self):
        """验证组合的有效性"""
        valid_combinations = {
            ('甲', '己'): WuXing.TU,
            ('乙', '庚'): WuXing.JIN,
            ('丙', '辛'): WuXing.SHUI,
            ('丁', '壬'): WuXing.MU,
            ('戊', '癸'): WuXing.HUO
        }

        combination = tuple(sorted([self.first_tiangan, self.second_tiangan]))
        if combination not in valid_combinations:
            raise ValueError(
                f"无效的天干组合: {self.first_tiangan} + {self.second_tiangan}")

        if valid_combinations[combination] != self.he_hua_result:
            raise ValueError(
                f"合化结果错误: {self.first_tiangan} + {self.second_tiangan} 应该合化为 {valid_combinations[combination].value}")

    @classmethod
    def create(cls, tiangan1: str, tiangan2: str) -> 'TianganCombination':
        """创建天干组合"""
        valid_combinations = {
            ('甲', '己'): WuXing.TU,
            ('乙', '庚'): WuXing.JIN,
            ('丙', '辛'): WuXing.SHUI,
            ('丁', '壬'): WuXing.MU,
            ('戊', '癸'): WuXing.HUO
        }

        combination = tuple(sorted([tiangan1, tiangan2]))
        if combination not in valid_combinations:
            raise ValueError(f"无效的天干组合: {tiangan1} + {tiangan2}")

        return cls(tiangan1, tiangan2, valid_combinations[combination])

    def get_description(self) -> str:
        """获取组合描述"""
        return f"{self.first_tiangan}{self.second_tiangan}合{self.he_hua_result.value}"

    def is_valid_combination(self) -> bool:
        """判断是否为有效组合"""
        return True  # 如果对象能创建成功，说明是有效组合
