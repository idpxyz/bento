#!/usr/bin/env python3
"""
八卦纳甲映射系统运行脚本

这个脚本设置了正确的Python路径，然后运行纳甲映射系统
"""

import os
import sys
from pathlib import Path

# 添加src目录到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def main():
    """主函数"""
    print("=" * 60)
    print("八卦纳甲映射系统")
    print("=" * 60)

    try:
        # 导入并运行主程序
        from ganzi_utils.trigram_najia import main as najia_main
        najia_main()

        print("\n" + "=" * 60)
        print("系统运行完成！")
        print("=" * 60)

    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保src目录中有trigram_najia.py文件")
        sys.exit(1)
    except Exception as e:
        print(f"运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
