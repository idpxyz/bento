"""Order Specification - 订单查询规格

提供流式 API 构建复杂的订单查询条件
"""

from datetime import datetime

from bento.persistence.specification.builder import SpecificationBuilder
from bento.persistence.specification.criteria.comparison import (
    EqualsCriterion,
    GreaterThanCriterion,
    LessThanCriterion,
)


class OrderQuerySpec(SpecificationBuilder):
    """订单查询规格（基础设施层）

    使用示例:
        ```python
        # 查找特定客户的高价值订单
        spec = OrderSpec() \\
            .customer_id_equals(customer_id) \\
            .amount_greater_than(1000.0)

        orders = await order_repo.find(spec)
        ```
    """

    def customer_id_equals(self, customer_id: str) -> "OrderQuerySpec":
        """筛选特定客户的订单"""
        self.add_criterion(EqualsCriterion("customer_id", customer_id))
        return self

    def amount_greater_than(self, amount: float) -> "OrderQuerySpec":
        """筛选金额大于指定值的订单"""
        self.add_criterion(GreaterThanCriterion("total", amount))
        return self

    def amount_less_than(self, amount: float) -> "OrderQuerySpec":
        """筛选金额小于指定值的订单"""
        self.add_criterion(LessThanCriterion("total", amount))
        return self

    def amount_between(self, min_amount: float, max_amount: float) -> "OrderQuerySpec":
        """筛选金额在指定范围内的订单"""
        self.add_criterion(GreaterThanCriterion("total", min_amount))
        self.add_criterion(LessThanCriterion("total", max_amount))
        return self

    def status_equals(self, status: str) -> "OrderQuerySpec":
        """筛选特定状态的订单"""
        self.add_criterion(EqualsCriterion("status", status))
        return self

    def created_after(self, date: datetime) -> "OrderQuerySpec":
        """筛选指定日期之后创建的订单"""
        self.add_criterion(GreaterThanCriterion("created_at", date))
        return self

    def created_before(self, date: datetime) -> "OrderQuerySpec":
        """筛选指定日期之前创建的订单"""
        self.add_criterion(LessThanCriterion("created_at", date))
        return self

    def created_between(self, start_date: datetime, end_date: datetime) -> "OrderQuerySpec":
        """筛选在指定日期范围内创建的订单"""
        self.add_criterion(GreaterThanCriterion("created_at", start_date))
        self.add_criterion(LessThanCriterion("created_at", end_date))
        return self

    def is_paid(self) -> "OrderQuerySpec":
        """筛选已支付的订单"""
        return self.status_equals("paid")

    def is_pending(self) -> "OrderQuerySpec":
        """筛选待支付的订单"""
        return self.status_equals("pending")

    def is_shipped(self) -> "OrderQuerySpec":
        """筛选已发货的订单"""
        return self.status_equals("shipped")

    def is_delivered(self) -> "OrderQuerySpec":
        """筛选已送达的订单"""
        return self.status_equals("delivered")

    def is_cancelled(self) -> "OrderQuerySpec":
        """筛选已取消的订单"""
        return self.status_equals("cancelled")
