"""
八卦纳甲映射系统使用示例

演示如何使用纳甲映射系统进行各种计算和查询
"""

import os
import sys
from pathlib import Path

from trigram_najia import (
    Direction,
    HeavenlyStem,
    NajiaCalculator,
    NajiaMapping,
    Trigram,
)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入模块
sys.path.insert(0, str(project_root / "src"))


def basic_mapping_examples():
    """基础映射示例"""
    print("=" * 50)
    print("基础映射示例")
    print("=" * 50)

    mapping = NajiaMapping()

    # 1. 查询八卦对应的天干
    print("1. 八卦对应的天干:")
    for trigram in Trigram:
        stems = mapping.get_stems_for_trigram(trigram)
        stem_names = [stem.value for stem in stems]
        symbol = mapping.get_trigram_symbol(trigram)
        print(f"   {trigram.value}（{symbol}）→ {', '.join(stem_names)}")

    print()

    # 2. 查询天干对应的八卦
    print("2. 天干对应的八卦:")
    for stem in HeavenlyStem:
        trigram = mapping.get_trigram_for_stem(stem)
        if trigram:
            symbol = mapping.get_trigram_symbol(trigram)
            print(f"   {stem.value} → {trigram.value}（{symbol}）")

    print()

    # 3. 查询八卦方位
    print("3. 八卦方位:")
    for trigram in Trigram:
        direction = mapping.get_direction_for_trigram(trigram)
        symbol = mapping.get_trigram_symbol(trigram)
        print(f"   {trigram.value}（{symbol}）→ {direction.value}")


def advanced_calculation_examples():
    """高级计算示例"""
    print("\n" + "=" * 50)
    print("高级计算示例")
    print("=" * 50)

    mapping = NajiaMapping()
    calculator = NajiaCalculator()

    # 1. 计算八卦关系
    print("1. 八卦关系计算:")
    test_pairs = [
        (Trigram.KAN, Trigram.LI, "坎离对冲"),
        (Trigram.ZHEN, Trigram.DUI, "震兑对冲"),
        (Trigram.QIAN, Trigram.KUN, "乾坤对冲"),
        (Trigram.KAN, Trigram.ZHEN, "坎震相邻"),
        (Trigram.LI, Trigram.DUI, "离兑相邻"),
    ]

    for trigram1, trigram2, description in test_pairs:
        relationship = calculator.calculate_trigram_relationship(
            trigram1, trigram2)
        symbol1 = mapping.get_trigram_symbol(trigram1)
        symbol2 = mapping.get_trigram_symbol(trigram2)
        print(
            f"   {trigram1.value}（{symbol1}）与{trigram2.value}（{symbol2}）{description}: {relationship}")

    print()

    # 2. 循环顺序分析
    print("2. 后天八卦循环顺序:")
    circular_order = mapping.get_circular_order()
    for i, trigram in enumerate(circular_order, 1):
        direction = mapping.get_direction_for_trigram(trigram)
        symbol = mapping.get_trigram_symbol(trigram)
        stems = [stem.value for stem in mapping.get_stems_for_trigram(trigram)]
        print(
            f"   {i}. {trigram.value}（{symbol}）{direction.value} - {', '.join(stems)}")


def practical_application_examples():
    """实际应用示例"""
    print("\n" + "=" * 50)
    print("实际应用示例")
    print("=" * 50)

    mapping = NajiaMapping()

    # 1. 生成完整的映射表
    print("1. 完整映射表:")
    mapping_data = mapping.get_complete_mapping()

    print(f"{'八卦':<6} {'符号':<4} {'天干':<10} {'方位':<8} {'英文名':<10}")
    print("-" * 50)

    for trigram_name, data in mapping_data.items():
        print(
            f"{trigram_name:<6} {data['symbol']:<4} {', '.join(data['stems']):<10} {data['direction']:<8} {data['english_name']:<10}")

    print()

    # 2. 方位分析
    print("2. 方位分析:")
    directions = {}
    for trigram in Trigram:
        direction = mapping.get_direction_for_trigram(trigram)
        if direction.value not in directions:
            directions[direction.value] = []
        directions[direction.value].append(trigram.value)

    for direction, trigrams in directions.items():
        print(f"   {direction}: {', '.join(trigrams)}")

    print()

    # 3. 天干分布分析
    print("3. 天干分布分析:")
    stem_distribution = {}
    for stem in HeavenlyStem:
        trigram = mapping.get_trigram_for_stem(stem)
        if trigram:
            if trigram.value not in stem_distribution:
                stem_distribution[trigram.value] = []
            stem_distribution[trigram.value].append(stem.value)

    for trigram, stems in stem_distribution.items():
        print(f"   {trigram}: {', '.join(stems)}")


def data_export_examples():
    """数据导出示例"""
    print("\n" + "=" * 50)
    print("数据导出示例")
    print("=" * 50)

    mapping = NajiaMapping()

    # 1. 导出到JSON
    print("1. 导出到JSON文件...")
    mapping.export_to_json("najia_mapping_export.json")
    print("   JSON文件已生成: najia_mapping_export.json")

    # 2. 生成CSV格式数据
    print("\n2. CSV格式数据:")
    print("八卦,符号,天干,方位,英文名")
    mapping_data = mapping.get_complete_mapping()
    for trigram_name, data in mapping_data.items():
        stems_str = ';'.join(data['stems'])
        print(
            f"{trigram_name},{data['symbol']},{stems_str},{data['direction']},{data['english_name']}")

    # 3. 生成Markdown表格
    print("\n3. Markdown表格格式:")
    print("| 八卦 | 符号 | 天干 | 方位 | 英文名 |")
    print("|------|------|------|------|--------|")
    for trigram_name, data in mapping_data.items():
        stems_str = '、'.join(data['stems'])
        print(
            f"| {trigram_name} | {data['symbol']} | {stems_str} | {data['direction']} | {data['english_name']} |")


def interactive_query_example():
    """交互式查询示例"""
    print("\n" + "=" * 50)
    print("交互式查询示例")
    print("=" * 50)

    mapping = NajiaMapping()
    calculator = NajiaCalculator()

    # 模拟用户查询
    queries = [
        ("乾", "查询乾卦信息"),
        ("甲", "查询天干甲对应八卦"),
        ("北方", "查询北方八卦"),
        ("坎离", "查询坎离关系"),
    ]

    for query, description in queries:
        print(f"\n{description}: {query}")

        if query in ["乾", "坤", "震", "巽", "坎", "离", "艮", "兑"]:
            # 查询八卦信息
            for trigram in Trigram:
                if trigram.value == query:
                    stems = mapping.get_stems_for_trigram(trigram)
                    direction = mapping.get_direction_for_trigram(trigram)
                    symbol = mapping.get_trigram_symbol(trigram)
                    stem_names = [stem.value for stem in stems]
                    print(f"   八卦: {trigram.value}（{symbol}）")
                    print(f"   天干: {', '.join(stem_names)}")
                    print(f"   方位: {direction.value}")
                    break

        elif query in ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]:
            # 查询天干信息
            for stem in HeavenlyStem:
                if stem.value == query:
                    trigram = mapping.get_trigram_for_stem(stem)
                    if trigram:
                        symbol = mapping.get_trigram_symbol(trigram)
                        print(f"   天干: {stem.value}")
                        print(f"   对应八卦: {trigram.value}（{symbol}）")
                    break

        elif "北方" in query or "南方" in query or "东方" in query or "西方" in query:
            # 查询方位信息
            for trigram in Trigram:
                direction = mapping.get_direction_for_trigram(trigram)
                if direction.value == query:
                    stems = mapping.get_stems_for_trigram(trigram)
                    symbol = mapping.get_trigram_symbol(trigram)
                    stem_names = [stem.value for stem in stems]
                    print(f"   方位: {direction.value}")
                    print(f"   八卦: {trigram.value}（{symbol}）")
                    print(f"   天干: {', '.join(stem_names)}")
                    break

        elif len(query) == 2 and all(c in "乾坤震巽坎离艮兑" for c in query):
            # 查询八卦关系
            trigram1 = None
            trigram2 = None
            for trigram in Trigram:
                if trigram.value == query[0]:
                    trigram1 = trigram
                if trigram.value == query[1]:
                    trigram2 = trigram

            if trigram1 and trigram2:
                relationship = calculator.calculate_trigram_relationship(
                    trigram1, trigram2)
                symbol1 = mapping.get_trigram_symbol(trigram1)
                symbol2 = mapping.get_trigram_symbol(trigram2)
                print(
                    f"   {trigram1.value}（{symbol1}）与{trigram2.value}（{symbol2}）的关系: {relationship}")


def main():
    """主函数"""
    print("八卦纳甲映射系统使用示例")
    print("=" * 60)

    # 运行各种示例
    basic_mapping_examples()
    advanced_calculation_examples()
    practical_application_examples()
    data_export_examples()
    interactive_query_example()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
