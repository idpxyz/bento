"""自定义映射示例。

本示例展示了如何使用映射器系统的自定义映射功能处理复杂的映射逻辑，包括：
1. 使用自定义函数进行值转换
2. 处理多字段合并映射
3. 实现条件映射逻辑
4. 处理格式转换和数据清洗
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


# 枚举类型定义
class PaymentStatus(Enum):
    """支付状态枚举"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(Enum):
    """支付方式枚举"""
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    DIGITAL_WALLET = "DIGITAL_WALLET"
    CASH = "CASH"


# 源对象类
@dataclass
class PaymentEntity:
    """支付实体类（源对象）"""
    id: str = ""
    amount: float = 0.0
    currency: str = ""
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: PaymentMethod = PaymentMethod.CASH
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    card_details: Optional[Dict[str, str]] = None


# 目标对象类
@dataclass
class PaymentDTO:
    """支付DTO类（目标对象）"""
    payment_id: str = ""
    amount_formatted: str = ""  # 格式化的金额，如 "$100.00 USD"
    status_code: int = 0  # 数值状态码
    status_description: str = ""  # 状态描述
    payment_method_name: str = ""  # 支付方式名称
    created_date: str = ""  # ISO格式的日期字符串
    last_updated: str = ""  # 相对时间描述，如 "2 hours ago"
    is_completed: bool = False  # 是否已完成
    masked_card_number: Optional[str] = None  # 掩码处理的卡号
    additional_info: Dict[str, str] = field(default_factory=dict)  # 附加信息


def custom_mapping_example():
    """自定义映射示例"""
    print("\n=== 自定义映射示例 ===")
    
    try:
        # 创建源对象
        payment_entity = PaymentEntity(
            id="pmt_12345",
            amount=199.99,
            currency="USD",
            status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CREDIT_CARD,
            created_at=datetime(2023, 5, 15, 14, 30, 0),
            updated_at=datetime(2023, 5, 15, 15, 45, 0),
            metadata={
                "customer_id": "cust_789",
                "order_id": "ord_456",
                "promotion_code": "SUMMER2023"
            },
            card_details={
                "card_number": "4111111111111111",
                "expiry_date": "12/25",
                "card_holder": "John Doe",
                "card_type": "Visa"
            }
        )
        
        print(f"源对象: {payment_entity}")
        
        # 自定义映射函数
        
        # 1. 格式化金额
        def format_amount(payment: PaymentEntity) -> str:
            return f"${payment.amount:.2f} {payment.currency}"
        
        # 2. 状态码映射
        def map_status_code(payment: PaymentEntity) -> int:
            status_codes = {
                PaymentStatus.PENDING: 100,
                PaymentStatus.PROCESSING: 200,
                PaymentStatus.COMPLETED: 300,
                PaymentStatus.FAILED: 400,
                PaymentStatus.REFUNDED: 500
            }
            return status_codes.get(payment.status, 0)
        
        # 3. 状态描述映射
        def map_status_description(payment: PaymentEntity) -> str:
            descriptions = {
                PaymentStatus.PENDING: "Payment is pending processing",
                PaymentStatus.PROCESSING: "Payment is being processed",
                PaymentStatus.COMPLETED: "Payment has been completed successfully",
                PaymentStatus.FAILED: "Payment processing failed",
                PaymentStatus.REFUNDED: "Payment has been refunded"
            }
            return descriptions.get(payment.status, "Unknown status")
        
        # 4. 支付方式名称映射
        def map_payment_method_name(payment: PaymentEntity) -> str:
            method_names = {
                PaymentMethod.CREDIT_CARD: "Credit Card",
                PaymentMethod.DEBIT_CARD: "Debit Card",
                PaymentMethod.BANK_TRANSFER: "Bank Transfer",
                PaymentMethod.DIGITAL_WALLET: "Digital Wallet",
                PaymentMethod.CASH: "Cash"
            }
            return method_names.get(payment.payment_method, "Unknown method")
        
        # 5. 日期格式化
        def format_date(dt: datetime) -> str:
            return dt.isoformat() if dt else ""
        
        # 6. 相对时间描述
        def get_relative_time(payment: PaymentEntity) -> str:
            if not payment.updated_at:
                return "Never updated"
            
            now = datetime.now()
            delta = now - payment.updated_at
            
            if delta.days > 0:
                return f"{delta.days} days ago"
            elif delta.seconds >= 3600:
                hours = delta.seconds // 3600
                return f"{hours} hours ago"
            elif delta.seconds >= 60:
                minutes = delta.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return f"{delta.seconds} seconds ago"
        
        # 7. 完成状态检查
        def is_payment_completed(payment: PaymentEntity) -> bool:
            return payment.status == PaymentStatus.COMPLETED
        
        # 8. 卡号掩码处理
        def mask_card_number(payment: PaymentEntity) -> Optional[str]:
            if not payment.card_details or "card_number" not in payment.card_details:
                return None
            
            card_number = payment.card_details["card_number"]
            if len(card_number) < 4:
                return card_number
            
            return "X" * (len(card_number) - 4) + card_number[-4:]
        
        # 9. 附加信息处理
        def process_additional_info(payment: PaymentEntity) -> Dict[str, str]:
            result = {}
            
            # 添加元数据信息
            for key, value in payment.metadata.items():
                result[f"meta_{key}"] = str(value)
            
            # 添加卡片信息（除了卡号）
            if payment.card_details:
                for key, value in payment.card_details.items():
                    if key != "card_number":  # 排除卡号
                        result[f"card_{key}"] = str(value)
            
            return result
        
        # 手动执行映射
        try:
            # 创建目标对象
            payment_dto = PaymentDTO()
            
            # 手动应用映射函数
            payment_dto.payment_id = payment_entity.id
            payment_dto.amount_formatted = format_amount(payment_entity)
            payment_dto.status_code = map_status_code(payment_entity)
            payment_dto.status_description = map_status_description(payment_entity)
            payment_dto.payment_method_name = map_payment_method_name(payment_entity)
            payment_dto.created_date = format_date(payment_entity.created_at)
            payment_dto.last_updated = get_relative_time(payment_entity)
            payment_dto.is_completed = is_payment_completed(payment_entity)
            payment_dto.masked_card_number = mask_card_number(payment_entity)
            payment_dto.additional_info = process_additional_info(payment_entity)
            
            # 打印结果
            print("\n手动映射结果:")
            print(f"支付ID: {payment_dto.payment_id}")
            print(f"格式化金额: {payment_dto.amount_formatted}")
            print(f"状态码: {payment_dto.status_code}")
            print(f"状态描述: {payment_dto.status_description}")
            print(f"支付方式: {payment_dto.payment_method_name}")
            print(f"创建日期: {payment_dto.created_date}")
            print(f"最后更新: {payment_dto.last_updated}")
            print(f"是否已完成: {payment_dto.is_completed}")
            print(f"掩码卡号: {payment_dto.masked_card_number}")
            
            print("\n附加信息:")
            for key, value in payment_dto.additional_info.items():
                print(f"  {key}: {value}")
                
            # 显示MapperBuilder配置示例（不执行）
            print("\nMapperBuilder的配置示例（不执行）:")
            print("""
        payment_mapper = MapperBuilder.for_types(PaymentEntity, PaymentDTO) \\
            .map("id", "payment_id") \\
            .map_custom("amount_formatted", format_amount) \\
            .map_custom("status_code", map_status_code) \\
            .map_custom("status_description", map_status_description) \\
            .map_custom("payment_method_name", map_payment_method_name) \\
            .map_custom("created_date", lambda p: format_date(p.created_at)) \\
            .map_custom("last_updated", get_relative_time) \\
            .map_custom("is_completed", is_payment_completed) \\
            .map_custom("masked_card_number", mask_card_number) \\
            .map_custom("additional_info", process_additional_info) \\
            .build()
            """)
            
        except Exception as e:
            print(f"手动映射过程中发生错误: {str(e)}")
        
        # 演示自定义映射中的异常处理
        print("\n演示自定义映射中的异常处理:")
        print("如果尝试访问不存在的属性，将导致异常:")
        print("""
        def invalid_mapping_function(payment):
            # 故意访问不存在的属性
            return payment.non_existent_attribute
            
        invalid_mapper = (MapperBuilder()
            .for_types(PaymentEntity, PaymentDTO)
            .map("id", "payment_id")
            .map_custom("amount_formatted", invalid_mapping_function)  # 使用会导致错误的函数
            .build()
        )
        """)
            
    except Exception as e:
        print(f"映射过程中发生错误: {str(e)}")


if __name__ == "__main__":
    custom_mapping_example() 