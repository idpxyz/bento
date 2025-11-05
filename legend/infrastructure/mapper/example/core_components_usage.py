"""核心组件使用示例。

本示例展示了映射器系统的三个核心组件（Mapper、MapperBuilder、MapperRegistry）的综合使用，包括：
1. 使用MapperBuilder创建和配置映射器
2. 将映射器注册到MapperRegistry
3. 从MapperRegistry获取映射器并使用
4. 在实际应用场景中的最佳实践
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import uuid

from idp.framework.infrastructure.mapper import MapperBuilder
from idp.framework.infrastructure.mapper.registry import dto_mapper_registry, po_mapper_registry, vo_mapper_registry
from idp.framework.infrastructure.mapper.core.converter import type_converter_registry

# 注册自定义转换器，解决str到NoneType的转换问题
type_converter_registry.register_converter(str, type(None), lambda s: None)

# 领域实体
@dataclass
class OrderEntity:
    """订单领域实体"""
    id: str = ""
    customer_id: str = ""
    order_date: datetime = field(default_factory=datetime.now)
    total_amount: float = 0.0
    status: str = "PENDING"
    items: List[Dict] = field(default_factory=list)
    shipping_address: Dict = field(default_factory=dict)
    payment_info: Dict = field(default_factory=dict)
    notes: Optional[str] = None
    is_priority: bool = False
    last_updated: Optional[datetime] = None


# DTO对象 - 用于API交互
@dataclass
class OrderDTO:
    """订单DTO"""
    order_id: str = ""  # 字段名不同
    customer_id: str = ""  # 字段名相同
    created_at: str = ""  # 字段名不同，类型不同
    amount: float = 0.0  # 字段名不同
    status: str = "PENDING"  # 字段名相同
    items: List[Dict] = field(default_factory=list)  # 字段名相同
    shipping_details: Dict = field(default_factory=dict)  # 字段名不同
    payment_details: Dict = field(default_factory=dict)  # 字段名不同
    comments: Optional[str] = None  # 字段名不同
    priority: bool = False  # 字段名不同
    updated_at: str = ""  # 字段名不同，类型不同


# PO对象 - 用于数据库持久化
@dataclass
class OrderPO:
    """订单持久化对象"""
    id: str = ""
    customer_id: str = ""
    order_date: str = ""  # 存储为字符串
    total_amount: float = 0.0
    status: str = "PENDING"
    items_json: str = "{}"  # 存储为JSON字符串
    shipping_address_json: str = "{}"  # 存储为JSON字符串
    payment_info_json: str = "{}"  # 存储为JSON字符串
    notes: Optional[str] = None
    is_priority: bool = False
    last_updated: str = ""  # 存储为字符串


def core_components_usage_example():
    """核心组件使用示例"""
    print("\n=== 核心组件使用示例 ===")
    
    try:
        # 创建示例订单实体
        order = OrderEntity(
            id=str(uuid.uuid4()),
            customer_id="CUST-12345",
            order_date=datetime.now(),
            total_amount=129.99,  # 这个值与计算结果不同，用于对比
            status="PROCESSING",
            items=[
                {"product_id": "PROD-001", "name": "笔记本电脑", "quantity": 1, "price": 99.99},
                {"product_id": "PROD-002", "name": "鼠标", "quantity": 2, "price": 25.00}  # 修改数量为2
            ],
            shipping_address={
                "recipient": "张三",
                "street": "中关村大街1号",
                "city": "北京",
                "postal_code": "100080",
                "country": "中国"
            },
            payment_info={
                "method": "信用卡",
                "card_last4": "1234",
                "paid": True
            },
            notes="请在工作时间送货",
            is_priority=True,
            last_updated=datetime.now()
        )
        
        print("创建的订单实体:")
        print(f"ID: {order.id}")
        print(f"客户ID: {order.customer_id}")
        print(f"订单日期: {order.order_date}")
        print(f"总金额: {order.total_amount}")
        print(f"状态: {order.status}")
        print(f"商品数量: {len(order.items)}")
        print(f"优先级: {'是' if order.is_priority else '否'}")
        
        # 第一部分: 使用MapperBuilder创建映射器
        print("\n1. 使用MapperBuilder创建映射器")
        
        # 创建领域实体到DTO的映射器
        order_dto_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \
            .map("id", "order_id") \
            .map("customer_id", "customer_id") \
            .map_custom("created_at", lambda o: o.order_date.isoformat() if o.order_date else "") \
            .map("total_amount", "amount") \
            .map("status", "status") \
            .map("items", "items") \
            .map("shipping_address", "shipping_details") \
            .map("payment_info", "payment_details") \
            .map("notes", "comments") \
            .map("is_priority", "priority") \
            .map_custom("updated_at", lambda o: o.last_updated.isoformat() if o.last_updated else "") \
            .build()
        
        # 创建领域实体到PO的映射器
        import json
        
        order_po_mapper = MapperBuilder.for_types(OrderEntity, OrderPO) \
            .map("id", "id") \
            .map("customer_id", "customer_id") \
            .map_custom("order_date", lambda o: o.order_date.isoformat() if o.order_date else "") \
            .map("total_amount", "total_amount") \
            .map("status", "status") \
            .map_custom("items_json", lambda o: json.dumps(o.items)) \
            .map_custom("shipping_address_json", lambda o: json.dumps(o.shipping_address)) \
            .map_custom("payment_info_json", lambda o: json.dumps(o.payment_info)) \
            .map("notes", "notes") \
            .map("is_priority", "is_priority") \
            .map_custom("last_updated", lambda o: o.last_updated.isoformat() if o.last_updated else "") \
            .build()
        
        # 使用映射器进行映射
        order_dto = order_dto_mapper.map(order)
        order_po = order_po_mapper.map(order)
        
        print("\n使用MapperBuilder创建的映射器进行映射:")
        print(f"DTO - 订单ID: {order_dto.order_id}")
        print(f"DTO - 创建时间: {order_dto.created_at}")
        print(f"DTO - 金额: {order_dto.amount}")
        print(f"DTO - 优先级: {order_dto.priority}")
        
        print(f"\nPO - ID: {order_po.id}")
        print(f"PO - 订单日期: {order_po.order_date}")
        print(f"PO - 商品JSON: {order_po.items_json[:50] if hasattr(order_po, 'items_json') and order_po.items_json else '{}'}...")
        
        # 添加自动映射示例
        print("\n1.1 自动映射示例")
        
        # 创建使用自动映射的DTO映射器
        auto_dto_mapper = (MapperBuilder.for_types(OrderEntity, OrderDTO)
            .map("id", "order_id")
            .map_custom("created_at", lambda o: o.order_date.isoformat() if o.order_date else "")
            .map_custom("amount", lambda o: sum(item.get("price", 0) * item.get("quantity", 1) for item in o.items) if o.items else o.total_amount)  # 通过计算订单项目得到金额
            .map("shipping_address", "shipping_details")
            .map("payment_info", "payment_details")
            .map("notes", "comments")
            .map("is_priority", "priority")
            .map_custom("updated_at", lambda o: o.last_updated.isoformat() if o.last_updated else "")
            .auto_map()  # 自动映射其余相同名称的字段（如customer_id, status, items）
            .build())
        
        # 使用自动映射器
        auto_order_dto = auto_dto_mapper.map(order)
        
        print("使用自动映射的映射器:")
        print(f"DTO - 订单ID: {auto_order_dto.order_id}")
        print(f"DTO - 客户ID: {auto_order_dto.customer_id}  # 通过自动映射")
        print(f"DTO - 状态: {auto_order_dto.status}  # 通过自动映射")
        print(f"DTO - 商品数量: {len(auto_order_dto.items)}  # 通过自动映射")
        print(f"DTO - 计算的金额: {auto_order_dto.amount}  # 通过计算订单项目得到 (99.99 + 2*25.00 = 149.99)")
        print(f"DTO - 原始总金额: {order.total_amount}  # 原始订单实体中的总金额")
        
        # 创建使用自动映射的PO映射器
        auto_po_mapper = (MapperBuilder.for_types(OrderEntity, OrderPO)
            .map_custom("order_date", lambda o: o.order_date.isoformat() if o.order_date else "")
            .map_custom("items_json", lambda o: json.dumps(o.items))
            .map_custom("shipping_address_json", lambda o: json.dumps(o.shipping_address))
            .map_custom("payment_info_json", lambda o: json.dumps(o.payment_info))
            .map_custom("last_updated", lambda o: o.last_updated.isoformat() if o.last_updated else "")
            .auto_map()  # 自动映射其余相同名称的字段（如id, customer_id, total_amount, status, notes, is_priority）
            .build())
        
        # 使用自动映射的PO映射器
        auto_order_po = auto_po_mapper.map(order)
        
        print("\n使用自动映射的PO映射器:")
        print(f"PO - ID: {auto_order_po.id}  # 通过自动映射")
        print(f"PO - 客户ID: {auto_order_po.customer_id}  # 通过自动映射")
        print(f"PO - 状态: {auto_order_po.status}  # 通过自动映射")
        print(f"PO - 总金额: {auto_order_po.total_amount}  # 通过自动映射")
        
        # 第二部分: 将映射器注册到MapperRegistry
        print("\n2. 将映射器注册到MapperRegistry")
        
        # 注册到DTO映射器注册表
        dto_mapper_registry.register_domain_to_dto(OrderEntity, OrderDTO, order_dto_mapper)
        print("已将OrderEntity->OrderDTO映射器注册到DTO注册表")
        
        # 注册到PO映射器注册表
        po_mapper_registry.register_domain_to_po(OrderEntity, OrderPO, order_po_mapper)
        print("已将OrderEntity->OrderPO映射器注册到PO注册表")
        
        # 第三部分: 从MapperRegistry获取映射器
        print("\n3. 从MapperRegistry获取映射器")
        
        # 从DTO注册表获取映射器
        retrieved_dto_mapper = dto_mapper_registry.get_domain_to_dto(OrderEntity, OrderDTO)
        print(f"从DTO注册表获取的映射器: {retrieved_dto_mapper is not None}")
        
        # 从PO注册表获取映射器
        retrieved_po_mapper = po_mapper_registry.get_domain_to_po(OrderEntity, OrderPO)
        print(f"从PO注册表获取的映射器: {retrieved_po_mapper is not None}")
        
        # 使用获取的映射器进行映射
        if retrieved_dto_mapper and retrieved_po_mapper:
            new_order = OrderEntity(
                id=str(uuid.uuid4()),
                customer_id="CUST-67890",
                order_date=datetime.now(),
                total_amount=59.99,
                status="NEW",
                items=[{"product_id": "PROD-003", "name": "键盘", "quantity": 1, "price": 59.99}]
            )
            
            new_dto = retrieved_dto_mapper.map(new_order)
            new_po = retrieved_po_mapper.map(new_order)
            
            print("\n使用从注册表获取的映射器进行映射:")
            print(f"新DTO - 订单ID: {new_dto.order_id}")
            print(f"新DTO - 客户ID: {new_dto.customer_id}")
            print(f"新DTO - 金额: {new_dto.amount}")
            
            print(f"\n新PO - ID: {new_po.id}")
            print(f"新PO - 客户ID: {new_po.customer_id}")
            print(f"新PO - 总金额: {new_po.total_amount}")
        
        # 第四部分: 实际应用场景示例
        print("\n4. 实际应用场景示例")
        
        # 模拟服务层代码
        class OrderService:
            def create_order(self, order_dto: OrderDTO) -> OrderDTO:
                # 1. 手动将DTO转换为领域实体
                order_entity = OrderEntity(
                    id=order_dto.order_id if order_dto.order_id else str(uuid.uuid4()),
                    customer_id=order_dto.customer_id,
                    order_date=datetime.fromisoformat(order_dto.created_at) if order_dto.created_at else datetime.now(),
                    total_amount=order_dto.amount,
                    status=order_dto.status,
                    items=order_dto.items,
                    shipping_address=order_dto.shipping_details,
                    payment_info=order_dto.payment_details,
                    notes=order_dto.comments,
                    is_priority=order_dto.priority
                )
                
                # 2. 应用领域逻辑
                order_entity.status = "CONFIRMED"
                order_entity.last_updated = datetime.now()
                
                # 3. 持久化领域实体
                # 3.1 从PO注册表获取领域实体到PO的映射器
                domain_to_po_mapper = po_mapper_registry.get_domain_to_po(OrderEntity, OrderPO)
                
                # 3.2 将领域实体转换为PO
                order_po = domain_to_po_mapper.map(order_entity)
                
                # 3.3 模拟保存到数据库
                print(f"保存订单到数据库: {order_po.id}")
                
                # 4. 返回更新后的DTO
                # 4.1 从DTO注册表获取领域实体到DTO的映射器
                domain_to_dto_mapper = dto_mapper_registry.get_domain_to_dto(OrderEntity, OrderDTO)
                
                # 4.2 将领域实体转换为DTO
                updated_dto = domain_to_dto_mapper.map(order_entity)
                
                return updated_dto
        
        # 模拟API请求
        new_order_dto = OrderDTO(
            order_id="",  # 新订单，ID为空
            customer_id="CUST-99999",
            created_at=datetime.now().isoformat(),
            amount=199.99,
            status="PENDING",
            items=[{"product_id": "PROD-004", "name": "显示器", "quantity": 1, "price": 199.99}],
            shipping_details={
                "recipient": "李四",
                "street": "人民路100号",
                "city": "上海",
                "postal_code": "200001",
                "country": "中国"
            },
            priority=True
        )
        
        # 使用服务处理订单
        order_service = OrderService()
        processed_order_dto = order_service.create_order(new_order_dto)
        
        print("\n处理后的订单DTO:")
        print(f"订单ID: {processed_order_dto.order_id}")
        print(f"客户ID: {processed_order_dto.customer_id}")
        print(f"状态: {processed_order_dto.status}")  # 应该是 "CONFIRMED"
        print(f"更新时间: {processed_order_dto.updated_at}")
        
        print("\n核心组件使用示例完成!")
        
    except Exception as e:
        print(f"示例执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    core_components_usage_example() 