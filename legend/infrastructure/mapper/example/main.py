"""映射器示例主程序

本程序运行所有映射器示例，展示映射器的各种功能。
"""

import sys
from typing import Callable, List, Tuple

from idp.framework.infrastructure.mapper.example.basic_mapping import basic_mapping_example
from idp.framework.infrastructure.mapper.example.nested_mapping import nested_mapping_example
from idp.framework.infrastructure.mapper.example.collection_mapping import collection_mapping_example
from idp.framework.infrastructure.mapper.example.custom_mapping import custom_mapping_example
from idp.framework.infrastructure.mapper.example.bidirectional_mapping import bidirectional_mapping_example
from idp.framework.infrastructure.mapper.example.domain_vo_mapping import domain_vo_mapping_example
from idp.framework.infrastructure.mapper.example.auto_mapping import auto_mapping_example
from idp.framework.infrastructure.mapper.example.circular_reference_mapping import circular_reference_mapping_example
from idp.framework.infrastructure.mapper.example.batch_mapping import batch_mapping_example
from idp.framework.infrastructure.mapper.example.type_conversion_mapping import type_conversion_mapping_example
from idp.framework.infrastructure.mapper.example.test_mapper_builder import test_mapper_builder
from idp.framework.infrastructure.mapper.example.core_components_usage import core_components_usage_example


def run_all_examples() -> None:
    """运行所有映射器示例"""
    print("=" * 80)
    print("IDP 映射器系统示例")
    print("=" * 80)
    
    # 定义所有示例及其名称
    examples: List[Tuple[str, Callable[[], None]]] = [
        ("基本映射", basic_mapping_example),
        ("嵌套对象映射", nested_mapping_example),
        ("集合映射", collection_mapping_example),
        ("自定义映射", custom_mapping_example),
        ("双向映射", bidirectional_mapping_example),
        ("领域对象-值对象映射", domain_vo_mapping_example),
        ("自动映射", auto_mapping_example),
        ("循环引用映射", circular_reference_mapping_example),
        ("批量映射性能", batch_mapping_example),
        ("类型转换映射", type_conversion_mapping_example),
        ("测试MapperBuilder", test_mapper_builder),
        ("核心组件综合使用", core_components_usage_example)
    ]
    
    # 运行每个示例
    for name, example_func in examples:
        print(f"\n\n{'=' * 40}")
        print(f"  开始运行: {name}")
        print(f"{'=' * 40}")
        
        try:
            example_func()
            print(f"\n✓ {name} 示例运行成功")
        except Exception as e:
            print(f"\n✗ {name} 示例运行失败: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    print("\n\n======================================")
    print("       所有映射器示例运行完成")
    print("======================================")


if __name__ == "__main__":
    run_all_examples() 