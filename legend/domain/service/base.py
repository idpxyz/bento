# 领域服务
from abc import ABC
from typing import TypeVar, Generic

T = TypeVar('T')

class DomainService(ABC):
    """
    领域服务基类
    
    用于封装跨聚合根的业务逻辑
    """
    pass

# 示例领域服务
# idp/domain/services/order_pricing_service.py
# from idp.domain.service.domain_service import DomainService
# from idp.domain.model.order.order import Order
# from idp.domain.model.product.product import Product
# from idp.domain.model.customer.customer import Customer

# class OrderPricingService(DomainService):
#     """订单定价服务"""
    
#     def calculate_order_price(self, order: Order, customer: Customer, products: dict[str, Product]) -> float:
#         """
#         计算订单价格
        
#         Args:
#             order: 订单
#             customer: 客户
#             products: 产品字典（产品ID -> 产品）
            
#         Returns:
#             计算后的订单价格
#         """
#         base_price = sum(item.get("price", 0) * item.get("quantity", 0) for item in order.items)
        
#         # 应用客户折扣
#         if customer.discount_rate > 0:
#             base_price = base_price * (1 - customer.discount_rate)
        
#         # 应用产品特殊定价
#         for item in order.items:
#             product_id = item.get("product_id")
#             if product_id in products and products[product_id].has_special_pricing:
#                 # 应用特殊定价逻辑
#                 pass
        
#         return base_price