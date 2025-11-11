"""
   八卦纳甲映射系统 (Trigram Najia Mapping System)

   实现八卦与天干的对应关系，包括：
   - 八卦符号与天干的映射
   - 后天八卦方位
   - 纳甲规则的实现
   """

import json
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Trigram(Enum):
    """八卦枚举"""
    QIAN = "乾"  # ☰
    KUN = "坤"   # ☷
    ZHEN = "震"  # ☳
    XUN = "巽"   # ☴
    KAN = "坎"   # ☵
    LI = "离"    # ☲
    GEN = "艮"   # ☶
    DUI = "兑"   # ☱


class HeavenlyStem(Enum):
    """天干枚举"""
    JIA = "甲"
    YI = "乙"
    BING = "丙"
    DING = "丁"
    WU = "戊"
    JI = "己"
    GENG = "庚"
    XIN = "辛"
    REN = "壬"
    GUI = "癸"


class Direction(Enum):
    """方位枚举"""
    NORTH = "北方"
    SOUTH = "南方"
    EAST = "东方"
    WEST = "西方"
    SOUTHEAST = "东南"
    SOUTHWEST = "西南"
    NORTHWEST = "西北"
    NORTHEAST = "东北"


class NajiaMapping:
    """纳甲映射类"""

    def __init__(self):
        # 八卦到天干的映射关系
        self.trigram_to_stems: Dict[Trigram, List[HeavenlyStem]] = {
            Trigram.QIAN: [HeavenlyStem.JIA, HeavenlyStem.REN],  # 乾配甲壬
            Trigram.KUN: [HeavenlyStem.YI, HeavenlyStem.GUI],    # 坤配乙癸
            Trigram.ZHEN: [HeavenlyStem.GENG],                   # 震配庚
            Trigram.XUN: [HeavenlyStem.XIN],                     # 巽配辛
            Trigram.KAN: [HeavenlyStem.WU],                      # 坎配戊
            Trigram.LI: [HeavenlyStem.JI],                       # 离配己
            Trigram.GEN: [HeavenlyStem.BING],                    # 艮配丙
            Trigram.DUI: [HeavenlyStem.DING],                    # 兑配丁
        }

        # 后天八卦方位映射
        self.trigram_directions: Dict[Trigram, Direction] = {
            Trigram.KAN: Direction.NORTH,      # 坎居北方
            Trigram.LI: Direction.SOUTH,       # 离居南方
            Trigram.ZHEN: Direction.EAST,      # 震居东方
            Trigram.DUI: Direction.WEST,       # 兑居西方
            Trigram.XUN: Direction.SOUTHEAST,  # 巽居东南
            Trigram.KUN: Direction.SOUTHWEST,  # 坤居西南
            Trigram.QIAN: Direction.NORTHWEST,  # 乾居西北
            Trigram.GEN: Direction.NORTHEAST,  # 艮居东北
        }

        # 八卦符号映射
        self.trigram_symbols: Dict[Trigram, str] = {
            Trigram.QIAN: "☰",
            Trigram.KUN: "☷",
            Trigram.ZHEN: "☳",
            Trigram.XUN: "☴",
            Trigram.KAN: "☵",
            Trigram.LI: "☲",
            Trigram.GEN: "☶",
            Trigram.DUI: "☱",
        }

    def get_stems_for_trigram(self, trigram: Trigram) -> List[HeavenlyStem]:
        """获取八卦对应的天干"""
        return self.trigram_to_stems.get(trigram, [])

    def get_trigram_for_stem(self, stem: HeavenlyStem) -> Optional[Trigram]:
        """根据天干获取对应的八卦"""
        for trigram, stems in self.trigram_to_stems.items():
            if stem in stems:
                return trigram
        return None

    def get_direction_for_trigram(self, trigram: Trigram) -> Direction:
        """获取八卦的方位"""
        return self.trigram_directions.get(trigram)

    def get_trigram_symbol(self, trigram: Trigram) -> str:
        """获取八卦符号"""
        return self.trigram_symbols.get(trigram, "")

    def get_complete_mapping(self) -> Dict[str, Dict]:
        """获取完整的映射信息"""
        mapping = {}
        for trigram in Trigram:
            mapping[trigram.value] = {
                "symbol": self.get_trigram_symbol(trigram),
                "stems": [stem.value for stem in self.get_stems_for_trigram(trigram)],
                "direction": self.get_direction_for_trigram(trigram).value,
                "english_name": trigram.name
            }
        return mapping

    def get_circular_order(self) -> List[Trigram]:
        """获取后天八卦的循环顺序"""
        return [
            Trigram.KAN,   # 北方
            Trigram.LI,    # 南方
            Trigram.DUI,   # 西方
            Trigram.XUN,   # 东南
            Trigram.KUN,   # 西南
            Trigram.QIAN,  # 西北
            Trigram.GEN,   # 东北
            Trigram.ZHEN,  # 东方
        ]

    def export_to_json(self, filepath: str = "najia_mapping.json"):
        """导出映射到JSON文件"""
        mapping_data = self.get_complete_mapping()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
        print(f"映射数据已导出到: {filepath}")

    def print_mapping_table(self):
        """打印映射表"""
        print("=" * 60)
        print("八卦纳甲映射表")
        print("=" * 60)
        print(f"{'八卦':<6} {'符号':<4} {'天干':<8} {'方位':<6}")
        print("-" * 60)

        for trigram in Trigram:
            symbol = self.get_trigram_symbol(trigram)
            stems = [
                stem.value for stem in self.get_stems_for_trigram(trigram)]
            direction = self.get_direction_for_trigram(trigram).value
            print(
                f"{trigram.value:<6} {symbol:<4} {''.join(stems):<8} {direction:<6}")
        print("=" * 60)


class NajiaCalculator:
    """纳甲计算器 - 优化版本"""

    def __init__(self):
        self.mapping = NajiaMapping()
        # 预计算关系矩阵以提高性能
        self._relationship_matrix = self._build_relationship_matrix()

    def _build_relationship_matrix(self) -> Dict[Tuple[Trigram, Trigram], str]:
        """构建八卦关系矩阵"""
        matrix = {}

        # 预定义的对冲关系
        opposite_pairs = [
            (Trigram.KAN, Trigram.LI),   # 坎离对冲
            (Trigram.ZHEN, Trigram.DUI),  # 震兑对冲
            (Trigram.QIAN, Trigram.KUN),  # 乾坤对冲
            (Trigram.GEN, Trigram.XUN),  # 艮巽对冲
        ]

        # 预定义的相邻关系
        adjacent_pairs = [
            (Trigram.KAN, Trigram.GEN),  # 坎艮相邻
            (Trigram.KAN, Trigram.ZHEN),  # 坎震相邻
            (Trigram.LI, Trigram.DUI),   # 离兑相邻
            (Trigram.LI, Trigram.XUN),   # 离巽相邻
            (Trigram.ZHEN, Trigram.XUN),  # 震巽相邻
            (Trigram.ZHEN, Trigram.QIAN),  # 震乾相邻
            (Trigram.DUI, Trigram.KUN),  # 兑坤相邻
            (Trigram.DUI, Trigram.GEN),  # 兑艮相邻
            (Trigram.XUN, Trigram.KUN),  # 巽坤相邻
            (Trigram.GEN, Trigram.QIAN),  # 艮乾相邻
        ]

        # 填充关系矩阵
        for trigram1 in Trigram:
            for trigram2 in Trigram:
                if trigram1 == trigram2:
                    matrix[(trigram1, trigram2)] = "同位"
                elif (trigram1, trigram2) in opposite_pairs or (trigram2, trigram1) in opposite_pairs:
                    matrix[(trigram1, trigram2)] = "对冲"
                elif (trigram1, trigram2) in adjacent_pairs or (trigram2, trigram1) in adjacent_pairs:
                    matrix[(trigram1, trigram2)] = "相邻"
                else:
                    matrix[(trigram1, trigram2)] = "其他"

        return matrix

    def calculate_trigram_relationship(self, trigram1: Trigram, trigram2: Trigram) -> str:
        """计算两个八卦的关系 - 优化版本"""
        # 直接查找预计算的关系矩阵
        return self._relationship_matrix.get((trigram1, trigram2), "其他")

    def calculate_trigram_relationship_legacy(self, trigram1: Trigram, trigram2: Trigram) -> str:
        """计算两个八卦的关系 - 原始版本（保留用于对比）"""
        # 获取方位
        dir1 = self.mapping.get_direction_for_trigram(trigram1)
        dir2 = self.mapping.get_direction_for_trigram(trigram2)

        # 简单的方位关系判断
        if dir1 == dir2:
            return "同位"
        elif self._are_opposite_directions(dir1, dir2):
            return "对冲"
        elif self._are_adjacent_directions(dir1, dir2):
            return "相邻"
        else:
            return "其他"

    def _are_opposite_directions(self, dir1: Direction, dir2: Direction) -> bool:
        """判断是否为对冲方位"""
        opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.EAST: Direction.WEST,
            Direction.SOUTHEAST: Direction.NORTHWEST,
            Direction.SOUTHWEST: Direction.NORTHEAST,
        }
        return opposites.get(dir1) == dir2 or opposites.get(dir2) == dir1

    def _are_adjacent_directions(self, dir1: Direction, dir2: Direction) -> bool:
        """判断是否为相邻方位"""
        # 简化的相邻判断
        adjacent_pairs = [
            (Direction.NORTH, Direction.NORTHEAST),
            (Direction.NORTH, Direction.NORTHWEST),
            (Direction.SOUTH, Direction.SOUTHEAST),
            (Direction.SOUTH, Direction.SOUTHWEST),
            (Direction.EAST, Direction.SOUTHEAST),
            (Direction.EAST, Direction.NORTHEAST),
            (Direction.WEST, Direction.SOUTHWEST),
            (Direction.WEST, Direction.NORTHWEST),
        ]
        return (dir1, dir2) in adjacent_pairs or (dir2, dir1) in adjacent_pairs

    def get_all_relationships(self) -> Dict[Tuple[Trigram, Trigram], str]:
        """获取所有八卦关系 - 用于调试和验证"""
        return self._relationship_matrix.copy()

    def print_relationship_matrix(self):
        """打印关系矩阵 - 用于调试"""
        print("八卦关系矩阵:")
        print("=" * 50)
        print(f"{'':<6}", end="")
        for trigram2 in Trigram:
            print(f"{trigram2.value:<6}", end="")
        print()

        for trigram1 in Trigram:
            print(f"{trigram1.value:<6}", end="")
            for trigram2 in Trigram:
                relationship = self.calculate_trigram_relationship(
                    trigram1, trigram2)
                print(f"{relationship:<6}", end="")
            print()
        print("=" * 50)


def main():
    """主函数 - 演示纳甲映射系统"""
    try:
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()

        console.print(Panel.fit(
            "[bold blue]八卦纳甲映射系统演示[/bold blue]",
            border_style="blue"
        ))

        # 创建映射实例
        najia = NajiaMapping()
        calculator = NajiaCalculator()

        # 打印映射表
        console.print("[bold cyan]八卦纳甲映射表:[/bold cyan]")

        table = Table(title="八卦纳甲映射表", box=box.ROUNDED)
        table.add_column("八卦", style="cyan", no_wrap=True)
        table.add_column("符号", style="blue", justify="center")
        table.add_column("天干", style="green")
        table.add_column("方位", style="yellow")

        for trigram in Trigram:
            symbol = najia.get_trigram_symbol(trigram)
            stems = [
                stem.value for stem in najia.get_stems_for_trigram(trigram)]
            direction = najia.get_direction_for_trigram(trigram).value
            table.add_row(
                trigram.value,
                symbol,
                ", ".join(stems),
                direction
            )

        console.print(table)

        # 演示功能
        console.print("\n[bold magenta]功能演示:[/bold magenta]")

        # 1. 获取八卦对应的天干
        trigram = Trigram.QIAN
        stems = najia.get_stems_for_trigram(trigram)
        console.print(
            f"[green]1. {trigram.value}（{najia.get_trigram_symbol(trigram)}）对应的天干:[/green] {[stem.value for stem in stems]}")

        # 2. 根据天干获取八卦
        stem = HeavenlyStem.JIA
        trigram = najia.get_trigram_for_stem(stem)
        if trigram:
            console.print(
                f"[green]2. 天干{stem.value}对应的八卦:[/green] {trigram.value}（{najia.get_trigram_symbol(trigram)}）")

        # 3. 获取方位信息
        trigram = Trigram.KAN
        direction = najia.get_direction_for_trigram(trigram)
        console.print(
            f"[green]3. {trigram.value}（{najia.get_trigram_symbol(trigram)}）的方位:[/green] {direction.value}")

        # 4. 计算八卦关系
        trigram1, trigram2 = Trigram.KAN, Trigram.LI
        relationship = calculator.calculate_trigram_relationship(
            trigram1, trigram2)
        console.print(
            f"[green]4. {trigram1.value}与{trigram2.value}的关系:[/green] {relationship}")

        # 5. 导出到JSON
        najia.export_to_json()
        console.print("[green]5. 映射数据已导出到JSON文件[/green]")

        # 显示关系矩阵
        console.print("\n[bold cyan]八卦关系矩阵预览:[/bold cyan]")
        calculator.print_relationship_matrix()

        console.print(Panel.fit(
            "[bold green]🎉 演示完成！[/bold green]",
            border_style="green"
        ))

    except ImportError:
        # 如果没有rich库，使用普通输出
        print("八卦纳甲映射系统演示")
        print("=" * 40)

        # 创建映射实例
        najia = NajiaMapping()
        calculator = NajiaCalculator()

        # 打印映射表
        najia.print_mapping_table()

        # 演示功能
        print("\n功能演示:")
        print("-" * 20)

        # 1. 获取八卦对应的天干
        trigram = Trigram.QIAN
        stems = najia.get_stems_for_trigram(trigram)
        print(
            f"{trigram.value}（{najia.get_trigram_symbol(trigram)}）对应的天干: {[stem.value for stem in stems]}")

        # 2. 根据天干获取八卦
        stem = HeavenlyStem.JIA
        trigram = najia.get_trigram_for_stem(stem)
        if trigram:
            print(
                f"天干{stem.value}对应的八卦: {trigram.value}（{najia.get_trigram_symbol(trigram)}）")

        # 3. 获取方位信息
        trigram = Trigram.KAN
        direction = najia.get_direction_for_trigram(trigram)
        print(
            f"{trigram.value}（{najia.get_trigram_symbol(trigram)}）的方位: {direction.value}")

        # 4. 计算八卦关系
        trigram1, trigram2 = Trigram.KAN, Trigram.LI
        relationship = calculator.calculate_trigram_relationship(
            trigram1, trigram2)
        print(f"{trigram1.value}与{trigram2.value}的关系: {relationship}")

        # 5. 导出到JSON
        najia.export_to_json()

        print("\n演示完成！")


if __name__ == "__main__":
    main()
