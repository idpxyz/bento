"""
八卦纳甲映射系统测试
"""

import os
import sys
import unittest
from pathlib import Path

from idp.projects.godata.ganzi_utils.trigram_najia import (
    Direction,
    HeavenlyStem,
    NajiaCalculator,
    NajiaMapping,
    Trigram,
)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestNajiaMapping(unittest.TestCase):
    """纳甲映射测试类"""

    def setUp(self):
        """测试前准备"""
        self.mapping = NajiaMapping()
        self.calculator = NajiaCalculator()

    def test_trigram_to_stems_mapping(self):
        """测试八卦到天干的映射"""
        # 测试乾卦
        stems = self.mapping.get_stems_for_trigram(Trigram.QIAN)
        self.assertEqual(len(stems), 2)
        self.assertIn(HeavenlyStem.JIA, stems)
        self.assertIn(HeavenlyStem.REN, stems)

        # 测试坤卦
        stems = self.mapping.get_stems_for_trigram(Trigram.KUN)
        self.assertEqual(len(stems), 2)
        self.assertIn(HeavenlyStem.YI, stems)
        self.assertIn(HeavenlyStem.GUI, stems)

        # 测试单天干卦
        stems = self.mapping.get_stems_for_trigram(Trigram.ZHEN)
        self.assertEqual(len(stems), 1)
        self.assertIn(HeavenlyStem.GENG, stems)

    def test_stem_to_trigram_mapping(self):
        """测试天干到八卦的映射"""
        # 测试甲对应乾
        trigram = self.mapping.get_trigram_for_stem(HeavenlyStem.JIA)
        self.assertEqual(trigram, Trigram.QIAN)

        # 测试庚对应震
        trigram = self.mapping.get_trigram_for_stem(HeavenlyStem.GENG)
        self.assertEqual(trigram, Trigram.ZHEN)

        # 测试不存在的天干
        trigram = self.mapping.get_trigram_for_stem(HeavenlyStem.JIA)  # 甲已存在
        self.assertIsNotNone(trigram)

    def test_trigram_directions(self):
        """测试八卦方位"""
        # 测试坎居北方
        direction = self.mapping.get_direction_for_trigram(Trigram.KAN)
        self.assertEqual(direction, Direction.NORTH)

        # 测试离居南方
        direction = self.mapping.get_direction_for_trigram(Trigram.LI)
        self.assertEqual(direction, Direction.SOUTH)

        # 测试震居东方
        direction = self.mapping.get_direction_for_trigram(Trigram.ZHEN)
        self.assertEqual(direction, Direction.EAST)

    def test_trigram_symbols(self):
        """测试八卦符号"""
        # 测试乾卦符号
        symbol = self.mapping.get_trigram_symbol(Trigram.QIAN)
        self.assertEqual(symbol, "☰")

        # 测试坤卦符号
        symbol = self.mapping.get_trigram_symbol(Trigram.KUN)
        self.assertEqual(symbol, "☷")

        # 测试坎卦符号
        symbol = self.mapping.get_trigram_symbol(Trigram.KAN)
        self.assertEqual(symbol, "☵")

    def test_complete_mapping(self):
        """测试完整映射"""
        mapping_data = self.mapping.get_complete_mapping()

        # 检查所有八卦都存在
        self.assertEqual(len(mapping_data), 8)

        # 检查乾卦的完整信息
        qian_data = mapping_data["乾"]
        self.assertEqual(qian_data["symbol"], "☰")
        self.assertEqual(qian_data["stems"], ["甲", "壬"])
        self.assertEqual(qian_data["direction"], "西北")

    def test_circular_order(self):
        """测试循环顺序"""
        circular_order = self.mapping.get_circular_order()

        # 检查顺序正确性
        self.assertEqual(circular_order[0], Trigram.KAN)   # 北方
        self.assertEqual(circular_order[1], Trigram.LI)    # 南方
        self.assertEqual(circular_order[2], Trigram.DUI)   # 西方
        self.assertEqual(circular_order[3], Trigram.XUN)   # 东南

    def test_trigram_relationships(self):
        """测试八卦关系计算"""
        # 测试对冲关系
        relationship = self.calculator.calculate_trigram_relationship(
            Trigram.KAN, Trigram.LI
        )
        self.assertEqual(relationship, "对冲")

        # 测试同位关系
        relationship = self.calculator.calculate_trigram_relationship(
            Trigram.KAN, Trigram.KAN
        )
        self.assertEqual(relationship, "同位")

    def test_all_mappings_consistency(self):
        """测试所有映射的一致性"""
        # 检查每个天干都有对应的八卦
        all_stems = set()
        for trigram in Trigram:
            stems = self.mapping.get_stems_for_trigram(trigram)
            all_stems.update(stems)

        # 检查每个天干都能找到对应的八卦
        for stem in HeavenlyStem:
            trigram = self.mapping.get_trigram_for_stem(stem)
            self.assertIsNotNone(trigram, f"天干{stem.value}没有对应的八卦")

    def test_direction_consistency(self):
        """测试方位一致性"""
        # 检查每个八卦都有方位
        for trigram in Trigram:
            direction = self.mapping.get_direction_for_trigram(trigram)
            self.assertIsNotNone(direction, f"八卦{trigram.value}没有方位")

    def test_symbol_consistency(self):
        """测试符号一致性"""
        # 检查每个八卦都有符号
        for trigram in Trigram:
            symbol = self.mapping.get_trigram_symbol(trigram)
            self.assertIsNotNone(symbol, f"八卦{trigram.value}没有符号")
            self.assertNotEqual(symbol, "", f"八卦{trigram.value}符号为空")


class TestNajiaCalculator(unittest.TestCase):
    """纳甲计算器测试类"""

    def setUp(self):
        """测试前准备"""
        self.calculator = NajiaCalculator()

    def test_opposite_directions(self):
        """测试对冲方位判断"""
        # 测试南北对冲
        self.assertTrue(
            self.calculator._are_opposite_directions(
                Direction.NORTH, Direction.SOUTH
            )
        )

        # 测试东西对冲
        self.assertTrue(
            self.calculator._are_opposite_directions(
                Direction.EAST, Direction.WEST
            )
        )

        # 测试非对冲
        self.assertFalse(
            self.calculator._are_opposite_directions(
                Direction.NORTH, Direction.EAST
            )
        )

    def test_adjacent_directions(self):
        """测试相邻方位判断"""
        # 测试相邻方位
        self.assertTrue(
            self.calculator._are_adjacent_directions(
                Direction.NORTH, Direction.NORTHEAST
            )
        )

        # 测试非相邻方位
        self.assertFalse(
            self.calculator._are_adjacent_directions(
                Direction.NORTH, Direction.SOUTH
            )
        )


def run_performance_test():
    """运行性能测试"""
    print("运行性能测试...")

    mapping = NajiaMapping()
    calculator = NajiaCalculator()

    import time

    # 测试映射查询性能
    start_time = time.time()
    for _ in range(10000):
        for trigram in Trigram:
            stems = mapping.get_stems_for_trigram(trigram)
            direction = mapping.get_direction_for_trigram(trigram)
    end_time = time.time()

    print(f"10000次映射查询耗时: {end_time - start_time:.4f}秒")

    # 测试关系计算性能
    start_time = time.time()
    for _ in range(10000):
        for trigram1 in Trigram:
            for trigram2 in Trigram:
                relationship = calculator.calculate_trigram_relationship(
                    trigram1, trigram2)
    end_time = time.time()

    print(f"10000次关系计算耗时: {end_time - start_time:.4f}秒")


if __name__ == "__main__":
    # 运行单元测试
    print("运行单元测试...")
    unittest.main(verbosity=2, exit=False)

    # 运行性能测试
    run_performance_test()

    print("\n所有测试完成！")
