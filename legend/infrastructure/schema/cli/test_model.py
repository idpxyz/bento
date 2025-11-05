"""
测试模型导入和使用
"""

import os
import sys

# 添加项目路径
sys.path.append('/workspace')

# 直接导入模型（不通过 __init__.py）
from idp.framework.infrastructure.schema.generated.models.productadded import (
    ProductAdded,
    ProductImage,
)


def test_product_added():
    """测试 ProductAdded 模型及嵌套的 ProductImage 模型"""
    try:
        # 创建一个 ProductImage 实例
        image = ProductImage(
            url="https://example.com/img.jpg",
            alt="测试图片",
            is_primary=True
        )
        
        # 创建一个 ProductAdded 实例，包含嵌套的 ProductImage
        product = ProductAdded(
            product_id="test123",
            name="测试产品",
            description="这是一个测试产品",
            price=99.99,
            categories=["测试", "示例"],
            images=[image],
            status="active",
            created_by="user123"
        )
        
        # 输出 JSON
        print("模型验证成功！JSON 输出:")
        print(product.model_dump_json(indent=2))
        return True
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_product_added() 