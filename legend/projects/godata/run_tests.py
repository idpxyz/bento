#!/usr/bin/env python3
"""
八卦纳甲映射系统测试运行脚本

这个脚本设置了正确的Python路径，然后运行测试
"""

import os
import sys
import unittest
from pathlib import Path

# 添加src目录到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def main():
    """主函数"""
    print("=" * 60)
    print("八卦纳甲映射系统测试")
    print("=" * 60)

    try:
        # 导入测试模块
        import tests.test_najia as test_module

        # 运行单元测试
        print("运行单元测试...")
        unittest.main(verbosity=2, exit=False, module=test_module)

        # 运行性能测试
        print("\n" + "=" * 40)
        print("运行性能测试...")
        test_module.run_performance_test()

        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)

    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保tests目录中有test_najia.py文件")
        sys.exit(1)
    except Exception as e:
        print(f"运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
