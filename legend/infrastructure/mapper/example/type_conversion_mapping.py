"""类型转换映射示例

本示例演示如何使用映射器进行类型转换，包括基本类型转换和自定义类型转换。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union

from idp.framework.infrastructure.mapper.core.converter import type_converter_registry
from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


# 枚举类型
class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# 自定义类型
class Money:
    """金额类型"""

    def __init__(self, amount: float, currency: str = "CNY"):
        self.amount = amount
        self.currency = currency

    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"


# 源对象类
@dataclass
class OrderEntity:
    """订单实体"""
    id: int
    customer_id: int
    status: OrderStatus
    amount: Money
    quantity: int
    created_at: datetime
    updated_at: datetime
    notes: str
    tags: List[str]


# 目标对象类
@dataclass
class OrderDTO:
    """订单DTO"""

    def __init__(
        self,
        order_id: int = None,
        customer_id: int = None,
        status: str = None,
        amount: str = None,
        quantity: int = None,
        created_at: str = None,
        updated_at_str: str = None,
        notes: str = None,
        tags_string: str = None
    ):
        self.order_id = order_id
        self.customer_id = customer_id
        self.status = status
        self.amount = amount
        self.quantity = quantity
        self.created_at = created_at
        self.updated_at_str = updated_at_str
        self.notes = notes
        self.tags_string = tags_string


def register_custom_converters():
    """注册自定义类型转换器"""
    # 获取全局类型转换器注册表实例
    converter_registry = type_converter_registry

    # 注册枚举到字符串的转换器
    converter_registry.register_converter(
        OrderStatus, str, lambda status: status.value)

    # 注册Money到字符串的转换器
    converter_registry.register_converter(
        Money, str, lambda money: f"{money.amount} {money.currency}")

    # 注册datetime到字符串的转换器 (ISO格式)
    converter_registry.register_converter(
        datetime, str, lambda dt: dt.isoformat())

    # 注册字符串到datetime的转换器
    converter_registry.register_converter(
        str, datetime, lambda s: datetime.fromisoformat(s))

    # 注册列表到字符串的转换器
    converter_registry.register_converter(
        list, str, lambda lst: ', '.join(lst))

    # 注册字符串到列表的转换器
    converter_registry.register_converter(
        str, list, lambda s: [item.strip() for item in s.split(',')])


def type_conversion_mapping_example():
    """类型转换映射示例"""
    print("\n===== 类型转换映射示例 =====")

    # 创建源对象
    order = OrderEntity(
        id=12345,
        customer_id=9876,
        status=OrderStatus.PROCESSING,
        amount=Money(1299.99, "CNY"),
        quantity=5,
        created_at=datetime(2023, 6, 15, 10, 30),
        updated_at=datetime(2023, 6, 15, 14, 45),
        notes="Express delivery requested",
        tags=["urgent", "gift", "international"]
    )

    # 打印源对象信息
    print("源对象:")
    print(f"ID: {order.id} (类型: {type(order.id).__name__})")
    print(f"客户ID: {order.customer_id} (类型: {type(order.customer_id).__name__})")
    print(f"状态: {order.status} (类型: {type(order.status).__name__})")
    print(
        f"金额: {order.amount.amount} {order.amount.currency} (类型: {type(order.amount).__name__})")
    print(f"商品数量: {order.quantity} (类型: {type(order.quantity).__name__})")
    print(f"创建时间: {order.created_at} (类型: {type(order.created_at).__name__})")
    print(f"更新时间: {order.updated_at} (类型: {type(order.updated_at).__name__})")
    print(f"备注: {order.notes} (类型: {type(order.notes).__name__})")
    print(f"标签: {order.tags} (类型: {type(order.tags).__name__})")

    # 注册自定义类型转换器
    register_custom_converters()

    # 手动执行映射
    order_dto = OrderDTO()
    order_dto.order_id = order.id
    order_dto.customer_id = order.customer_id
    order_dto.status = order.status.value  # 枚举到字符串
    # Money到字符串
    order_dto.amount = f"{order.amount.amount} {order.amount.currency}"
    order_dto.quantity = order.quantity
    order_dto.created_at = order.created_at.isoformat()  # datetime到字符串
    order_dto.updated_at_str = order.updated_at.isoformat()  # datetime到字符串
    order_dto.notes = order.notes
    order_dto.tags_string = ", ".join(order.tags)  # 列表到字符串

    # 打印目标对象信息
    print("\n目标对象:")
    print(
        f"订单ID: {order_dto.order_id} (类型: {type(order_dto.order_id).__name__})")
    print(
        f"客户ID: {order_dto.customer_id} (类型: {type(order_dto.customer_id).__name__})")
    print(f"状态: {order_dto.status} (类型: {type(order_dto.status).__name__})")
    print(f"金额: {order_dto.amount} (类型: {type(order_dto.amount).__name__})")
    print(
        f"商品数量: {order_dto.quantity} (类型: {type(order_dto.quantity).__name__})")
    print(
        f"创建时间: {order_dto.created_at} (类型: {type(order_dto.created_at).__name__})")
    print(
        f"更新时间: {order_dto.updated_at_str} (类型: {type(order_dto.updated_at_str).__name__})")
    print(f"备注: {order_dto.notes} (类型: {type(order_dto.notes).__name__})")
    print(
        f"标签: {order_dto.tags_string} (类型: {type(order_dto.tags_string).__name__})")

    # 创建源对象
    new_order_dto = OrderDTO(
        order_id=54321,
        customer_id=6789,
        status="SHIPPED",
        amount="899.99 USD",
        quantity=3,
        created_at="2023-07-20T09:15:00",
        updated_at_str="2023-07-20T10:30:00",
        notes="Handle with care",
        tags_string="fragile, electronics, gift"
    )

    # 手动执行反向映射
    mapped_back_order = OrderEntity(
        id=new_order_dto.order_id,
        customer_id=new_order_dto.customer_id,
        status=OrderStatus.SHIPPED,  # 字符串到枚举
        amount=Money(899.99, "USD"),  # 字符串到Money
        quantity=new_order_dto.quantity,
        created_at=datetime.fromisoformat(
            new_order_dto.created_at),  # 字符串到datetime
        updated_at=datetime.fromisoformat(
            new_order_dto.updated_at_str),  # 字符串到datetime
        notes=new_order_dto.notes,
        tags=[item.strip()
              for item in new_order_dto.tags_string.split(",")]  # 字符串到列表
    )

    # 打印反向映射结果
    print("\n反向映射结果:")
    print(f"ID: {mapped_back_order.id} (类型: {type(mapped_back_order.id).__name__})")
    print(
        f"客户ID: {mapped_back_order.customer_id} (类型: {type(mapped_back_order.customer_id).__name__})")
    print(
        f"状态: {mapped_back_order.status} (类型: {type(mapped_back_order.status).__name__})")
    if hasattr(mapped_back_order.amount, 'amount') and hasattr(mapped_back_order.amount, 'currency'):
        print(f"金额: {mapped_back_order.amount.amount} {mapped_back_order.amount.currency} (类型: {type(mapped_back_order.amount).__name__})")
    else:
        print(
            f"金额: {mapped_back_order.amount} (类型: {type(mapped_back_order.amount).__name__})")
    print(
        f"商品数量: {mapped_back_order.quantity} (类型: {type(mapped_back_order.quantity).__name__})")
    print(
        f"创建时间: {mapped_back_order.created_at} (类型: {type(mapped_back_order.created_at).__name__})")
    print(
        f"更新时间: {mapped_back_order.updated_at} (类型: {type(mapped_back_order.updated_at).__name__})")
    print(
        f"备注: {mapped_back_order.notes} (类型: {type(mapped_back_order.notes).__name__})")
    print(
        f"标签: {mapped_back_order.tags} (类型: {type(mapped_back_order.tags).__name__})")

    print("\n===== 类型转换映射示例结束 =====")


if __name__ == "__main__":
    type_conversion_mapping_example()
