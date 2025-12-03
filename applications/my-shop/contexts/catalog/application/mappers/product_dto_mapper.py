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

        # Custom mapping for computed fields
        self.field_mappings = {
            "is_categorized": lambda product: product.is_categorized()  # 方法 → 属性
        }
