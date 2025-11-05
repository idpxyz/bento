#!/usr/bin/env python3
"""Schema 注册监控命令行工具

该工具用于启动 Schema 注册监控服务。
"""

import argparse
import asyncio
import os
import signal
import sys
from typing import Any, Dict, List, Optional

from idp.framework.bootstrap.component.logger_setup import logger_setup, logger_manager
from idp.framework.infrastructure.schema.monitor.schema_monitor import SchemaMonitor


async def run_monitor(args: argparse.Namespace) -> None:
    """运行 Schema 监控服务"""
    # 设置日志
    await logger_setup()
    
    # 创建 Schema 监控器
    monitor = SchemaMonitor(args.url)
    
    # 绑定信号处理
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(loop)))
    
    logger = logger_manager.get_logger(__name__)
    logger.info(
        "Schema 监控服务启动",
        url=args.url or os.environ.get("PULSAR_ADMIN_URL"),
        check_interval=args.interval,
        event_type="schema_monitor_start"
    )
    
    try:
        # 启动监控
        await monitor.start_monitoring()
        
        # 保持任务运行
        while True:
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        logger.info("Schema 监控服务正在关闭...", event_type="schema_monitor_shutdown")
    finally:
        # 停止日志处理器
        await logger_manager.stop()


async def shutdown(loop: asyncio.AbstractEventLoop) -> None:
    """优雅关闭服务"""
    # 取消所有任务
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def check_once(args: argparse.Namespace) -> None:
    """执行单次健康检查"""
    # 设置日志
    await logger_setup()
    
    # 创建 Schema 监控器
    monitor = SchemaMonitor(args.url)
    
    logger = logger_manager.get_logger(__name__)
    logger.info(
        "执行 Schema 健康检查",
        url=args.url or os.environ.get("PULSAR_ADMIN_URL"),
        event_type="schema_health_check"
    )
    
    try:
        # 执行健康检查
        healthy, results = await monitor.check_schema_health()
        
        # 输出结果
        print(f"\n[🔍] Schema 健康检查结果: {'健康 ✅' if healthy else '异常 ❌'}")
        for result in results:
            status_icon = "✅" if result["status"] == "available" else "❌"
            print(f"  {status_icon} {result['schema']} ({result['topic']})")
            if result["status"] == "available":
                print(f"    版本: {result.get('version', 'unknown')}")
                print(f"    类型: {result.get('type', 'unknown')}")
            else:
                print(f"    错误: {result.get('error', 'unknown')}")
        
        if not results:
            print("  没有找到任何 Schema")
    except Exception as e:
        logger.error("Schema 健康检查失败", error=str(e), event_type="schema_health_check_error", exc_info=True)
        print(f"\n[❌] Schema 健康检查失败: {e}")
    finally:
        # 停止日志处理器
        await logger_manager.stop()


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Schema 注册监控工具")
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 启动监控服务的命令
    monitor_parser = subparsers.add_parser("start", help="启动 Schema 监控服务")
    monitor_parser.add_argument("--url", help="Pulsar Admin URL")
    monitor_parser.add_argument("--interval", type=int, default=3600, help="监控检查间隔(秒)")
    
    # 执行单次健康检查的命令
    check_parser = subparsers.add_parser("check", help="执行单次 Schema 健康检查")
    check_parser.add_argument("--url", help="Pulsar Admin URL")
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    if args.command == "start":
        try:
            asyncio.run(run_monitor(args))
        except KeyboardInterrupt:
            print("\n[👋] Schema 监控服务已停止")
    elif args.command == "check":
        asyncio.run(check_once(args))
    else:
        print("请指定子命令: start 或 check")
        sys.exit(1) 