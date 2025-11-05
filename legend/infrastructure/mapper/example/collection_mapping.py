"""集合映射示例。

本示例展示了如何使用映射器系统处理集合类型的映射，包括：
1. 列表映射
2. 集合映射
3. 字典映射
4. 嵌套集合映射
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Set, Dict, Optional
from uuid import UUID, uuid4

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


# 源对象类
@dataclass
class ProductEntity:
    """产品实体类（源对象）"""
    id: UUID
    name: str
    price: float
    description: str
    sku: str
    stock: int
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class OrderEntity:
    """订单实体类（源对象）"""
    id: UUID
    customer_id: UUID
    order_date: datetime
    items: List[ProductEntity] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    notes: Optional[str] = None


# 目标对象类
@dataclass
class ProductDTO:
    """产品DTO类（目标对象）"""
    product_id: str = ""
    product_name: str = ""
    unit_price: float = 0.0
    product_description: str = ""
    product_sku: str = ""
    available_stock: int = 0
    product_attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class OrderDTO:
    """订单DTO类（目标对象）"""
    order_id: str = ""
    customer_id: str = ""
    date: str = ""
    products: List[ProductDTO] = field(default_factory=list)
    order_tags: Set[str] = field(default_factory=set)
    additional_notes: Optional[str] = None


def collection_mapping_example():
    """集合映射示例"""
    print("\n=== 集合映射示例 ===")
    
    try:
        # 创建产品实体
        product1 = ProductEntity(
            id=uuid4(),
            name="Smartphone",
            price=799.99,
            description="Latest model smartphone with advanced features",
            sku="PHONE-12345",
            stock=50,
            attributes={
                "color": "black",
                "storage": "128GB",
                "screen": "6.5 inch"
            }
        )
        
        product2 = ProductEntity(
            id=uuid4(),
            name="Wireless Headphones",
            price=149.99,
            description="Noise cancelling wireless headphones",
            sku="AUDIO-67890",
            stock=30,
            attributes={
                "color": "white",
                "battery": "20 hours",
                "type": "over-ear"
            }
        )
        
        product3 = ProductEntity(
            id=uuid4(),
            name="Tablet",
            price=349.99,
            description="10-inch tablet with high resolution display",
            sku="TAB-54321",
            stock=25,
            attributes={
                "color": "silver",
                "storage": "64GB",
                "screen": "10 inch"
            }
        )
        
        # 创建订单实体
        order_entity = OrderEntity(
            id=uuid4(),
            customer_id=uuid4(),
            order_date=datetime.now(),
            items=[product1, product2, product3],
            tags={"electronics", "online", "priority"},
            notes="Customer requested express shipping"
        )
        
        print(f"源订单实体: {order_entity}")
        print(f"订单包含 {len(order_entity.items)} 个产品")
        
        # 手动执行映射
        try:
            # 手动创建订单DTO
            order_dto = OrderDTO()
            
            # 手动映射简单字段
            order_dto.order_id = str(order_entity.id)
            order_dto.customer_id = str(order_entity.customer_id)
            order_dto.date = order_entity.order_date.isoformat()
            order_dto.additional_notes = order_entity.notes
            
            # 手动映射集合 - 标签集合
            order_dto.order_tags = order_entity.tags.copy()
            
            # 手动映射集合 - 产品列表
            for product_entity in order_entity.items:
                # 为每个产品创建DTO
                product_dto = ProductDTO()
                
                # 映射产品字段
                product_dto.product_id = str(product_entity.id)
                product_dto.product_name = product_entity.name
                product_dto.unit_price = product_entity.price
                product_dto.product_description = product_entity.description
                product_dto.product_sku = product_entity.sku
                product_dto.available_stock = product_entity.stock
                product_dto.product_attributes = product_entity.attributes.copy()
                
                # 将产品DTO添加到订单DTO的产品列表中
                order_dto.products.append(product_dto)
            
            # 打印映射结果
            print("\n手动映射结果:")
            print(f"订单ID: {order_dto.order_id}")
            print(f"客户ID: {order_dto.customer_id}")
            print(f"日期: {order_dto.date}")
            print(f"标签: {order_dto.order_tags}")
            print(f"备注: {order_dto.additional_notes}")
            
            print(f"\n映射后的产品列表 ({len(order_dto.products)} 个产品):")
            for i, product in enumerate(order_dto.products, 1):
                print(f"\n产品 {i}:")
                print(f"  ID: {product.product_id}")
                print(f"  名称: {product.product_name}")
                print(f"  价格: ${product.unit_price:.2f}")
                print(f"  描述: {product.product_description}")
                print(f"  SKU: {product.product_sku}")
                print(f"  库存: {product.available_stock}")
                print(f"  属性:")
                for key, value in product.product_attributes.items():
                    print(f"    {key}: {value}")
            
            # 显示MapperBuilder配置示例（不执行）
            print("\nMapperBuilder的配置示例（不执行）:")
            print("""
        # 创建产品映射器
        product_mapper = MapperBuilder.for_types(ProductEntity, ProductDTO) \\
            .map_custom("product_id", lambda p: str(p.id)) \\
            .map("name", "product_name") \\
            .map("price", "unit_price") \\
            .map("description", "product_description") \\
            .map("sku", "product_sku") \\
            .map("stock", "available_stock") \\
            .map("attributes", "product_attributes") \\
            .build()
        
        # 创建订单映射器，使用产品映射器处理集合元素
        order_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \\
            .map_custom("order_id", lambda o: str(o.id)) \\
            .map_custom("customer_id", lambda o: str(o.customer_id)) \\
            .map_custom("date", lambda o: o.order_date.isoformat()) \\
            .map_collection("items", "products", product_mapper) \\
            .map("tags", "order_tags") \\
            .map("notes", "additional_notes") \\
            .build()
            """)
            
        except Exception as e:
            print(f"手动映射过程中发生错误: {str(e)}")
        
        # 演示集合映射中的异常处理
        print("\n演示集合映射中的异常处理:")
        print("1. 尝试映射不存在的字段:")
        print("""
        # 错误示例 - 尝试映射不存在的字段
        invalid_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \\
            .map_custom("order_id", lambda o: str(o.id)) \\
            .map("non_existent_field", "some_field")  # 这个字段不存在
            .build()
        """)
        
        print("\n2. 没有为集合元素提供映射器:")
        print("""
        # 错误示例 - 没有为集合元素提供映射器
        invalid_collection_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \\
            .map_collection("items", "products")  # 缺少元素映射器
            .build()
        """)
            
    except Exception as e:
        print(f"映射过程中发生错误: {str(e)}")


if __name__ == "__main__":
    collection_mapping_example() 