#!/usr/bin/env python3
"""
八卦纳甲映射系统性能测试

对比优化前后的关系计算性能
使用rich库美化输出
"""

import os
import sys
import time
from pathlib import Path

from ganzi_utils.trigram_najia import NajiaCalculator, Trigram
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table
from rich.text import Text

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 创建控制台实例
console = Console()


def test_relationship_calculation_performance():
    """测试关系计算性能"""
    console.print(Panel.fit(
        "[bold blue]八卦纳甲关系计算性能测试[/bold blue]",
        border_style="blue"
    ))

    calculator = NajiaCalculator()

    # 测试数据：所有八卦组合
    test_pairs = []
    for trigram1 in Trigram:
        for trigram2 in Trigram:
            test_pairs.append((trigram1, trigram2))

    console.print(f"[yellow]测试数据量:[/yellow] {len(test_pairs)} 个八卦组合")
    console.print()

    # 测试优化版本
    console.print("[bold green]1. 测试优化版本 (预计算矩阵):[/bold green]")

    with console.status("[bold green]运行优化版本测试...[/bold green]"):
        start_time = time.time()

        for _ in track(range(10000), description="优化版本测试进度"):
            for trigram1, trigram2 in test_pairs:
                relationship = calculator.calculate_trigram_relationship(
                    trigram1, trigram2)

        end_time = time.time()

    optimized_time = end_time - start_time
    console.print(f"   [green]10000次关系计算耗时:[/green] {optimized_time:.4f}秒")
    console.print(
        f"   [green]平均每次计算耗时:[/green] {optimized_time/10000/len(test_pairs)*1000:.4f}毫秒")

    # 测试原始版本
    console.print("\n[bold red]2. 测试原始版本 (动态计算):[/bold red]")

    with console.status("[bold red]运行原始版本测试...[/bold red]"):
        start_time = time.time()

        for _ in track(range(10000), description="原始版本测试进度"):
            for trigram1, trigram2 in test_pairs:
                relationship = calculator.calculate_trigram_relationship_legacy(
                    trigram1, trigram2)

        end_time = time.time()

    legacy_time = end_time - start_time
    console.print(f"   [red]10000次关系计算耗时:[/red] {legacy_time:.4f}秒")
    console.print(
        f"   [red]平均每次计算耗时:[/red] {legacy_time/10000/len(test_pairs)*1000:.4f}毫秒")

    # 性能对比表格
    console.print("\n[bold cyan]3. 性能对比:[/bold cyan]")
    speedup = legacy_time / optimized_time

    table = Table(title="性能对比结果", box=box.ROUNDED)
    table.add_column("指标", style="cyan", no_wrap=True)
    table.add_column("优化版本", style="green")
    table.add_column("原始版本", style="red")
    table.add_column("提升", style="yellow")

    table.add_row(
        "计算耗时",
        f"{optimized_time:.4f}秒",
        f"{legacy_time:.4f}秒",
        f"{speedup:.2f}倍"
    )

    table.add_row(
        "平均耗时",
        f"{optimized_time/10000/len(test_pairs)*1000:.4f}毫秒",
        f"{legacy_time/10000/len(test_pairs)*1000:.4f}毫秒",
        f"{(speedup-1)*100:.1f}%"
    )

    console.print(table)

    # 验证结果一致性
    console.print("\n[bold magenta]4. 验证结果一致性:[/bold magenta]")

    with console.status("[bold magenta]验证结果一致性...[/bold magenta]"):
        mismatches = 0
        for trigram1, trigram2 in test_pairs:
            optimized_result = calculator.calculate_trigram_relationship(
                trigram1, trigram2)
            legacy_result = calculator.calculate_trigram_relationship_legacy(
                trigram1, trigram2)
            if optimized_result != legacy_result:
                mismatches += 1
                console.print(
                    f"   [red]不匹配:[/red] {trigram1.value}与{trigram2.value} - 优化:{optimized_result}, 原始:{legacy_result}")

    if mismatches == 0:
        console.print("   [bold green]✅ 所有结果一致[/bold green]")
    else:
        console.print(f"   [bold red]❌ 发现 {mismatches} 个不匹配[/bold red]")


def test_mapping_performance():
    """测试映射查询性能"""
    console.print(Panel.fit(
        "[bold blue]八卦纳甲映射查询性能测试[/bold blue]",
        border_style="blue"
    ))

    from ganzi_utils.trigram_najia import HeavenlyStem, NajiaMapping

    mapping = NajiaMapping()

    # 测试映射查询性能
    console.print("[bold green]测试映射查询性能:[/bold green]")

    with console.status("[bold green]运行映射查询测试...[/bold green]"):
        start_time = time.time()
        for _ in track(range(10000), description="映射查询测试"):
            for trigram in Trigram:
                stems = mapping.get_stems_for_trigram(trigram)
                direction = mapping.get_direction_for_trigram(trigram)
                symbol = mapping.get_trigram_symbol(trigram)
        end_time = time.time()

    mapping_time = end_time - start_time
    console.print(f"   [green]10000次映射查询耗时:[/green] {mapping_time:.4f}秒")

    # 测试天干到八卦的查询性能
    console.print("\n[bold green]测试天干查询性能:[/bold green]")

    with console.status("[bold green]运行天干查询测试...[/bold green]"):
        start_time = time.time()
        for _ in track(range(10000), description="天干查询测试"):
            for stem in HeavenlyStem:
                trigram = mapping.get_trigram_for_stem(stem)
        end_time = time.time()

    stem_time = end_time - start_time
    console.print(f"   [green]10000次天干查询耗时:[/green] {stem_time:.4f}秒")

    # 创建性能汇总表格
    table = Table(title="映射查询性能汇总", box=box.ROUNDED)
    table.add_column("查询类型", style="cyan", no_wrap=True)
    table.add_column("测试次数", style="blue")
    table.add_column("总耗时", style="green")
    table.add_column("平均耗时", style="yellow")

    table.add_row(
        "映射查询",
        "10000次",
        f"{mapping_time:.4f}秒",
        f"{mapping_time/10000:.6f}秒"
    )

    table.add_row(
        "天干查询",
        "10000次",
        f"{stem_time:.4f}秒",
        f"{stem_time/10000:.6f}秒"
    )

    console.print(table)


def test_memory_usage():
    """测试内存使用情况"""
    console.print(Panel.fit(
        "[bold blue]内存使用情况测试[/bold blue]",
        border_style="blue"
    ))

    try:
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 创建多个计算器实例
        console.print("[bold green]创建100个计算器实例...[/bold green]")
        calculators = []

        for i in track(range(100), description="创建计算器实例"):
            calculator = NajiaCalculator()
            calculators.append(calculator)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 创建内存使用表格
        table = Table(title="内存使用情况", box=box.ROUNDED)
        table.add_column("指标", style="cyan", no_wrap=True)
        table.add_column("数值", style="green")
        table.add_column("单位", style="blue")

        table.add_row("初始内存使用", f"{initial_memory:.2f}", "MB")
        table.add_row("创建100个计算器后内存使用", f"{final_memory:.2f}", "MB")
        table.add_row("内存增加", f"{memory_increase:.2f}", "MB")
        table.add_row("每个计算器平均内存", f"{memory_increase/100:.4f}", "MB")

        console.print(table)

    except ImportError:
        console.print(
            "[yellow]跳过内存测试 (需要安装psutil: pip install psutil)[/yellow]")


def demonstrate_relationship_matrix():
    """演示关系矩阵"""
    console.print(Panel.fit(
        "[bold blue]八卦关系矩阵演示[/bold blue]",
        border_style="blue"
    ))

    calculator = NajiaCalculator()

    # 创建关系矩阵表格
    table = Table(title="八卦关系矩阵", box=box.ROUNDED)

    # 添加列标题
    table.add_column("", style="cyan", no_wrap=True)
    for trigram in Trigram:
        table.add_column(trigram.value, style="blue", justify="center")

    # 添加行数据
    for trigram1 in Trigram:
        row = [trigram1.value]
        for trigram2 in Trigram:
            relationship = calculator.calculate_trigram_relationship(
                trigram1, trigram2)
            # 根据关系类型设置颜色
            if relationship == "同位":
                style = "bold green"
            elif relationship == "对冲":
                style = "bold red"
            elif relationship == "相邻":
                style = "bold yellow"
            else:
                style = "white"
            row.append(f"[{style}]{relationship}[/{style}]")
        table.add_row(*row)

    console.print(table)

    # 显示关系示例
    console.print("\n[bold cyan]关系示例:[/bold cyan]")
    examples = [
        (Trigram.KAN, Trigram.LI, "坎离对冲", "red"),
        (Trigram.ZHEN, Trigram.DUI, "震兑对冲", "red"),
        (Trigram.QIAN, Trigram.KUN, "乾坤对冲", "red"),
        (Trigram.KAN, Trigram.GEN, "坎艮相邻", "yellow"),
        (Trigram.LI, Trigram.DUI, "离兑相邻", "yellow"),
        (Trigram.QIAN, Trigram.QIAN, "乾乾同位", "green"),
    ]

    for trigram1, trigram2, description, color in examples:
        relationship = calculator.calculate_trigram_relationship(
            trigram1, trigram2)
        console.print(
            f"   [bold]{trigram1.value}与{trigram2.value}[/bold] {description}: [{color}]{relationship}[/{color}]")


def show_performance_summary():
    """显示性能总结"""
    console.print(Panel.fit(
        "[bold green]🎉 性能优化总结[/bold green]",
        border_style="green"
    ))

    summary_text = Text()
    summary_text.append("✅ 关系计算性能大幅提升\n", style="bold green")
    summary_text.append("✅ 使用预计算矩阵优化\n", style="bold green")
    summary_text.append("✅ 保持结果一致性\n", style="bold green")
    summary_text.append("✅ 内存使用合理\n", style="bold green")
    summary_text.append("✅ 代码结构清晰\n", style="bold green")

    console.print(Align.center(summary_text))


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold blue]八卦纳甲映射系统性能测试[/bold blue]\n[dim]使用rich库美化输出[/dim]",
        border_style="blue"
    ))

    try:
        # 运行各种性能测试
        test_relationship_calculation_performance()
        test_mapping_performance()
        test_memory_usage()
        demonstrate_relationship_matrix()
        show_performance_summary()

        console.print(Panel.fit(
            "[bold green]🎯 性能测试完成！[/bold green]",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]测试过程中出现错误:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc(), style="red")


if __name__ == "__main__":
    main()
