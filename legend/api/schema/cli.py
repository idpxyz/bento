#!/usr/bin/env python3
"""
Schema 注册监控 API 命令行工具

该工具用于启动 Schema 注册监控 API 服务
"""

import argparse
import os
import sys
from typing import Optional

from idp.framework.api.schema.app import start_app


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Schema 注册监控 API 服务")
    
    parser.add_argument("--host", help="监听主机", default="0.0.0.0")
    parser.add_argument("--port", type=int, help="监听端口", default=8000)
    parser.add_argument("--reload", action="store_true", help="开发模式下自动重载")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    return parser.parse_args()


def main() -> int:
    """主函数"""
    args = parse_args()
    
    print(f"[🚀] 启动 Schema 注册监控 API 服务 - http://{args.host}:{args.port}/schema-monitor")
    
    try:
        start_app(
            host=args.host,
            port=args.port,
            reload=args.reload,
            debug=args.debug
        )
        return 0
    except KeyboardInterrupt:
        print("\n[👋] Schema 注册监控 API 服务已停止")
        return 0
    except Exception as e:
        print(f"[❌] 启动服务失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 