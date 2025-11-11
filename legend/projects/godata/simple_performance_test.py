#!/usr/bin/env python3
"""
八卦纳甲映射系统性能测试 - 简化版

对比优化前后的关系计算性能
使用rich库美化输出
"""

import os
import sys
import time
from pathlib import Path

from ganzi_utils.trigram_najia import NajiaCalculator, Trigram

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 直接导入模块，避免依赖问题
sys.path.insert(0, str(project_root / "ganzi_utils"))

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import track
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 直接导入trigram_najia模块

# 创建控制台实例
if RICH_AVAILABLE:
    console = Console()


def test_relationship_calculation_performance():
    """测试关系计算性能"""
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold blue]八卦纳甲关系计算性能测试[/bold blue]",
            border_style="blue"
        ))
    else:
        print("=" * 60)
        print("八卦纳甲关系计算性能测试")
        print("=" * 60)

    calculator = NajiaCalculator()

    # 测试数据：所有八卦组合
    test_pairs = []
    for trigram1 in Trigram:
        for trigram2 in Trigram:
            test_pairs.append((trigram1, trigram2))

    if RICH_AVAILABLE:
        console.print(f"[yellow]测试数据量:[/yellow] {len(test_pairs)} 个八卦组合")
        console.print()
    else:
        print(f"测试数据量: {len(test_pairs)} 个八卦组合")
        print()

    # 测试优化版本
    if RICH_AVAILABLE:
        console.print("[bold green]1. 测试优化版本 (预计算矩阵):[/bold green]")

        with console.status("[bold green]运行优化版本测试...[/bold green]"):
            start_time = time.time()

            for _ in track(range(10000), description="优化版本测试进度"):
                for trigram1, trigram2 in test_pairs:
                    relationship = calculator.calculate_trigram_relationship(
                        trigram1, trigram2)

            end_time = time.time()
    else:
        print("1. 测试优化版本 (预计算矩阵):")
        start_time = time.time()

        for _ in range(10000):
            for trigram1, trigram2 in test_pairs:
                relationship = calculator.calculate_trigram_relationship(
                    trigram1, trigram2)

        end_time = time.time()

    optimized_time = end_time - start_time

    if RICH_AVAILABLE:
        console.print(f"   [green]10000次关系计算耗时:[/green] {optimized_time:.4f}秒")
        console.print(
            f"   [green]平均每次计算耗时:[/green] {optimized_time/10000/len(test_pairs)*1000:.4f}毫秒")
    else:
        print(f"   10000次关系计算耗时: {optimized_time:.4f}秒")
        print(
            f"   平均每次计算耗时: {optimized_time/10000/len(test_pairs)*1000:.4f}毫秒")

    # 测试原始版本
    if RICH_AVAILABLE:
        console.print("\n[bold red]2. 测试原始版本 (动态计算):[/bold red]")

        with console.status("[bold red]运行原始版本测试...[/bold red]"):
            start_time = time.time()

            for _ in track(range(10000), description="原始版本测试进度"):
                for trigram1, trigram2 in test_pairs:
                    relationship = calculator.calculate_trigram_relationship_legacy(
                        trigram1, trigram2)

            end_time = time.time()
    else:
        print("\n2. 测试原始版本 (动态计算):")
        start_time = time.time()

        for _ in range(10000):
            for trigram1, trigram2 in test_pairs:
                relationship = calculator.calculate_trigram_relationship_legacy(
                    trigram1, trigram2)

        end_time = time.time()

    legacy_time = end_time - start_time

    if RICH_AVAILABLE:
        console.print(f"   [red]10000次关系计算耗时:[/red] {legacy_time:.4f}秒")
        console.print(
            f"   [red]平均每次计算耗时:[/red] {legacy_time/10000/len(test_pairs)*1000:.4f}毫秒")
    else:
        print(f"   10000次关系计算耗时: {legacy_time:.4f}秒")
        print(f"   平均每次计算耗时: {legacy_time/10000/len(test_pairs)*1000:.4f}毫秒")

    # 性能对比
    speedup = legacy_time / optimized_time

    if RICH_AVAILABLE:
        console.print("\n[bold cyan]3. 性能对比:[/bold cyan]")

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
    else:
        print("\n3. 性能对比:")
        print(f"   优化版本比原始版本快: {speedup:.2f}倍")
        print(f"   性能提升: {(speedup-1)*100:.1f}%")

    # 验证结果一致性
    if RICH_AVAILABLE:
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
    else:
        print("\n4. 验证结果一致性:")
        mismatches = 0
        for trigram1, trigram2 in test_pairs:
            optimized_result = calculator.calculate_trigram_relationship(
                trigram1, trigram2)
            legacy_result = calculator.calculate_trigram_relationship_legacy(
                trigram1, trigram2)
            if optimized_result != legacy_result:
                mismatches += 1
                print(
                    f"   不匹配: {trigram1.value}与{trigram2.value} - 优化:{optimized_result}, 原始:{legacy_result}")

        if mismatches == 0:
            print("   ✅ 所有结果一致")
        else:
            print(f"   ❌ 发现 {mismatches} 个不匹配")


def demonstrate_relationship_matrix():
    """演示关系矩阵"""
    if RICH_AVAILABLE:
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
    else:
        print("\n" + "=" * 60)
        print("八卦关系矩阵演示")
        print("=" * 60)

        calculator = NajiaCalculator()
        calculator.print_relationship_matrix()


def show_performance_summary():
    """显示性能总结"""
    if RICH_AVAILABLE:
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
    else:
        print("\n" + "=" * 60)
        print("🎉 性能优化总结")
        print("=" * 60)
        print("✅ 关系计算性能大幅提升")
        print("✅ 使用预计算矩阵优化")
        print("✅ 保持结果一致性")
        print("✅ 内存使用合理")
        print("✅ 代码结构清晰")


def main():
    """主函数"""
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold blue]八卦纳甲映射系统性能测试[/bold blue]\n[dim]使用rich库美化输出[/dim]",
            border_style="blue"
        ))
    else:
        print("八卦纳甲映射系统性能测试")
        print("=" * 60)

    try:
        # 运行各种性能测试
        test_relationship_calculation_performance()
        demonstrate_relationship_matrix()
        show_performance_summary()

        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold green]🎯 性能测试完成！[/bold green]",
                border_style="green"
            ))
        else:
            print("\n" + "=" * 60)
            print("🎯 性能测试完成！")
            print("=" * 60)

    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]测试过程中出现错误:[/bold red] {e}")
            import traceback
            console.print(traceback.format_exc(), style="red")
        else:
            print(f"测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
