"""批量映射性能示例

本示例演示如何使用映射器进行批量映射，并比较串行和并行处理的性能差异。
"""

import time
from dataclasses import dataclass, field
from typing import List

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


# 源对象类
@dataclass
class ProductEntity:
    """产品实体"""
    id: int
    name: str
    price: float
    description: str
    sku: str
    stock: int
    category: str
    tags: List[str]
    created_at: str
    updated_at: str


# 目标对象类
@dataclass
class ProductDTO:
    """产品DTO"""
    id: int = 0
    name: str = ""
    price: float = 0.0
    description: str = ""
    sku: str = ""
    stock: int = 0
    category: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


def create_test_data(count: int) -> List[ProductEntity]:
    """创建测试数据
    
    Args:
        count: 数据数量
        
    Returns:
        List[ProductEntity]: 产品实体列表
    """
    products = []
    for i in range(count):
        product = ProductEntity(
            id=i,
            name=f"Product {i}",
            price=10.0 + i * 0.5,
            description=f"This is product {i} with a detailed description that is long enough to simulate real-world data",
            sku=f"SKU-{i:06d}",
            stock=100 + i,
            category=f"Category {i % 10}",
            tags=[f"tag{j}" for j in range(i % 5 + 1)],
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-06-01T00:00:00Z"
        )
        products.append(product)
    return products


def batch_mapping_example():
    """批量映射性能示例"""
    print("\n===== 批量映射性能示例 =====")
    
    # 创建映射器
    mapper_builder = MapperBuilder.for_types(ProductEntity, ProductDTO)
    mapper = mapper_builder \
        .map("id", "id") \
        .map("name", "name") \
        .map("price", "price") \
        .map("description", "description") \
        .map("sku", "sku") \
        .map("stock", "stock") \
        .map("category", "category") \
        .map("tags", "tags") \
        .map("created_at", "created_at") \
        .map("updated_at", "updated_at") \
        .build()
    
    # 测试不同批量大小的性能
    batch_sizes = [10, 100, 1000, 5000]
    
    for batch_size in batch_sizes:
        print(f"\n测试批量大小: {batch_size}")
        
        # 创建测试数据
        products = create_test_data(batch_size)
        
        # 测试串行映射性能
        start_time = time.time()
        result_serial = []
        for product in products:
            result_serial.append(mapper.map(product))
        serial_time = time.time() - start_time
        print(f"串行映射耗时: {serial_time:.4f} 秒")
        
        # 测试并行映射性能（小批量）
        mapper_builder = MapperBuilder.for_types(ProductEntity, ProductDTO)
        parallel_mapper_small = mapper_builder \
            .map("id", "id") \
            .map("name", "name") \
            .map("price", "price") \
            .map("description", "description") \
            .map("sku", "sku") \
            .map("stock", "stock") \
            .map("category", "category") \
            .map("tags", "tags") \
            .map("created_at", "created_at") \
            .map("updated_at", "updated_at") \
            .configure_batch_mapping(batch_size_threshold=10, max_workers=4) \
            .build()
        
        start_time = time.time()
        result_parallel_small = parallel_mapper_small.map_list(products)
        parallel_time_small = time.time() - start_time
        print(f"并行映射耗时 (阈值=10, 工作线程=4): {parallel_time_small:.4f} 秒")
        
        # 测试并行映射性能（大批量）
        mapper_builder = MapperBuilder.for_types(ProductEntity, ProductDTO)
        parallel_mapper_large = mapper_builder \
            .map("id", "id") \
            .map("name", "name") \
            .map("price", "price") \
            .map("description", "description") \
            .map("sku", "sku") \
            .map("stock", "stock") \
            .map("category", "category") \
            .map("tags", "tags") \
            .map("created_at", "created_at") \
            .map("updated_at", "updated_at") \
            .configure_batch_mapping(batch_size_threshold=10, max_workers=8) \
            .build()
        
        start_time = time.time()
        result_parallel_large = parallel_mapper_large.map_list(products)
        parallel_time_large = time.time() - start_time
        print(f"并行映射耗时 (阈值=10, 工作线程=8): {parallel_time_large:.4f} 秒")
        
        # 计算性能提升
        speedup_small = serial_time / parallel_time_small if parallel_time_small > 0 else 0
        speedup_large = serial_time / parallel_time_large if parallel_time_large > 0 else 0
        print(f"性能提升 (4线程): {speedup_small:.2f}x")
        print(f"性能提升 (8线程): {speedup_large:.2f}x")
        
        # 验证结果正确性
        is_equal = len(result_serial) == len(result_parallel_small) == len(result_parallel_large)
        print(f"结果数量一致: {is_equal}")
        
        if is_equal and len(result_serial) > 0:
            sample_index = min(5, len(result_serial) - 1)
            print(f"\n样本数据 (索引 {sample_index}):")
            print(f"串行结果: ID={result_serial[sample_index].id}, 名称={result_serial[sample_index].name}")
            print(f"并行结果 (4线程): ID={result_parallel_small[sample_index].id}, 名称={result_parallel_small[sample_index].name}")
            print(f"并行结果 (8线程): ID={result_parallel_large[sample_index].id}, 名称={result_parallel_large[sample_index].name}")
    
    print("\n===== 批量映射性能示例结束 =====")


if __name__ == "__main__":
    batch_mapping_example() 