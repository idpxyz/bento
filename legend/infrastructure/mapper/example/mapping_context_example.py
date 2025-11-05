"""映射上下文(MappingContext)使用示例。

本示例展示了MappingContext在以下场景中的应用：
1. 处理循环引用 - 避免无限递归
2. 对象跟踪 - 避免重复映射同一对象
3. 共享状态 - 在映射过程中传递信息
4. 在DDD中的应用 - 处理聚合根和实体之间的关系
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

from idp.framework.infrastructure.mapper import MapperBuilder
from idp.framework.infrastructure.mapper.core.context import MappingContext
from idp.framework.infrastructure.mapper.registry import dto_mapper_registry, po_mapper_registry


# ===== 1. 定义领域模型 =====

# 1.1 定义具有循环引用的领域模型
@dataclass
class Customer:
    """客户聚合根"""
    id: str
    name: str
    email: str
    address: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    orders: List['Order'] = field(default_factory=list)

    def add_order(self, order: 'Order') -> None:
        """添加订单"""
        self.orders.append(order)
        order.customer = self  # 建立双向关系


@dataclass
class Order:
    """订单聚合根"""
    id: str
    order_date: datetime
    total_amount: float
    status: str
    items: List['OrderItem'] = field(default_factory=list)
    customer: Optional[Customer] = None

    def add_item(self, item: 'OrderItem') -> None:
        """添加订单项"""
        self.items.append(item)
        item.order = self  # 建立双向关系


@dataclass
class OrderItem:
    """订单项实体"""
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    order: Optional[Order] = None

    @property
    def total_price(self) -> float:
        """计算总价"""
        return self.quantity * self.unit_price


# 1.2 定义DTO模型
@dataclass
class CustomerDTO:
    """客户DTO"""
    customer_id: str
    customer_name: str
    email: str
    address: Dict[str, str] = field(default_factory=dict)
    registration_date: str = ""
    orders: List['OrderDTO'] = field(default_factory=list)


@dataclass
class OrderDTO:
    """订单DTO"""
    order_id: str
    order_date: str
    amount: float
    status: str
    items: List['OrderItemDTO'] = field(default_factory=list)
    customer: Optional[CustomerDTO] = None


@dataclass
class OrderItemDTO:
    """订单项DTO"""
    item_id: str
    product_id: str
    product_name: str
    quantity: int
    price: float
    total: float = 0.0
    order: Optional[OrderDTO] = None


# 1.3 定义持久化对象模型
@dataclass
class CustomerPO:
    """客户持久化对象"""
    id: str
    name: str
    email: str
    address_json: str = "{}"
    created_at: str = ""
    # 不存储订单关系，通过外键在订单表中表示


@dataclass
class OrderPO:
    """订单持久化对象"""
    id: str
    customer_id: str  # 外键
    order_date: str
    total_amount: float
    status: str
    # 不存储订单项关系，通过外键在订单项表中表示


@dataclass
class OrderItemPO:
    """订单项持久化对象"""
    id: str
    order_id: str  # 外键
    product_id: str
    product_name: str
    quantity: int
    unit_price: float


# ===== 2. 创建映射器 =====

def create_mappers():
    """创建并注册映射器"""
    # 2.1 创建领域模型到DTO的映射器
    # 注意：由于循环引用，我们需要先创建映射器，然后再配置它们

    # 先创建基本映射器
    customer_dto_mapper = (MapperBuilder.for_types(Customer, CustomerDTO)
                           .map("id", "customer_id")
                           .map("name", "customer_name")
                           .map("email", "email")
                           .map("address", "address")
                           .map_custom("registration_date", lambda c: c.created_at.isoformat() if c.created_at else "")
                           # 暂时不映射orders，避免循环引用问题
                           .build())

    order_dto_mapper = (MapperBuilder.for_types(Order, OrderDTO)
                        .map("id", "order_id")
                        .map_custom("order_date", lambda o: o.order_date.isoformat() if o.order_date else "")
                        .map("total_amount", "amount")
                        .map("status", "status")
                        # 暂时不映射items和customer，避免循环引用问题
                        .build())

    order_item_dto_mapper = (MapperBuilder.for_types(OrderItem, OrderItemDTO)
                             .map("id", "item_id")
                             .map("product_id", "product_id")
                             .map("product_name", "product_name")
                             .map("quantity", "quantity")
                             .map("unit_price", "price")
                             .map_custom("total", lambda i: i.quantity * i.unit_price)
                             # 暂时不映射order，避免循环引用问题
                             .build())

    # 2.2 创建领域模型到PO的映射器
    customer_po_mapper = (MapperBuilder.for_types(Customer, CustomerPO)
                          .map("id", "id")
                          .map("name", "name")
                          .map("email", "email")
                          .map_custom("address_json", lambda c: json.dumps(c.address))
                          .map_custom("created_at", lambda c: c.created_at.isoformat() if c.created_at else "")
                          .build())

    order_po_mapper = (MapperBuilder.for_types(Order, OrderPO)
                       .map("id", "id")
                       .map_custom("customer_id", lambda o: o.customer.id if o.customer else "")
                       .map_custom("order_date", lambda o: o.order_date.isoformat() if o.order_date else "")
                       .map("total_amount", "total_amount")
                       .map("status", "status")
                       .build())

    order_item_po_mapper = (MapperBuilder.for_types(OrderItem, OrderItemPO)
                            .map("id", "id")
                            .map_custom("order_id", lambda i: i.order.id if i.order else "")
                            .map("product_id", "product_id")
                            .map("product_name", "product_name")
                            .map("quantity", "quantity")
                            .map("unit_price", "unit_price")
                            .build())

    # 2.3 注册映射器
    dto_mapper_registry.register_domain_to_dto(Customer, CustomerDTO, customer_dto_mapper)
    dto_mapper_registry.register_domain_to_dto(Order, OrderDTO, order_dto_mapper)
    dto_mapper_registry.register_domain_to_dto(OrderItem, OrderItemDTO, order_item_dto_mapper)

    po_mapper_registry.register_domain_to_po(Customer, CustomerPO, customer_po_mapper)
    po_mapper_registry.register_domain_to_po(Order, OrderPO, order_po_mapper)
    po_mapper_registry.register_domain_to_po(OrderItem, OrderItemPO, order_item_po_mapper)

    return {
        "customer_dto_mapper": customer_dto_mapper,
        "order_dto_mapper": order_dto_mapper,
        "order_item_dto_mapper": order_item_dto_mapper,
        "customer_po_mapper": customer_po_mapper,
        "order_po_mapper": order_po_mapper,
        "order_item_po_mapper": order_item_po_mapper
    }


# ===== 3. 示例场景 =====

def create_sample_data():
    """创建示例数据"""
    # 创建客户
    customer = Customer(
        id="CUST-" + str(uuid.uuid4())[:8],
        name="张三",
        email="zhangsan@example.com",
        address={
            "street": "中关村大街1号",
            "city": "北京",
            "postal_code": "100080",
            "country": "中国"
        },
        created_at=datetime.now()
    )

    # 创建订单
    order = Order(
        id="ORD-" + str(uuid.uuid4())[:8],
        order_date=datetime.now(),
        total_amount=0,  # 初始为0，后面计算
        status="PENDING"
    )

    # 创建订单项
    item1 = OrderItem(
        id="ITEM-" + str(uuid.uuid4())[:8],
        product_id="PROD-001",
        product_name="笔记本电脑",
        quantity=1,
        unit_price=5999.00
    )

    item2 = OrderItem(
        id="ITEM-" + str(uuid.uuid4())[:8],
        product_id="PROD-002",
        product_name="无线鼠标",
        quantity=2,
        unit_price=99.50
    )

    # 建立关系
    customer.add_order(order)
    order.add_item(item1)
    order.add_item(item2)

    # 计算订单总金额
    order.total_amount = sum(item.total_price for item in order.items)

    return customer, order, [item1, item2]


# ===== 4. 映射上下文示例 =====

def circular_reference_example(mappers):
    """循环引用处理示例
    
    本示例展示了MappingContext如何解决对象映射中的循环引用问题:
    1. 问题描述 - 当对象之间存在双向引用时，直接映射会导致无限递归
    2. 解决方案 - 使用MappingContext跟踪已映射对象，避免重复映射
    3. 实现步骤 - 先创建目标对象，注册到上下文，映射基本属性，最后手动建立关系
    4. 性能比较 - 对比有无上下文的映射性能差异
    """
    print("\n=== 1. 循环引用处理示例 ===")

    # 获取示例数据
    customer, order, items = create_sample_data()

    print(f"客户: {customer.name} (ID: {customer.id})")
    print(f"订单: {order.id}, 金额: {order.total_amount}")
    print(f"订单项: {len(items)} 项")
    print(f"循环引用验证:")
    print(f"  - 客户的第一个订单ID: {customer.orders[0].id}")
    print(f"  - 订单的客户ID: {order.customer.id}")
    print(f"  - 订单的第一个订单项ID: {order.items[0].id}")
    print(f"  - 第一个订单项的订单ID: {items[0].order.id}")

    # 不使用映射上下文 - 会导致无限递归
    print("\n1.1 不使用映射上下文的问题:")
    try:
        # 这里会导致无限递归: 客户->订单->客户->订单...
        print("  直接映射客户会导致无限递归，已注释掉相关代码")
        # customer_dto = mappers["customer_dto_mapper"].map(customer)
        print("  如果取消注释上面的代码，将导致RecursionError")
    except RecursionError as e:
        print(f"  发生递归错误: {str(e)}")

    # 错误的解决方案 - 忽略循环引用
    print("\n1.2 错误的解决方案 - 忽略循环引用:")
    print("  这种方法会丢失对象之间的关系，导致数据不完整")
    print("  例如：客户DTO中不包含订单，或订单DTO中不包含客户")
    print("  这在某些场景下可能可以接受，但在需要完整对象图的场景下是不可行的")

    # 使用映射上下文 - 正确处理循环引用
    print("\n1.3 使用映射上下文解决循环引用:")

    # 计时开始
    start_time = datetime.now()

    context = MappingContext()

    # 手动处理循环引用的步骤
    print("  步骤1: 创建目标DTO对象")
    # 1. 先创建DTO对象
    customer_dto = CustomerDTO(
        customer_id="",
        customer_name="",
        email="",
        orders=[]
    )

    order_dto = OrderDTO(
        order_id="",
        order_date="",
        amount=0,
        status="",
        items=[]
    )

    print("  步骤2: 注册对象到上下文")
    # 2. 注册对象到上下文
    context.register_mapped_object(customer, customer_dto)
    context.register_mapped_object(order, order_dto)

    print("  步骤3: 映射基本属性")
    # 3. 映射客户基本属性
    mappers["customer_dto_mapper"].map_to_target_with_context(customer, customer_dto, context)

    # 4. 映射订单基本属性
    mappers["order_dto_mapper"].map_to_target_with_context(order, order_dto, context)

    print("  步骤4: 手动建立关系")
    # 5. 手动建立关系
    customer_dto.orders.append(order_dto)
    order_dto.customer = customer_dto

    print("  步骤5: 映射子对象")
    # 6. 映射订单项
    for item in order.items:
        item_dto = OrderItemDTO(
            item_id="",
            product_id="",
            product_name="",
            quantity=0,
            price=0,
            total=0
        )
        context.register_mapped_object(item, item_dto)
        mappers["order_item_dto_mapper"].map_to_target_with_context(item, item_dto, context)
        item_dto.order = order_dto
        order_dto.items.append(item_dto)

    # 计时结束
    mapping_time = datetime.now() - start_time
    print(f"  映射耗时: {mapping_time.total_seconds() * 1000:.2f}ms")

    # 验证映射结果
    print("\n1.4 验证映射结果:")
    print(f"  客户DTO:")
    print(f"  - 客户ID: {customer_dto.customer_id}")
    print(f"  - 客户名称: {customer_dto.customer_name}")
    print(f"  - 电子邮件: {customer_dto.email}")
    print(f"  - 订单数量: {len(customer_dto.orders)}")

    if customer_dto.orders:
        order_dto = customer_dto.orders[0]
        print(f"  - 第一个订单ID: {order_dto.order_id}")
        print(f"  - 订单金额: {order_dto.amount}")
        print(f"  - 订单项数量: {len(order_dto.items)}")

        # 验证循环引用是否正确处理
        print("\n1.5 验证循环引用处理:")
        print(f"  - 客户DTO的订单引用回客户: {order_dto.customer is customer_dto}")

        if order_dto.items:
            item_dto = order_dto.items[0]
            print(f"  - 第一个订单项ID: {item_dto.item_id}")
            print(f"  - 订单项引用回订单: {item_dto.order is order_dto}")

    # 1.6 使用辅助函数简化循环引用处理
    print("\n1.6 使用辅助函数简化循环引用处理:")

    def map_with_circular_references(source, target_type, mappers, property_mappings=None):
        """处理循环引用的辅助函数
        
        Args:
            source: 源对象
            target_type: 目标类型
            mappers: 映射器字典
            property_mappings: 属性映射配置
            
        Returns:
            映射后的目标对象
        """
        # 创建上下文
        ctx = MappingContext()

        # 创建空目标对象 - 处理必填参数
        if target_type == CustomerDTO:
            target = CustomerDTO(
                customer_id="",
                customer_name="",
                email="",
                orders=[]
            )
        elif target_type == OrderDTO:
            target = OrderDTO(
                order_id="",
                order_date="",
                amount=0,
                status="",
                items=[]
            )
        elif target_type == OrderItemDTO:
            target = OrderItemDTO(
                item_id="",
                product_id="",
                product_name="",
                quantity=0,
                price=0,
                total=0
            )
        else:
            # 尝试创建无参实例，可能会失败
            try:
                target = target_type()
            except TypeError as e:
                raise ValueError(f"无法创建{target_type.__name__}的实例: {str(e)}")

        # 注册到上下文
        ctx.register_mapped_object(source, target)

        # 获取合适的映射器
        mapper_key = f"{source.__class__.__name__.lower()}_dto_mapper"
        mapper = mappers.get(mapper_key)

        if not mapper:
            raise ValueError(f"找不到映射器: {mapper_key}")

        # 映射基本属性
        mapper.map_to_target_with_context(source, target, ctx)

        # 处理自定义属性映射
        if property_mappings:
            for prop_name, mapping_func in property_mappings.items():
                setattr(target, prop_name, mapping_func(source, target, ctx))

        return target, ctx

    # 使用辅助函数映射客户
    start_time = datetime.now()

    # 定义关系映射
    def map_customer_orders(customer, customer_dto, ctx):
        """映射客户订单关系"""
        orders = []
        for order in customer.orders:
            # 创建订单DTO
            order_dto = OrderDTO(
                order_id="",
                order_date="",
                amount=0,
                status="",
                items=[]
            )
            # 注册到上下文
            ctx.register_mapped_object(order, order_dto)
            # 映射基本属性
            mappers["order_dto_mapper"].map_to_target_with_context(order, order_dto, ctx)
            # 设置关系
            order_dto.customer = customer_dto
            # 映射订单项
            for item in order.items:
                item_dto = OrderItemDTO(
                    item_id="",
                    product_id="",
                    product_name="",
                    quantity=0,
                    price=0,
                    total=0
                )
                ctx.register_mapped_object(item, item_dto)
                mappers["order_item_dto_mapper"].map_to_target_with_context(item, item_dto, ctx)
                item_dto.order = order_dto
                order_dto.items.append(item_dto)
            orders.append(order_dto)
        return orders

    # 使用辅助函数映射
    customer_dto2, _ = map_with_circular_references(
        customer,
        CustomerDTO,
        mappers,
        {"orders": map_customer_orders}
    )

    helper_time = datetime.now() - start_time
    print(f"  使用辅助函数映射耗时: {helper_time.total_seconds() * 1000:.2f}ms")

    # 验证结果
    print("  验证辅助函数映射结果:")
    print(f"  - 客户ID: {customer_dto2.customer_id}")
    print(f"  - 订单数量: {len(customer_dto2.orders)}")
    if customer_dto2.orders:
        print(f"  - 第一个订单ID: {customer_dto2.orders[0].order_id}")
        print(f"  - 订单项数量: {len(customer_dto2.orders[0].items)}")
        print(f"  - 循环引用验证: {customer_dto2.orders[0].customer is customer_dto2}")

    # 1.7 最佳实践总结
    print("\n1.7 循环引用处理最佳实践:")
    print("  1. 识别对象图中的循环引用")
    print("  2. 使用MappingContext跟踪已映射对象")
    print("  3. 先创建和注册目标对象，再映射属性")
    print("  4. 手动建立对象之间的关系")
    print("  5. 封装通用的辅助函数简化重复代码")
    print("  6. 考虑在复杂场景中使用专门的对象图映射库")


def object_tracking_example(mappers):
    """对象跟踪示例
    
    本示例展示了MappingContext如何跟踪已映射对象，避免重复映射:
    1. 对象标识 - 如何识别和跟踪对象
    2. 对象缓存 - 如何重用已映射的对象
    3. 性能优化 - 减少重复映射提高性能
    4. 一致性保证 - 确保同一个源对象映射到同一个目标对象
    5. 内存优化 - 避免创建重复对象
    """
    print("\n=== 2. 对象跟踪示例 ===")

    # 获取示例数据
    customer, order, items = create_sample_data()

    # 2.1 基本对象跟踪
    print("\n2.1 基本对象跟踪:")

    # 创建映射上下文
    context = MappingContext()

    # 首先映射订单
    print("  首次映射订单:")
    start_time = datetime.now()

    order_dto = OrderDTO(
        order_id="",
        order_date="",
        amount=0,
        status="",
        items=[]
    )
    context.register_mapped_object(order, order_dto)
    mappers["order_dto_mapper"].map_to_target_with_context(order, order_dto, context)

    first_mapping_time = datetime.now() - start_time
    print(f"  - 映射订单: {order_dto.order_id}")
    print(f"  - 映射耗时: {first_mapping_time.total_seconds() * 1000:.2f}ms")

    # 检查订单是否已在上下文中注册
    is_tracked = context.has_mapped_object(order)
    print(f"  - 订单是否已在上下文中跟踪: {is_tracked}")

    # 获取已映射的订单对象
    tracked_order_dto = context.get_mapped_object(order)
    print(f"  - 从上下文获取的订单DTO与直接映射的是否相同: {tracked_order_dto is order_dto}")

    # 再次映射同一个订单 - 应该返回已映射的对象
    print("\n  再次映射相同订单:")
    start_time = datetime.now()

    another_order_dto = OrderDTO(
        order_id="DIFFERENT",
        order_date="",
        amount=0,
        status="",
        items=[]
    )
    mappers["order_dto_mapper"].map_to_target_with_context(order, another_order_dto, context)

    second_mapping_time = datetime.now() - start_time
    print(f"  - 再次映射后的订单ID: {another_order_dto.order_id}")
    print(f"  - 是否与原始订单DTO相同: {another_order_dto.order_id == order_dto.order_id}")
    print(f"  - 映射耗时: {second_mapping_time.total_seconds() * 1000:.2f}ms")
    print(f"  - 性能提升: {first_mapping_time.total_seconds() / max(second_mapping_time.total_seconds(), 0.001):.2f}倍")

    # 2.2 集合对象跟踪
    print("\n2.2 集合对象跟踪:")

    # 创建新的上下文
    collection_context = MappingContext()

    # 映射订单项集合
    print("  映射订单项集合:")
    start_time = datetime.now()

    # 先映射一个订单项
    item_dto1 = OrderItemDTO(
        item_id="",
        product_id="",
        product_name="",
        quantity=0,
        price=0,
        total=0
    )
    collection_context.register_mapped_object(items[0], item_dto1)
    mappers["order_item_dto_mapper"].map_to_target_with_context(items[0], item_dto1, collection_context)
    print(f"  - 映射第一个订单项: {item_dto1.item_id}")

    # 映射所有订单项
    all_items_dtos = []
    for item in items:
        # 检查是否已映射
        if collection_context.has_mapped_object(item):
            # 重用已映射对象
            item_dto = collection_context.get_mapped_object(item)
            print(f"  - 重用已映射的订单项: {item_dto.item_id}")
        else:
            # 创建新对象并映射
            item_dto = OrderItemDTO(
                item_id="",
                product_id="",
                product_name="",
                quantity=0,
                price=0,
                total=0
            )
            collection_context.register_mapped_object(item, item_dto)
            mappers["order_item_dto_mapper"].map_to_target_with_context(item, item_dto, collection_context)
            print(f"  - 新映射订单项: {item_dto.item_id}")

        all_items_dtos.append(item_dto)

    collection_mapping_time = datetime.now() - start_time
    print(f"  - 总映射耗时: {collection_mapping_time.total_seconds() * 1000:.2f}ms")
    print(f"  - 映射的订单项数量: {len(all_items_dtos)}")
    print(f"  - 第一个订单项是否被重用: {all_items_dtos[0] is item_dto1}")

    # 2.3 对象图跟踪
    print("\n2.3 对象图跟踪:")

    # 创建新的上下文
    graph_context = MappingContext()

    # 映射完整对象图
    print("  映射完整客户-订单-订单项对象图:")
    start_time = datetime.now()

    # 辅助函数 - 映射客户及其关联对象
    def map_customer_graph(customer, context):
        """映射客户及其关联对象"""
        # 检查客户是否已映射
        if context.has_mapped_object(customer):
            return context.get_mapped_object(customer)

        # 创建客户DTO
        customer_dto = CustomerDTO(
            customer_id="",
            customer_name="",
            email="",
            orders=[]
        )
        context.register_mapped_object(customer, customer_dto)
        mappers["customer_dto_mapper"].map_to_target_with_context(customer, customer_dto, context)

        # 映射订单
        for order in customer.orders:
            order_dto = map_order_graph(order, context)
            customer_dto.orders.append(order_dto)
            order_dto.customer = customer_dto

        return customer_dto

    def map_order_graph(order, context):
        """映射订单及其关联对象"""
        # 检查订单是否已映射
        if context.has_mapped_object(order):
            return context.get_mapped_object(order)

        # 创建订单DTO
        order_dto = OrderDTO(
            order_id="",
            order_date="",
            amount=0,
            status="",
            items=[]
        )
        context.register_mapped_object(order, order_dto)
        mappers["order_dto_mapper"].map_to_target_with_context(order, order_dto, context)

        # 映射订单项
        for item in order.items:
            item_dto = map_order_item_graph(item, context)
            order_dto.items.append(item_dto)
            item_dto.order = order_dto

        return order_dto

    def map_order_item_graph(item, context):
        """映射订单项"""
        # 检查订单项是否已映射
        if context.has_mapped_object(item):
            return context.get_mapped_object(item)

        # 创建订单项DTO
        item_dto = OrderItemDTO(
            item_id="",
            product_id="",
            product_name="",
            quantity=0,
            price=0,
            total=0
        )
        context.register_mapped_object(item, item_dto)
        mappers["order_item_dto_mapper"].map_to_target_with_context(item, item_dto, context)

        return item_dto

    # 映射客户对象图
    customer_dto = map_customer_graph(customer, graph_context)

    graph_mapping_time = datetime.now() - start_time
    print(f"  - 对象图映射耗时: {graph_mapping_time.total_seconds() * 1000:.2f}ms")

    # 验证对象图
    print("  验证对象图:")
    print(f"  - 客户DTO ID: {customer_dto.customer_id}")
    print(f"  - 订单数量: {len(customer_dto.orders)}")

    if customer_dto.orders:
        order_dto = customer_dto.orders[0]
        print(f"  - 第一个订单DTO ID: {order_dto.order_id}")
        print(f"  - 订单项数量: {len(order_dto.items)}")

        # 验证循环引用
        print(f"  - 订单DTO的客户引用回客户DTO: {order_dto.customer is customer_dto}")

        if order_dto.items:
            item_dto = order_dto.items[0]
            print(f"  - 第一个订单项DTO ID: {item_dto.item_id}")
            print(f"  - 订单项DTO的订单引用回订单DTO: {item_dto.order is order_dto}")

    # 2.4 对象标识和相等性
    print("\n2.4 对象标识和相等性:")

    # 创建两个相同ID但不同实例的订单
    order1 = Order(
        id=order.id,  # 使用相同ID
        order_date=order.order_date,
        total_amount=order.total_amount,
        status=order.status
    )

    # 检查是否被识别为同一个对象
    print("  测试对象标识:")
    print(f"  - 两个订单实例是否相同: {order is order1}")
    print(f"  - 两个订单ID是否相同: {order.id == order1.id}")

    # 在上下文中查找
    has_original = graph_context.has_mapped_object(order)
    has_duplicate = graph_context.has_mapped_object(order1)

    print(f"  - 原始订单是否在上下文中: {has_original}")
    print(f"  - 相同ID的新订单是否在上下文中: {has_duplicate}")
    print("  - 注意: 默认情况下，MappingContext使用对象标识(id())而非对象相等性来跟踪对象")

    # 2.5 最佳实践
    print("\n2.5 对象跟踪最佳实践:")
    print("  1. 始终使用context.register_mapped_object()注册对象")
    print("  2. 在映射前使用context.has_mapped_object()检查对象是否已映射")
    print("  3. 使用context.get_mapped_object()获取已映射的对象")
    print("  4. 为复杂对象图创建专门的映射函数")
    print("  5. 考虑自定义对象标识策略，例如基于ID而非对象引用")
    print("  6. 在批量操作中重用上下文以提高性能")


def shared_state_example(mappers):
    """共享状态示例
    
    本示例展示了MappingContext如何通过共享状态控制映射行为:
    1. 状态传递 - 在映射过程中传递配置和上下文信息
    2. 条件映射 - 根据状态决定映射哪些属性和如何映射
    3. 安全控制 - 基于权限级别过滤敏感数据
    4. 格式化控制 - 根据区域设置调整数据格式
    5. 动态映射 - 运行时调整映射行为
    """
    print("\n=== 3. 共享状态示例 ===")

    # 获取示例数据
    customer, order, items = create_sample_data()

    # 3.1 基本状态设置和获取
    print("\n3.1 基本状态设置和获取:")

    # 创建映射上下文并设置共享状态
    context = MappingContext()
    context.set_state("include_details", True)
    context.set_state("security_level", "admin")
    context.set_state("locale", "zh_CN")

    print("  设置的共享状态:")
    print(f"  - include_details: {context.get_state('include_details')}")
    print(f"  - security_level: {context.get_state('security_level')}")
    print(f"  - locale: {context.get_state('locale')}")
    print(f"  - 不存在的状态: {context.get_state('not_exist', '默认值')}")

    # 3.2 使用共享状态控制映射行为
    print("\n3.2 使用共享状态控制映射行为:")

    # 辅助函数
    def mask_email(email):
        """脱敏邮箱地址"""
        if not email:
            return ""
        parts = email.split('@')
        if len(parts) != 2:
            return email
        username = parts[0]
        domain = parts[1]
        if len(username) <= 3:
            masked_username = username[0] + "*" * (len(username) - 1)
        else:
            masked_username = username[:3] + "*" * (len(username) - 3)
        return f"{masked_username}@{domain}"

    def format_date(date, locale):
        """根据区域设置格式化日期"""
        if not date:
            return ""
        if locale == "zh_CN":
            return date.strftime("%Y年%m月%d日")
        elif locale == "en_US":
            return date.strftime("%m/%d/%Y")
        else:
            return date.isoformat()

    # 创建一个使用共享状态的自定义映射函数
    def map_customer_with_state(customer, context):
        """根据上下文状态映射客户
        
        Args:
            customer: 客户领域对象
            context: 映射上下文
            
        Returns:
            CustomerDTO: 根据上下文状态映射的客户DTO
        """
        # 获取状态
        security_level = context.get_state("security_level", "user")
        locale = context.get_state("locale", "en_US")
        include_details = context.get_state("include_details", False)

        print(f"  映射客户，使用以下状态:")
        print(f"  - 安全级别: {security_level}")
        print(f"  - 区域设置: {locale}")
        print(f"  - 包含详情: {include_details}")

        # 根据安全级别决定映射内容
        address = {}
        if security_level == "admin":
            # 管理员可以看到完整地址
            address = customer.address
        elif security_level == "manager":
            # 经理可以看到部分地址
            address = {
                "city": customer.address.get("city", ""),
                "country": customer.address.get("country", "")
            }
        # 普通用户看不到地址

        # 根据区域设置格式化日期
        registration_date = format_date(customer.created_at, locale)

        # 创建客户DTO
        customer_dto = CustomerDTO(
            customer_id=customer.id,
            customer_name=customer.name,
            email=customer.email if security_level in ["admin", "manager"] else mask_email(customer.email),
            address=address,
            registration_date=registration_date,
            orders=[]
        )

        # 根据是否包含详情决定是否映射订单
        if include_details:
            for o in customer.orders:
                # 创建订单DTO对象
                order_dto = OrderDTO(
                    order_id=o.id,
                    order_date=format_date(o.order_date, locale),
                    amount=o.total_amount,
                    status=o.status,
                    items=[]
                )

                # 根据安全级别决定是否包含订单项
                if security_level in ["admin", "manager"]:
                    # 映射订单项
                    for item in o.items:
                        item_dto = OrderItemDTO(
                            item_id=item.id,
                            product_id=item.product_id,
                            product_name=item.product_name,
                            quantity=item.quantity,
                            price=item.unit_price,
                            total=item.quantity * item.unit_price
                        )
                        item_dto.order = order_dto
                        order_dto.items.append(item_dto)

                customer_dto.orders.append(order_dto)
                order_dto.customer = customer_dto

        return customer_dto

    # 3.3 不同安全级别的映射结果
    print("\n3.3 不同安全级别的映射结果:")

    # 管理员视图
    admin_context = MappingContext()
    admin_context.set_state("security_level", "admin")
    admin_context.set_state("locale", "zh_CN")
    admin_context.set_state("include_details", True)

    admin_dto = map_customer_with_state(customer, admin_context)

    print("\n  管理员视图:")
    print(f"  - 客户ID: {admin_dto.customer_id}")
    print(f"  - 客户名称: {admin_dto.customer_name}")
    print(f"  - 电子邮件: {admin_dto.email}")
    print(f"  - 注册日期: {admin_dto.registration_date}")
    print(f"  - 地址: {admin_dto.address}")
    print(f"  - 订单数量: {len(admin_dto.orders)}")
    if admin_dto.orders:
        print(f"  - 第一个订单项数量: {len(admin_dto.orders[0].items)}")

    # 经理视图
    manager_context = MappingContext()
    manager_context.set_state("security_level", "manager")
    manager_context.set_state("locale", "en_US")
    manager_context.set_state("include_details", True)

    manager_dto = map_customer_with_state(customer, manager_context)

    print("\n  经理视图:")
    print(f"  - 客户ID: {manager_dto.customer_id}")
    print(f"  - 客户名称: {manager_dto.customer_name}")
    print(f"  - 电子邮件: {manager_dto.email}")
    print(f"  - 注册日期: {manager_dto.registration_date}")
    print(f"  - 地址: {manager_dto.address}")
    print(f"  - 订单数量: {len(manager_dto.orders)}")
    if manager_dto.orders:
        print(f"  - 第一个订单项数量: {len(manager_dto.orders[0].items)}")

    # 普通用户视图
    user_context = MappingContext()
    user_context.set_state("security_level", "user")
    user_context.set_state("locale", "zh_CN")
    user_context.set_state("include_details", False)

    user_dto = map_customer_with_state(customer, user_context)

    print("\n  普通用户视图:")
    print(f"  - 客户ID: {user_dto.customer_id}")
    print(f"  - 客户名称: {user_dto.customer_name}")
    print(f"  - 电子邮件: {user_dto.email}")
    print(f"  - 注册日期: {user_dto.registration_date}")
    print(f"  - 地址: {user_dto.address}")
    print(f"  - 订单数量: {len(user_dto.orders)}")

    # 3.4 使用共享状态传递请求上下文
    print("\n3.4 使用共享状态传递请求上下文:")

    # 模拟API请求上下文
    class RequestContext:
        def __init__(self, user_id, roles, language):
            self.user_id = user_id
            self.roles = roles
            self.language = language
            self.timestamp = datetime.now()

    # 创建请求上下文
    request = RequestContext(
        user_id="user123",
        roles=["admin"],
        language="en_US"
    )

    # 创建映射上下文并设置请求信息
    api_context = MappingContext()
    api_context.set_state("request", request)
    api_context.set_state("include_audit", True)

    # 使用请求上下文进行映射
    def map_with_request_context(customer, context):
        """使用请求上下文映射客户"""
        # 获取请求上下文
        request = context.get_state("request")
        if not request:
            raise ValueError("缺少请求上下文")

        # 根据角色确定安全级别
        security_level = "user"
        if "admin" in request.roles:
            security_level = "admin"
        elif "manager" in request.roles:
            security_level = "manager"

        # 设置映射选项
        context.set_state("security_level", security_level)
        context.set_state("locale", request.language)
        context.set_state("include_details", True)

        # 映射客户
        customer_dto = map_customer_with_state(customer, context)

        # 添加审计信息
        if context.get_state("include_audit", False):
            audit_info = {
                "mapped_by": request.user_id,
                "mapped_at": request.timestamp.isoformat(),
                "security_level": security_level
            }
            # 在实际应用中，可能需要扩展DTO类以包含审计字段
            # 这里我们使用动态属性模拟
            setattr(customer_dto, "_audit", audit_info)

        return customer_dto

    # 使用请求上下文映射
    try:
        request_dto = map_with_request_context(customer, api_context)

        print("  使用请求上下文映射结果:")
        print(f"  - 客户ID: {request_dto.customer_id}")
        print(f"  - 客户名称: {request_dto.customer_name}")
        print(f"  - 电子邮件: {request_dto.email}")
        print(f"  - 注册日期: {request_dto.registration_date}")

        # 显示审计信息
        if hasattr(request_dto, "_audit"):
            audit = getattr(request_dto, "_audit")
            print("  - 审计信息:")
            for key, value in audit.items():
                print(f"    - {key}: {value}")
    except ValueError as e:
        print(f"  错误: {str(e)}")

    # 3.5 最佳实践
    print("\n3.5 共享状态最佳实践:")
    print("  1. 使用明确的状态键名，避免冲突")
    print("  2. 为可选状态提供默认值")
    print("  3. 在映射函数开始时获取所有需要的状态")
    print("  4. 使用状态控制映射行为，而不是硬编码")
    print("  5. 考虑将复杂对象作为状态值，例如请求上下文")
    print("  6. 使用状态传递审计和安全信息")


def ddd_application_example(mappers):
    """DDD应用场景示例
    
    本示例展示了MappingContext在领域驱动设计(DDD)应用中的实际应用场景:
    1. 聚合根与实体的映射 - 处理复杂对象图
    2. 持久化映射 - 从领域模型到持久化对象的转换
    3. 错误处理 - 处理映射过程中的异常情况
    4. 性能优化 - 使用对象跟踪减少重复映射
    """
    print("\n=== 4. DDD应用场景示例 ===")

    # 获取示例数据
    customer, order, items = create_sample_data()

    # 模拟应用服务
    class OrderApplicationService:
        def __init__(self, mappers):
            self.mappers = mappers
            # 模拟缓存
            self._order_cache = {}

        def get_order_with_details(self, order, include_customer_details=False, security_level="user"):
            """获取订单详情
            
            Args:
                order: 订单领域对象
                include_customer_details: 是否包含客户详情
                security_level: 安全级别，决定返回的数据敏感度
                
            Returns:
                OrderDTO: 订单数据传输对象
                
            Raises:
                ValueError: 当订单对象为None时抛出
            """
            # 参数验证
            if order is None:
                raise ValueError("订单对象不能为空")

            # 检查缓存
            cache_key = f"{order.id}_{include_customer_details}_{security_level}"
            if cache_key in self._order_cache:
                print(f"从缓存获取订单DTO: {order.id}")
                return self._order_cache[cache_key]

            # 创建映射上下文
            context = MappingContext()

            # 设置映射选项
            context.set_state("include_customer_details", include_customer_details)
            context.set_state("security_level", security_level)
            context.set_state("timestamp", datetime.now().isoformat())

            try:
                # 创建订单DTO
                order_dto = OrderDTO(
                    order_id=order.id,
                    order_date=order.order_date.isoformat() if order.order_date else "",
                    amount=order.total_amount,
                    status=order.status,
                    items=[]
                )

                # 注册到上下文以启用对象跟踪
                context.register_mapped_object(order, order_dto)

                # 如果需要包含客户详情
                if include_customer_details and order.customer:
                    customer_dto = CustomerDTO(
                        customer_id=order.customer.id,
                        customer_name=order.customer.name,
                        email="",
                        orders=[]
                    )

                    # 注册到上下文以启用对象跟踪
                    context.register_mapped_object(order.customer, customer_dto)

                    # 根据安全级别决定映射内容
                    if security_level == "admin":
                        # 管理员可以看到所有信息
                        customer_dto.email = order.customer.email
                        customer_dto.address = order.customer.address.copy() if order.customer.address else {}
                    else:
                        # 普通用户只能看到基本信息，不包含地址和邮箱
                        customer_dto.customer_id = order.customer.id
                        customer_dto.customer_name = order.customer.name
                        # 邮箱脱敏
                        if order.customer.email:
                            parts = order.customer.email.split('@')
                            if len(parts) == 2:
                                customer_dto.email = f"{parts[0][:3]}***@{parts[1]}"

                    order_dto.customer = customer_dto

                # 映射订单项
                for item in order.items:
                    item_dto = OrderItemDTO(
                        item_id=item.id,
                        product_id=item.product_id,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        price=item.unit_price,
                        total=item.quantity * item.unit_price
                    )

                    # 注册到上下文以启用对象跟踪
                    context.register_mapped_object(item, item_dto)

                    item_dto.order = order_dto
                    order_dto.items.append(item_dto)

                # 添加到缓存
                self._order_cache[cache_key] = order_dto

                return order_dto

            except Exception as e:
                print(f"映射订单时发生错误: {str(e)}")
                # 在实际应用中，这里应该记录日志
                raise

        def save_order(self, order):
            """保存订单
            
            Args:
                order: 订单领域对象
                
            Returns:
                tuple: (order_po, item_pos) 订单和订单项的持久化对象
                
            Raises:
                ValueError: 当订单对象为None或无效时抛出
            """
            # 参数验证
            if order is None:
                raise ValueError("订单对象不能为空")

            if not order.id:
                raise ValueError("订单ID不能为空")

            if not order.items:
                raise ValueError("订单必须包含至少一个订单项")

            # 创建映射上下文
            context = MappingContext()

            # 设置审计信息
            context.set_state("operation", "save")
            context.set_state("timestamp", datetime.now().isoformat())
            context.set_state("user_id", "system")  # 在实际应用中，这应该是当前用户的ID

            try:
                # 映射订单到PO
                order_po = OrderPO(
                    id="",
                    customer_id="",
                    order_date="",
                    total_amount=0,
                    status=""
                )
                self.mappers["order_po_mapper"].map_to_target_with_context(order, order_po, context)

                # 映射订单项到PO
                item_pos = []
                for item in order.items:
                    item_po = OrderItemPO(
                        id="",
                        order_id="",
                        product_id="",
                        product_name="",
                        quantity=0,
                        unit_price=0
                    )
                    self.mappers["order_item_po_mapper"].map_to_target_with_context(item, item_po, context)
                    item_pos.append(item_po)

                # 模拟保存到数据库
                print(f"保存订单PO: {order_po.id}")
                for item_po in item_pos:
                    print(f"  - 保存订单项PO: {item_po.id}, 产品: {item_po.product_name}")

                # 清除缓存
                self._order_cache = {k: v for k, v in self._order_cache.items() if not k.startswith(order.id)}
                print(f"已清除订单 {order.id} 的缓存")

                return order_po, item_pos

            except Exception as e:
                print(f"保存订单时发生错误: {str(e)}")
                # 在实际应用中，这里应该记录日志
                raise

        def update_order_status(self, order, new_status):
            """更新订单状态
            
            展示如何使用MappingContext处理部分更新场景
            
            Args:
                order: 订单领域对象
                new_status: 新的订单状态
                
            Returns:
                OrderDTO: 更新后的订单DTO
            """
            # 参数验证
            if order is None:
                raise ValueError("订单对象不能为空")

            if not new_status:
                raise ValueError("新状态不能为空")

            # 更新领域对象
            old_status = order.status
            order.status = new_status

            # 创建映射上下文
            context = MappingContext()
            context.set_state("partial_update", True)
            context.set_state("updated_fields", ["status"])

            # 创建DTO并映射
            order_dto = OrderDTO(
                order_id="",
                order_date="",
                amount=0,
                status="",
                items=[]
            )
            self.mappers["order_dto_mapper"].map_to_target_with_context(order, order_dto, context)

            print(f"订单状态已更新: {old_status} -> {new_status}")

            # 清除缓存
            self._order_cache = {k: v for k, v in self._order_cache.items() if not k.startswith(order.id)}

            return order_dto

    # 创建应用服务
    order_service = OrderApplicationService(mappers)

    # 1. 获取订单详情 - 普通用户视图
    print("\n1. 获取订单详情 (普通用户视图):")
    try:
        order_dto = order_service.get_order_with_details(
            order,
            include_customer_details=True,
            security_level="user"
        )

        print(f"订单DTO: {order_dto.order_id}")
        print(f"订单日期: {order_dto.order_date}")
        print(f"订单金额: {order_dto.amount}")
        print(f"订单状态: {order_dto.status}")
        print(f"订单项数量: {len(order_dto.items)}")

        if order_dto.customer:
            print(f"客户信息: {order_dto.customer.customer_name} ({order_dto.customer.customer_id})")
            print(f"客户邮箱: {order_dto.customer.email} (脱敏)")
    except ValueError as e:
        print(f"参数错误: {str(e)}")

    # 2. 获取订单详情 - 管理员视图
    print("\n2. 获取订单详情 (管理员视图):")
    try:
        order_dto = order_service.get_order_with_details(
            order,
            include_customer_details=True,
            security_level="admin"
        )

        print(f"订单DTO: {order_dto.order_id}")
        print(f"订单金额: {order_dto.amount}")

        if order_dto.customer:
            print(f"客户信息: {order_dto.customer.customer_name} ({order_dto.customer.customer_id})")
            print(f"客户邮箱: {order_dto.customer.email} (完整)")
            print(f"客户地址: {order_dto.customer.address}")
    except ValueError as e:
        print(f"参数错误: {str(e)}")

    # 3. 测试缓存功能
    print("\n3. 测试缓存功能:")
    start_time = datetime.now()
    order_dto1 = order_service.get_order_with_details(order, include_customer_details=True)
    first_call_time = datetime.now() - start_time

    start_time = datetime.now()
    order_dto2 = order_service.get_order_with_details(order, include_customer_details=True)
    second_call_time = datetime.now() - start_time

    print(f"首次调用耗时: {first_call_time.total_seconds() * 1000:.2f}ms")
    print(f"二次调用耗时: {second_call_time.total_seconds() * 1000:.2f}ms")
    print(f"两次返回的是同一对象: {order_dto1 is order_dto2}")

    # 4. 保存订单
    print("\n4. 保存订单:")
    try:
        order_po, item_pos = order_service.save_order(order)

        print(f"保存的订单PO ID: {order_po.id}")
        print(f"关联的客户ID: {order_po.customer_id}")
        print(f"订单日期: {order_po.order_date}")
        print(f"订单金额: {order_po.total_amount}")
        print(f"订单状态: {order_po.status}")
        print(f"保存的订单项数量: {len(item_pos)}")
    except ValueError as e:
        print(f"参数错误: {str(e)}")

    # 5. 更新订单状态
    print("\n5. 更新订单状态:")
    try:
        updated_order_dto = order_service.update_order_status(order, "SHIPPED")
        print(f"更新后的订单状态: {updated_order_dto.status}")

        # 验证缓存已清除
        start_time = datetime.now()
        # 这里需要确保使用相同的参数，以便正确比较状态
        new_order_dto = order_service.get_order_with_details(
            order,
            include_customer_details=True,
            security_level="user"
        )
        reload_time = datetime.now() - start_time

        print(f"重新加载耗时: {reload_time.total_seconds() * 1000:.2f}ms")
        print(f"状态是否一致: {new_order_dto.status == 'SHIPPED'}")
        print(f"新状态: {new_order_dto.status}, 期望状态: SHIPPED")
    except ValueError as e:
        print(f"参数错误: {str(e)}")

    # 6. 错误处理示例
    print("\n6. 错误处理示例:")
    try:
        # 尝试保存没有订单项的订单
        empty_order = Order(
            id="ORD-" + str(uuid.uuid4())[:8],
            order_date=datetime.now(),
            total_amount=0,
            status="NEW"
        )
        order_service.save_order(empty_order)
    except ValueError as e:
        print(f"预期的错误: {str(e)}")


def run_examples():
    """运行所有示例"""
    try:
        # 创建映射器
        mappers = create_mappers()

        # 运行示例
        circular_reference_example(mappers)
        object_tracking_example(mappers)
        shared_state_example(mappers)
        ddd_application_example(mappers)

        print("\n所有示例运行完成!")
    except Exception as e:
        print(f"示例运行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_examples()
