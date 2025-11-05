"""自动映射示例。

本示例展示了如何使用映射器系统的自动映射功能，包括：
1. 创建具有相同字段名的源对象和目标对象类
2. 使用MapperBuilder的自动映射功能
3. 展示自动映射与显式映射的组合使用
4. 处理自动映射中的异常情况
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
import time

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


# 源对象类
@dataclass
class ProductEntity:
    """产品实体类（源对象）"""
    id: int = 0
    name: str = ""
    description: str = ""
    price: float = 0.0
    category: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)


# 目标对象类 - 大部分字段名与源对象相同，便于自动映射
@dataclass
class ProductDTO:
    """产品DTO类（目标对象）"""
    id: int = 0                                  # 与源对象字段名相同
    name: str = ""                               # 与源对象字段名相同
    description: str = ""                        # 与源对象字段名相同
    price: float = 0.0                           # 与源对象字段名相同
    category: str = ""                           # 与源对象字段名相同
    tags: List[str] = field(default_factory=list)  # 与源对象字段名相同
    created_at: str = ""                         # 与源对象字段名相同，但类型不同
    modified_at: Optional[str] = None            # 字段名不同，需要显式映射
    status: bool = True                          # 字段名不同，需要显式映射
    additional_info: Dict[str, str] = field(default_factory=dict)  # 字段名不同，需要显式映射


def auto_mapping_example():
    """自动映射示例"""
    print("\n=== 自动映射示例 ===")
    
    try:
        # 创建源对象
        product_entity = ProductEntity(
            id=101,
            name="智能手表",
            description="高性能智能手表，支持心率监测和运动追踪",
            price=299.99,
            category="电子产品",
            tags=["智能设备", "运动", "健康"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True,
            metadata={"brand": "TechFit", "model": "SW-200", "warranty": "2年"}
        )
        
        print(f"源对象: {product_entity}")
        time.sleep(0.1)  # 添加短暂延迟，确保输出正确显示
        
        # 1. 仅使用自动映射（不处理类型转换和不同名称的字段）
        print("\n" + "-" * 50)
        print("1. 仅使用自动映射:")
        print("-" * 50)
        try:
            auto_mapper = MapperBuilder.for_types(ProductEntity, ProductDTO) \
                .auto_map() \
                .build()
            
            auto_dto = auto_mapper.map(product_entity)
            print(f"自动映射结果: {auto_dto}")
            print("注意: 自动映射只处理了名称相同的字段，但created_at因类型不同而失败，且不同名称的字段未被映射")
            
        except Exception as e:
            print(f"自动映射异常: {type(e).__name__}")
            print(f"异常消息: {str(e)}")
        
        time.sleep(0.1)  # 添加短暂延迟，确保输出正确显示
        
        # 2. 自动映射 + 显式映射 + 类型转换
        print("\n" + "-" * 50)
        print("2. 自动映射 + 显式映射 + 类型转换:")
        print("-" * 50)
        combined_mapper = MapperBuilder.for_types(ProductEntity, ProductDTO) \
            .auto_map() \
            .map_custom("created_at", lambda p: p.created_at.isoformat() if p.created_at else "") \
            .map("updated_at", "modified_at") \
            .map_custom("modified_at", lambda p: p.updated_at.isoformat() if p.updated_at else None) \
            .map("is_active", "status") \
            .map("metadata", "additional_info") \
            .build()
        
        combined_dto = combined_mapper.map(product_entity)
        
        print("自动映射 + 显式映射结果:")
        print(f"ID: {combined_dto.id}")
        print(f"名称: {combined_dto.name}")
        print(f"描述: {combined_dto.description}")
        print(f"价格: {combined_dto.price}")
        print(f"分类: {combined_dto.category}")
        print(f"标签: {combined_dto.tags}")
        print(f"创建时间: {combined_dto.created_at}")
        print(f"修改时间: {combined_dto.modified_at}")
        print(f"状态: {combined_dto.status}")
        print("附加信息:")
        for key, value in combined_dto.additional_info.items():
            print(f"  {key}: {value}")
        
        time.sleep(0.1)  # 添加短暂延迟，确保输出正确显示
        
        # 3. 演示自动映射的限制 - 字段类型不兼容
        print("\n" + "-" * 50)
        print("3. 演示自动映射的限制 - 字段类型不兼容:")
        print("-" * 50)
        try:
            # 创建一个目标类，其中一个字段与源类型不兼容
            @dataclass
            class IncompatibleDTO:
                id: int = 0
                name: str = ""
                price: str = ""  # 注意这里类型是str，而源对象中是float
            
            incompatible_mapper = MapperBuilder.for_types(ProductEntity, IncompatibleDTO) \
                .auto_map() \
                .build()
            
            incompatible_dto = incompatible_mapper.map(product_entity)
            print(f"不兼容类型映射结果: {incompatible_dto}")
            
        except Exception as e:
            print(f"类型不兼容异常: {type(e).__name__}")
            print(f"异常消息: {str(e)}")
        
        time.sleep(0.1)  # 添加短暂延迟，确保输出正确显示
        
        # 4. 演示自动映射的优先级
        print("\n" + "-" * 50)
        print("4. 演示自动映射与显式映射的优先级:")
        print("-" * 50)
        
        # 先创建一个只使用自动映射的映射器，查看原始映射结果
        auto_only_mapper = MapperBuilder.for_types(ProductEntity, ProductDTO) \
            .auto_map() \
            .build()
        
        auto_only_dto = auto_only_mapper.map(product_entity)
        print(f"自动映射结果 - 名称字段: {auto_only_dto.name}")
        
        # 再创建一个使用自动映射 + 显式映射的映射器，展示显式映射覆盖自动映射
        priority_mapper = MapperBuilder.for_types(ProductEntity, ProductDTO) \
            .auto_map() \
            .map_custom("name", lambda p: f"自定义前缀: {p.name}") \
            .build()
        
        priority_dto = priority_mapper.map(product_entity)
        print(f"自动映射 + 显式映射结果 - 名称字段: {priority_dto.name}")
        print("注意: 显式映射的优先级高于自动映射")
        
    except Exception as e:
        print(f"映射过程中发生错误: {str(e)}")


if __name__ == "__main__":
    auto_mapping_example() 