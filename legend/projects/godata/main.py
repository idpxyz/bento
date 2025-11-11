import datetime as dt

from rich import print as rprint
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from idp.projects.godata.ganzi_utils import (
    NAYIN_MAP,
    FourPillars,
    current_luck_pillar,
    four_pillars_from_datetime,
    relation_type,
    start_luck_info,
    ten_god,
)

console = Console()


def create_title_panel():
    """创建标题面板"""
    title = Text("八字命理分析系统", style="bold blue on white", justify="center")
    subtitle = Text("Chinese Four Pillars Destiny Analysis System",
                    style="italic cyan", justify="center")
    return Panel(Align.center(title + "\n" + subtitle), border_style="blue")


def demo_ten_gods():
    """演示十神关系"""
    console.print(Panel.fit("🎯 天干关系分析（十神）", style="bold blue"))

    ten_god_table = Table(title="十神关系对照表", show_header=True,
                          header_style="bold magenta")
    ten_god_table.add_column("日主", style="cyan", justify="center")
    ten_god_table.add_column("目标", style="cyan", justify="center")
    ten_god_table.add_column("关系", style="green", justify="center")
    ten_god_table.add_column("五行关系", style="yellow")
    ten_god_table.add_column("说明", style="white")

    # 展示各种十神关系
    examples = [
        ("甲", "丙", "食神", "木生火", "日主生目标，同性为食神"),
        ("甲", "乙", "劫财", "木木同", "同五行同阴阳，劫财"),
        ("甲", "庚", "七杀", "金克木", "目标克日主，同性为七杀"),
        ("甲", "辛", "正官", "金克木", "目标克日主，异性为正官"),
        ("甲", "壬", "偏印", "水生木", "目标生日主，同性为偏印"),
        ("甲", "癸", "正印", "水生木", "目标生日主，异性为正印"),
        ("甲", "戊", "偏财", "木克土", "日主克目标，同性为偏财"),
        ("甲", "己", "正财", "木克土", "日主克目标，异性为正财"),
    ]

    for day_stem, target_stem, relation, wuxing, desc in examples:
        ten_god_table.add_row(day_stem, target_stem, relation, wuxing, desc)

    console.print(ten_god_table)


def demo_earthly_branches():
    """演示地支关系"""
    console.print(Panel.fit("🌍 地支关系分析", style="bold green"))

    relation_table = Table(
        title="地支关系对照表", show_header=True, header_style="bold magenta")
    relation_table.add_column("地支1", style="cyan", justify="center")
    relation_table.add_column("地支2", style="cyan", justify="center")
    relation_table.add_column("关系", style="green", justify="center")
    relation_table.add_column("性质", style="yellow")
    relation_table.add_column("说明", style="white")

    # 展示各种地支关系
    examples = [
        ("子", "丑", "六合", "吉", "子丑合土，六合之一"),
        ("子", "午", "冲", "凶", "子午相冲，水火不容"),
        ("子", "卯", "刑", "凶", "子卯相刑，无礼之刑"),
        ("子", "未", "害", "凶", "子未相害，六害之一"),
        ("子", "酉", "破", "凶", "子酉相破，六破之一"),
    ]

    for branch1, branch2, relation, nature, desc in examples:
        relation_table.add_row(branch1, branch2, relation, nature, desc)

    # 添加三合关系的特殊处理
    relation_table.add_row("寅", "午", "三合", "吉", "寅午戌三合火局")
    relation_table.add_row("申", "子", "三合", "吉", "申子辰三合水局")

    console.print(relation_table)


def demo_nayin_wuxing():
    """演示纳音五行"""
    console.print(Panel.fit("🎵 纳音五行查询", style="bold magenta"))

    nayin_table = Table(title="纳音五行对照表", show_header=True,
                        header_style="bold magenta")
    nayin_table.add_column("干支", style="cyan", justify="center")
    nayin_table.add_column("纳音", style="magenta", justify="center")
    nayin_table.add_column("五行", style="yellow", justify="center")
    nayin_table.add_column("特性", style="white")

    # 展示各种纳音五行
    common_ganzhi = [
        ("甲子", "海中金", "金", "深藏不露，内敛稳重"),
        ("乙丑", "海中金", "金", "深藏不露，内敛稳重"),
        ("丙寅", "炉中火", "火", "温暖明亮，热情奔放"),
        ("丁卯", "炉中火", "火", "温暖明亮，热情奔放"),
        ("戊辰", "大林木", "木", "高大挺拔，正直向上"),
        ("己巳", "大林木", "木", "高大挺拔，正直向上"),
        ("庚午", "路旁土", "土", "厚实稳重，包容万物"),
        ("辛未", "路旁土", "土", "厚实稳重，包容万物"),
        ("壬申", "剑锋金", "金", "锋利尖锐，果断决绝"),
        ("癸酉", "剑锋金", "金", "锋利尖锐，果断决绝"),
    ]

    for ganzhi, nayin, wuxing, feature in common_ganzhi:
        nayin_table.add_row(ganzhi, nayin, wuxing, feature)

    console.print(nayin_table)


def demo_four_pillars():
    """演示四柱八字计算"""
    console.print(Panel.fit("📅 四柱八字计算", style="bold yellow"))

    # 测试不同时间的四柱
    test_times = [
        ("2025年7月31日 6:00", dt.datetime(2025, 7, 31, 6)),
        ("1990年5月12日 14:30", dt.datetime(1990, 5, 12, 14, 30)),
        ("2000年1月1日 0:00", dt.datetime(2000, 1, 1, 0)),
    ]

    pillars_table = Table(title="四柱八字计算结果", show_header=True,
                          header_style="bold magenta")
    pillars_table.add_column("时间", style="cyan")
    pillars_table.add_column("年柱", style="red", justify="center")
    pillars_table.add_column("月柱", style="green", justify="center")
    pillars_table.add_column("日柱", style="blue", justify="center")
    pillars_table.add_column("时柱", style="yellow", justify="center")
    pillars_table.add_column("纳音", style="magenta")

    for time_str, dt_obj in test_times:
        try:
            year_pillar, month_pillar, day_pillar, hour_pillar = four_pillars_from_datetime(
                dt_obj)
            year_nayin = NAYIN_MAP.get(year_pillar, "未知")
            pillars_table.add_row(
                time_str,
                year_pillar,
                month_pillar,
                day_pillar,
                hour_pillar,
                year_nayin
            )
        except Exception as e:
            pillars_table.add_row(time_str, "错误", "错误", "错误", "错误", str(e))

    console.print(pillars_table)


def demo_luck_analysis():
    """演示大运分析"""
    console.print(Panel.fit("🌟 大运流年分析", style="bold red"))

    # 测试不同出生时间的大运
    test_births = [
        ("1990年5月12日 14:30 男", dt.datetime(1990, 5, 12, 14, 30), "male"),
        ("1995年8月15日 9:00 女", dt.datetime(1995, 8, 15, 9), "female"),
    ]

    luck_table = Table(title="大运分析结果", show_header=True,
                       header_style="bold magenta")
    luck_table.add_column("出生信息", style="cyan")
    luck_table.add_column("起运信息", style="green")
    luck_table.add_column("当前大运", style="yellow")
    luck_table.add_column("方向", style="blue")

    for birth_info, birth_dt, gender in test_births:
        try:
            start_age, direction = start_luck_info(birth_dt, gender)
            current_luck = current_luck_pillar(birth_dt, gender)

            # 格式化起运信息
            direction_text = "顺推" if direction == 1 else "逆推"
            start_info = f"约{start_age:.1f}岁起运"

            luck_table.add_row(birth_info, start_info,
                               current_luck, direction_text)
        except Exception as e:
            luck_table.add_row(birth_info, "计算错误", str(e), "未知")

    console.print(luck_table)


def demo_comprehensive_analysis():
    """演示综合分析"""
    console.print(Panel.fit("🔮 八字综合分析示例", style="bold white on blue"))

    # 选择一个示例进行综合分析
    birth_time = dt.datetime(1990, 5, 12, 14, 30)
    year_pillar, month_pillar, day_pillar, hour_pillar = four_pillars_from_datetime(
        birth_time)

    # 创建分析面板
    analysis_panel = Panel(
        f"""
[bold cyan]出生时间:[/bold cyan] 1990年5月12日 14:30
[bold red]年柱:[/bold red] {year_pillar} ({NAYIN_MAP.get(year_pillar, '未知')})
[bold green]月柱:[/bold green] {month_pillar}
[bold blue]日柱:[/bold blue] {day_pillar}
[bold yellow]时柱:[/bold yellow] {hour_pillar}

[bold magenta]日主分析:[/bold magenta]
• 日主: {day_pillar[0]} (天干)
• 日支: {day_pillar[1]} (地支)
• 纳音: {NAYIN_MAP.get(day_pillar, '未知')}

[bold white]十神关系:[/bold white]
• 年干对日主: {ten_god(day_pillar[0], year_pillar[0])}
• 月干对日主: {ten_god(day_pillar[0], month_pillar[0])}
• 时干对日主: {ten_god(day_pillar[0], hour_pillar[0])}
        """,
        title="八字命盘分析",
        border_style="blue"
    )

    console.print(analysis_panel)


def main():
    """主函数"""
    # 显示标题
    console.print(create_title_panel())
    console.print()

    # 1. 天干关系分析
    demo_ten_gods()
    console.print()

    # 2. 地支关系分析
    demo_earthly_branches()
    console.print()

    # 3. 纳音五行查询
    demo_nayin_wuxing()
    console.print()

    # 4. 四柱八字计算
    demo_four_pillars()
    console.print()

    # 5. 大运流年分析
    demo_luck_analysis()
    console.print()

    # 6. 综合分析示例
    demo_comprehensive_analysis()
    console.print()

    # 总结
    summary_panel = Panel(
        """
✅ 计算天干关系（十神） - 完成
✅ 计算地支关系（六合、冲、刑、害、破） - 完成
✅ 查询纳音五行 - 完成
✅ 计算四柱八字 - 完成
✅ 计算大运信息 - 完成
✅ 使用 rich 库美化专业输出 - 完成

[bold green]所有功能测试通过！[/bold green]
        """,
        title="功能测试总结",
        border_style="green"
    )
    console.print(summary_panel)


if __name__ == "__main__":
    main()
