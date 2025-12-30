"""Product DTO Mapper - Using Bento AutoMapper! 🎉"""

from bento.application.dto.auto_mapper import AutoMapper

from contexts.catalog.application.dto import ProductDTO
from contexts.catalog.domain.models.product import Product


class ProductDTOMapper(AutoMapper[Product, ProductDTO]):
    """Product DTO Mapper - 90% Zero Configuration! 🤖

    Uses Bento's AutoMapper (same as Domain↔PO mapping):
    - ✅ Automatic field mapping by name
    - ✅ Smart ID conversion (ID → str)
    - ✅ Smart Enum conversion (Enum → value)
    - ✅ Optional field handling
    - ✅ Only configure exceptions!

    Compare:
    Before: 20+ lines of manual field mapping
    After:  4 lines total! 🎊
    """

    def __init__(self):
        super().__init__(Product, ProductDTO)
        # All fields auto-mapped!
        # category_id: ID → str ✅ (automatic)
        # id: ID → str ✅ (automatic)
        # name, price, stock, etc. ✅ (automatic)

        # ✅ 增强计算字段 - 提供更丰富的业务信息
        self.field_mappings = {
            "is_categorized": lambda product: product.is_categorized(),  # 方法 → 属性
            "price_tier": lambda product: "expensive" if product.price > 1000 else "affordable",
            "stock_status": lambda product: "in_stock" if product.stock > 0 else "out_of_stock",
            "formatted_price": lambda product: f"${product.price:.2f}",
            "availability": lambda product: "available"
            if product.is_active and product.stock > 0
            else "unavailable",
        }
