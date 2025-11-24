"""Order query specifications - Infrastructure layer"""

from .order_query_spec import OrderQuerySpec

# 为了向后兼容，也导出 OrderSpec 别名
OrderSpec = OrderQuerySpec

__all__ = ["OrderQuerySpec", "OrderSpec"]
