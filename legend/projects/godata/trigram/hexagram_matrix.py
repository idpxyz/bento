#!/usr/bin/env python3
"""
64卦完整矩阵系统

包含：
- 八卦基础定义
- 64卦完整矩阵
- 卦象符号和名称
- 卦象关系分析
- 美观的可视化展示
"""

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from rich import box
    from rich.align import Align
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 创建控制台实例
if RICH_AVAILABLE:
    console = Console()


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


class Hexagram(Enum):
    """64卦枚举（按照《周易》传统顺序）"""
    # 1-8卦
    QIAN = "乾"      # 1. 乾卦
    KUN = "坤"       # 2. 坤卦
    TUN = "屯"       # 3. 屯卦
    MENG = "蒙"      # 4. 蒙卦
    XU = "需"        # 5. 需卦
    SONG = "讼"      # 6. 讼卦
    SHI = "师"       # 7. 师卦
    BI = "比"        # 8. 比卦

    # 9-16卦
    XIAO_CHU = "小畜"  # 9. 小畜卦
    LV = "履"         # 10. 履卦
    TAI = "泰"        # 11. 泰卦
    PI = "否"         # 12. 否卦
    TONG_REN = "同人"  # 13. 同人卦
    DA_YOU = "大有"    # 14. 大有卦
    QIAN_GUA = "谦"   # 15. 谦卦
    YU = "豫"         # 16. 豫卦

    # 17-24卦
    SUI = "随"        # 17. 随卦
    GU = "蛊"         # 18. 蛊卦
    LIN = "临"        # 19. 临卦
    GUAN = "观"       # 20. 观卦
    SHI_HE = "噬嗑"    # 21. 噬嗑卦
    BEN = "贲"        # 22. 贲卦
    BO = "剥"         # 23. 剥卦
    FU = "复"         # 24. 复卦

    # 25-32卦
    WU_WANG = "无妄"   # 25. 无妄卦
    DA_XU = "大畜"     # 26. 大畜卦
    YI = "颐"         # 27. 颐卦
    DA_GUO = "大过"    # 28. 大过卦
    KAN = "坎"        # 29. 坎卦
    LI = "离"         # 30. 离卦
    XIAN = "咸"       # 31. 咸卦
    HENG = "恒"       # 32. 恒卦

    # 33-40卦
    DUN = "遁"        # 33. 遁卦
    DA_ZHUANG = "大壮"  # 34. 大壮卦
    JIN = "晋"        # 35. 晋卦
    MING_YI = "明夷"   # 36. 明夷卦
    JIA_REN = "家人"   # 37. 家人卦
    KUI = "睽"        # 38. 睽卦
    JIAN = "蹇"       # 39. 蹇卦
    JIE = "解"        # 40. 解卦

    # 41-48卦
    SUN = "损"        # 41. 损卦
    YI_GUA = "益"     # 42. 益卦
    GUAI = "夬"       # 43. 夬卦
    GOU = "姤"        # 44. 姤卦
    CUI = "萃"        # 45. 萃卦
    SHENG = "升"      # 46. 升卦
    KUN_GUA = "困"   # 47. 困卦
    JING = "井"       # 48. 井卦

    # 49-56卦
    GE = "革"         # 49. 革卦
    DING = "鼎"       # 50. 鼎卦
    ZHEN = "震"       # 51. 震卦
    GEN = "艮"        # 52. 艮卦
    JIAN_GUA = "渐"   # 53. 渐卦
    GUI_MEI = "归妹"   # 54. 归妹卦
    FENG = "丰"       # 55. 丰卦
    LV_GUA = "旅"     # 56. 旅卦

    # 57-64卦
    XUN = "巽"        # 57. 巽卦
    DUI = "兑"        # 58. 兑卦
    HUAN = "涣"       # 59. 涣卦
    JIE_GUA = "节"    # 60. 节卦
    ZHONG_FU = "中孚"  # 61. 中孚卦
    XIAO_GUO = "小过"  # 62. 小过卦
    JI_JI = "既济"    # 63. 既济卦
    WEI_JI = "未济"   # 64. 未济卦


class HexagramMatrix:
    """64卦矩阵类"""

    def __init__(self):
        # 八卦符号映射
        self.trigram_symbols = {
            Trigram.QIAN: "☰",
            Trigram.KUN: "☷",
            Trigram.ZHEN: "☳",
            Trigram.XUN: "☴",
            Trigram.KAN: "☵",
            Trigram.LI: "☲",
            Trigram.GEN: "☶",
            Trigram.DUI: "☱"
        }

        # 八卦名称映射
        self.trigram_names = {
            Trigram.QIAN: "乾",
            Trigram.KUN: "坤",
            Trigram.ZHEN: "震",
            Trigram.XUN: "巽",
            Trigram.KAN: "坎",
            Trigram.LI: "离",
            Trigram.GEN: "艮",
            Trigram.DUI: "兑"
        }

        # 64卦矩阵 - 上卦为行，下卦为列
        self.hexagram_matrix = self._build_hexagram_matrix()

        # 卦象属性
        self.hexagram_attributes = self._build_hexagram_attributes()

    def _build_hexagram_matrix(self) -> Dict[Tuple[Trigram, Trigram], Hexagram]:
        """构建64卦矩阵 - 按照《周易》传统顺序"""
        matrix = {}

        # 后天八卦顺序：乾、坎、艮、震、巽、离、坤、兑
        houtian_order = [
            Trigram.QIAN,  # 乾
            Trigram.KAN,   # 坎
            Trigram.GEN,   # 艮
            Trigram.ZHEN,  # 震
            Trigram.XUN,   # 巽
            Trigram.LI,    # 离
            Trigram.KUN,   # 坤
            Trigram.DUI    # 兑
        ]

        # 按照《周易》传统64卦顺序的映射
        # 这里需要根据上下卦组合来确定对应的卦象
        # 简化处理：按照传统顺序排列
        hexagram_sequence = [
            Hexagram.QIAN,      # 1. 乾卦
            Hexagram.KUN,       # 2. 坤卦
            Hexagram.TUN,       # 3. 屯卦
            Hexagram.MENG,      # 4. 蒙卦
            Hexagram.XU,        # 5. 需卦
            Hexagram.SONG,      # 6. 讼卦
            Hexagram.SHI,       # 7. 师卦
            Hexagram.BI,        # 8. 比卦
            Hexagram.XIAO_CHU,  # 9. 小畜卦
            Hexagram.LV,        # 10. 履卦
            Hexagram.TAI,       # 11. 泰卦
            Hexagram.PI,        # 12. 否卦
            Hexagram.TONG_REN,  # 13. 同人卦
            Hexagram.DA_YOU,    # 14. 大有卦
            Hexagram.QIAN_GUA,  # 15. 谦卦
            Hexagram.YU,        # 16. 豫卦
            Hexagram.SUI,       # 17. 随卦
            Hexagram.GU,        # 18. 蛊卦
            Hexagram.LIN,       # 19. 临卦
            Hexagram.GUAN,      # 20. 观卦
            Hexagram.SHI_HE,    # 21. 噬嗑卦
            Hexagram.BEN,       # 22. 贲卦
            Hexagram.BO,        # 23. 剥卦
            Hexagram.FU,        # 24. 复卦
            Hexagram.WU_WANG,   # 25. 无妄卦
            Hexagram.DA_XU,     # 26. 大畜卦
            Hexagram.YI,        # 27. 颐卦
            Hexagram.DA_GUO,    # 28. 大过卦
            Hexagram.KAN,       # 29. 坎卦
            Hexagram.LI,        # 30. 离卦
            Hexagram.XIAN,      # 31. 咸卦
            Hexagram.HENG,      # 32. 恒卦
            Hexagram.DUN,       # 33. 遁卦
            Hexagram.DA_ZHUANG,  # 34. 大壮卦
            Hexagram.JIN,       # 35. 晋卦
            Hexagram.MING_YI,   # 36. 明夷卦
            Hexagram.JIA_REN,   # 37. 家人卦
            Hexagram.KUI,       # 38. 睽卦
            Hexagram.JIAN,      # 39. 蹇卦
            Hexagram.JIE,       # 40. 解卦
            Hexagram.SUN,       # 41. 损卦
            Hexagram.YI_GUA,    # 42. 益卦
            Hexagram.GUAI,      # 43. 夬卦
            Hexagram.GOU,       # 44. 姤卦
            Hexagram.CUI,       # 45. 萃卦
            Hexagram.SHENG,     # 46. 升卦
            Hexagram.KUN_GUA,   # 47. 困卦
            Hexagram.JING,      # 48. 井卦
            Hexagram.GE,        # 49. 革卦
            Hexagram.DING,      # 50. 鼎卦
            Hexagram.ZHEN,      # 51. 震卦
            Hexagram.GEN,       # 52. 艮卦
            Hexagram.JIAN_GUA,  # 53. 渐卦
            Hexagram.GUI_MEI,   # 54. 归妹卦
            Hexagram.FENG,      # 55. 丰卦
            Hexagram.LV_GUA,    # 56. 旅卦
            Hexagram.XUN,       # 57. 巽卦
            Hexagram.DUI,       # 58. 兑卦
            Hexagram.HUAN,      # 59. 涣卦
            Hexagram.JIE_GUA,   # 60. 节卦
            Hexagram.ZHONG_FU,  # 61. 中孚卦
            Hexagram.XIAO_GUO,  # 62. 小过卦
            Hexagram.JI_JI,     # 63. 既济卦
            Hexagram.WEI_JI     # 64. 未济卦
        ]

        # 构建矩阵：按照后天八卦顺序排列
        for i, upper in enumerate(houtian_order):
            for j, lower in enumerate(houtian_order):
                index = i * 8 + j
                if index < len(hexagram_sequence):
                    matrix[(upper, lower)] = hexagram_sequence[index]

        return matrix

    def _build_hexagram_attributes(self) -> Dict[Hexagram, Dict]:
        """构建卦象属性"""
        attributes = {}

        # 为每个卦象定义基本属性
        for hexagram in Hexagram:
            attributes[hexagram] = {
                "name": hexagram.value,
                "nature": "阳" if hexagram.value in ["乾", "震", "坎", "艮"] else "阴",
                "element": self._get_element(hexagram),
                "meaning": self._get_meaning(hexagram)
            }

        return attributes

    def _get_element(self, hexagram: Hexagram) -> str:
        """获取卦象对应的五行"""
        element_map = {
            "乾": "金", "坤": "土", "震": "木", "巽": "木",
            "坎": "水", "离": "火", "艮": "土", "兑": "金"
        }
        return element_map.get(hexagram.value, "未知")

    def _get_meaning(self, hexagram: Hexagram) -> str:
        """获取卦象含义"""
        meaning_map = {
            "乾": "天行健，君子以自强不息",
            "坤": "地势坤，君子以厚德载物",
            "震": "雷，动也",
            "巽": "风，入也",
            "坎": "水，陷也",
            "离": "火，丽也",
            "艮": "山，止也",
            "兑": "泽，说也"
        }
        return meaning_map.get(hexagram.value, "待补充")

    def get_hexagram(self, upper: Trigram, lower: Trigram) -> Optional[Hexagram]:
        """根据上下卦获取卦象"""
        return self.hexagram_matrix.get((upper, lower))

    def get_trigrams(self, hexagram: Hexagram) -> Optional[Tuple[Trigram, Trigram]]:
        """根据卦象获取上下卦"""
        for (upper, lower), h in self.hexagram_matrix.items():
            if h == hexagram:
                return (upper, lower)
        return None

    def get_hexagram_symbol(self, hexagram: Hexagram) -> str:
        """获取卦象符号"""
        trigrams = self.get_trigrams(hexagram)
        if trigrams:
            upper, lower = trigrams
            return f"{self.trigram_symbols[upper]}\n{self.trigram_symbols[lower]}"
        return ""

    def print_matrix(self):
        """打印64卦矩阵 - 按照后天八卦顺序"""
        if not RICH_AVAILABLE:
            self._print_matrix_plain()
            return

        console.print(Panel.fit(
            "[bold blue]☯ 64卦完整矩阵 ☯[/bold blue]\n[dim]Complete 64 Hexagram Matrix (Houtian Order)[/dim]",
            border_style="blue",
            padding=(1, 2)
        ))

        # 后天八卦顺序
        houtian_order = [
            Trigram.QIAN,  # 乾
            Trigram.KAN,   # 坎
            Trigram.GEN,   # 艮
            Trigram.ZHEN,  # 震
            Trigram.XUN,   # 巽
            Trigram.LI,    # 离
            Trigram.KUN,   # 坤
            Trigram.DUI    # 兑
        ]

        # 创建矩阵表格
        table = Table(
            title="[bold cyan]64卦矩阵表 (后天八卦顺序)[/bold cyan]",
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan"
        )

        # 添加列标题
        table.add_column("上卦\\下卦", style="bold cyan",
                         no_wrap=True, justify="center")
        for trigram in houtian_order:
            table.add_column(
                f"{trigram.value}",
                style="bold blue",
                justify="center",
                no_wrap=True
            )

        # 添加行数据
        for upper in houtian_order:
            row = [f"[bold cyan]{upper.value}[/bold cyan]"]
            for lower in houtian_order:
                hexagram = self.get_hexagram(upper, lower)
                if hexagram:
                    symbol = self.get_hexagram_symbol(hexagram)
                    cell_content = f"{hexagram.value}\n{symbol}"
                    row.append(f"[green]{cell_content}[/green]")
                else:
                    row.append("[red]无[/red]")
            table.add_row(*row)

        console.print(table)

        # 添加后天八卦方位说明
        direction_info = Text()
        direction_info.append("后天八卦顺序: ", style="bold yellow")
        direction_info.append("乾 → 坎 → 艮 → 震 → 巽 → 离 → 坤 → 兑", style="cyan")

        direction_panel = Panel(
            direction_info,
            title="[bold yellow]后天八卦顺序[/bold yellow]",
            border_style="yellow",
            padding=(0, 1)
        )
        console.print(direction_panel)

    def _print_matrix_plain(self):
        """普通文本打印矩阵 - 按照后天八卦顺序"""
        print("=" * 80)
        print("64卦完整矩阵 (后天八卦顺序)")
        print("=" * 80)

        # 后天八卦顺序
        houtian_order = [
            Trigram.QIAN,  # 乾
            Trigram.KAN,   # 坎
            Trigram.GEN,   # 艮
            Trigram.ZHEN,  # 震
            Trigram.XUN,   # 巽
            Trigram.LI,    # 离
            Trigram.KUN,   # 坤
            Trigram.DUI    # 兑
        ]

        # 打印表头
        print(f"{'上卦\\下卦':<8}", end="")
        for trigram in houtian_order:
            print(f"{trigram.value:<8}", end="")
        print()
        print("-" * 80)

        # 打印矩阵内容
        for upper in houtian_order:
            print(f"{upper.value:<8}", end="")
            for lower in houtian_order:
                hexagram = self.get_hexagram(upper, lower)
                if hexagram:
                    print(f"{hexagram.value:<8}", end="")
                else:
                    print(f"{'无':<8}", end="")
            print()
        print("=" * 80)

        # 打印方位说明
        print("后天八卦顺序: 乾 → 坎 → 艮 → 震 → 巽 → 离 → 坤 → 兑")
        print("=" * 80)

    def print_hexagram_details(self, hexagram: Hexagram):
        """打印卦象详细信息"""
        if not RICH_AVAILABLE:
            self._print_hexagram_details_plain(hexagram)
            return

        trigrams = self.get_trigrams(hexagram)
        if not trigrams:
            console.print(f"[red]未找到卦象 {hexagram.value} 的信息[/red]")
            return

        upper, lower = trigrams
        attributes = self.hexagram_attributes[hexagram]

        # 创建详细信息面板
        detail_text = Text()
        detail_text.append(f"卦象: {hexagram.value}\n", style="bold blue")
        detail_text.append(
            f"上卦: {upper.value} {self.trigram_symbols[upper]}\n", style="cyan")
        detail_text.append(
            f"下卦: {lower.value} {self.trigram_symbols[lower]}\n", style="cyan")
        detail_text.append(f"性质: {attributes['nature']}\n", style="green")
        detail_text.append(f"五行: {attributes['element']}\n", style="yellow")
        detail_text.append(f"含义: {attributes['meaning']}", style="white")

        detail_panel = Panel(
            detail_text,
            title=f"[bold green]{hexagram.value}卦详细信息[/bold green]",
            border_style="green",
            padding=(1, 2)
        )

        console.print(detail_panel)

    def _print_hexagram_details_plain(self, hexagram: Hexagram):
        """普通文本打印卦象详情"""
        trigrams = self.get_trigrams(hexagram)
        if not trigrams:
            print(f"未找到卦象 {hexagram.value} 的信息")
            return

        upper, lower = trigrams
        attributes = self.hexagram_attributes[hexagram]

        print(f"卦象: {hexagram.value}")
        print(f"上卦: {upper.value} {self.trigram_symbols[upper]}")
        print(f"下卦: {lower.value} {self.trigram_symbols[lower]}")
        print(f"性质: {attributes['nature']}")
        print(f"五行: {attributes['element']}")
        print(f"含义: {attributes['meaning']}")

    def export_to_json(self, filepath: str = "hexagram_matrix.json"):
        """导出矩阵到JSON文件"""
        data = {
            "matrix": {},
            "attributes": {}
        }

        # 导出矩阵
        for (upper, lower), hexagram in self.hexagram_matrix.items():
            key = f"{upper.value}_{lower.value}"
            data["matrix"][key] = hexagram.value

        # 导出属性
        for hexagram, attrs in self.hexagram_attributes.items():
            data["attributes"][hexagram.value] = attrs

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if RICH_AVAILABLE:
            console.print(f"[green]矩阵数据已导出到: {filepath}[/green]")
        else:
            print(f"矩阵数据已导出到: {filepath}")


def main():
    """主函数"""
    if not RICH_AVAILABLE:
        print("建议安装rich库以获得更好的显示效果: pip install rich")

    # 创建64卦矩阵
    matrix = HexagramMatrix()

    # 显示矩阵
    matrix.print_matrix()

    # 显示几个示例卦象的详细信息
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]示例卦象详细信息:[/bold cyan]")
    else:
        print("\n示例卦象详细信息:")

    example_hexagrams = [Hexagram.QIAN,
                         Hexagram.KUN, Hexagram.ZHEN, Hexagram.KAN]
    for hexagram in example_hexagrams:
        matrix.print_hexagram_details(hexagram)
        if RICH_AVAILABLE:
            console.print()

    # 导出数据
    matrix.export_to_json()

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold green]🎯 64卦矩阵展示完成！[/bold green]",
            border_style="green"
        ))
    else:
        print("\n🎯 64卦矩阵展示完成！")


if __name__ == "__main__":
    main()
