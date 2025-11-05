# idp/core/domain/specification.py
# from abc import ABC, abstractmethod
# from typing import TypeVar, Generic

# T = TypeVar('T')

# class Specification(Generic[T], ABC):
#     """
#     规格模式接口
    
#     用于封装业务规则和条件判断
#     """
    
#     @abstractmethod
#     def is_satisfied_by(self, candidate: T) -> bool:
#         """
#         判断候选对象是否满足规格
        
#         Args:
#             candidate: 候选对象
            
#         Returns:
#             是否满足规格
#         """
#         pass
    
#     def and_(self, other: 'Specification[T]') -> 'AndSpecification[T]':
#         """与操作"""
#         return AndSpecification(self, other)
    
#     def or_(self, other: 'Specification[T]') -> 'OrSpecification[T]':
#         """或操作"""
#         return OrSpecification(self, other)
    
#     def not_(self) -> 'NotSpecification[T]':
#         """非操作"""
#         return NotSpecification(self)


# class AndSpecification(Specification[T]):
#     """与规格"""
    
#     def __init__(self, left: Specification[T], right: Specification[T]):
#         self.left = left
#         self.right = right
    
#     def is_satisfied_by(self, candidate: T) -> bool:
#         return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)


# class OrSpecification(Specification[T]):
#     """或规格"""
    
#     def __init__(self, left: Specification[T], right: Specification[T]):
#         self.left = left
#         self.right = right
    
#     def is_satisfied_by(self, candidate: T) -> bool:
#         return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)


'''
    规格模式示例

    规格模式是一种设计模式，用于封装业务规则和条件判断。
    它允许开发者定义复杂的业务规则，并通过组合这些规则来构建更复杂的业务逻辑。
    规格模式通常用于以下场景：
    1. 验证输入数据
    2. 过滤数据
    3. 条件查询
    4. 业务规则表达
    5. 权限控制
    6. 状态机
    7. 事件处理
    8. 领域规则
    9. 业务逻辑
    10. 业务规则

    class NotSpecification(Specification[T]):
    """非规格"""
    
    def __init__(self, spec: Specification[T]):
        self.spec = spec
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.spec.is_satisfied_by(candidate)
    


# 示例：订单有效性规格
class OrderValidSpecification(Specification[Order]):
    def is_satisfied_by(self, order: Order) -> bool:
        return (order.items is not None and
                len(order.items) > 0 and
                order.customer_id is not None)

# 示例：订单金额规格
class OrderAmountSpecification(Specification[Order]):
    def __init__(self, min_amount: float):
        self.min_amount = min_amount

    def is_satisfied_by(self, order: Order) -> bool:
        return order.calculate_total_amount() >= self.min_amount

# 组合使用
valid_order_spec = OrderValidSpecification().and_(OrderAmountSpecification(100.0))
if valid_order_spec.is_satisfied_by(order):
    # 处理有效订单
    pass
'''


