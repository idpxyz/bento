#!/usr/bin/env python3
"""
测试生成的 Pydantic 模型是否能正确工作
"""
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent.parent))

def import_module_from_path(module_name, file_path):
    """从文件路径导入模块，避免导入整个包"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# 测试 ProductAdded 模型
def test_product_added():
    """测试 ProductAdded 模型及其嵌套类型 ProductImage"""
    try:
        # 直接从文件导入模块，而不是通过包导入
        productadded_path = (
            Path(__file__).parent.parent / 
            "generated" / "models" / "productadded.py"
        )
        productadded = import_module_from_path("productadded", productadded_path)
        
        # 创建 ProductImage 实例
        image1 = productadded.ProductImage(
            url="https://example.com/image1.jpg",
            alt="产品图片1",
            is_primary=True
        )
        
        image2 = productadded.ProductImage(
            url="https://example.com/image2.jpg",
            alt="产品图片2",
            is_primary=False
        )
        
        # 创建 ProductAdded 实例
        product = productadded.ProductAdded(
            product_id="PROD-123",
            name="测试产品",
            description="这是一个用于测试的产品",
            price=99.99,
            categories=["电子", "手机"],
            images=[image1, image2],
            status=productadded.ProductStatus.ACTIVE,
            created_at=datetime.now(),
            created_by="user-123"
        )
        
        # 验证序列化
        json_data = product.model_dump_json()
        print(f"ProductAdded 序列化成功:")
        print(json.dumps(json.loads(json_data), indent=2, ensure_ascii=False))
        
        # 验证反序列化
        parsed_product = productadded.ProductAdded.model_validate_json(json_data)
        print(f"\n反序列化成功: {parsed_product.name}")
        print(f"嵌套字段访问成功: {parsed_product.images[0].url}")
        
        return True
    except Exception as e:
        print(f"测试 ProductAdded 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# 测试 OrderCreated 模型
def test_order_created():
    """测试 OrderCreated 模型及其嵌套类型 OrderItem"""
    try:
        # 直接从文件导入模块，而不是通过包导入
        ordercreated_path = (
            Path(__file__).parent.parent / 
            "generated" / "models" / "ordercreated.py"
        )
        ordercreated = import_module_from_path("ordercreated", ordercreated_path)
        
        # 创建 OrderItem 实例
        item1 = ordercreated.OrderItem(
            product_id="PROD-123",
            product_name="测试产品1",
            quantity=2,
            unit_price=99.99,
            subtotal=199.98
        )
        
        item2 = ordercreated.OrderItem(
            product_id="PROD-456",
            product_name="测试产品2",
            quantity=1,
            unit_price=49.99,
            subtotal=49.99
        )
        
        # 创建 OrderCreated 实例
        order = ordercreated.OrderCreated(
            order_id="ORD-123456",
            customer_id="CUST-123",
            items=[item1, item2],
            total_amount=249.97,
            currency="CNY",
            status="已付款",
            created_at=datetime.now()
        )
        
        # 验证序列化
        json_data = order.model_dump_json()
        print(f"\nOrderCreated 序列化成功:")
        print(json.dumps(json.loads(json_data), indent=2, ensure_ascii=False))
        
        # 验证反序列化
        parsed_order = ordercreated.OrderCreated.model_validate_json(json_data)
        print(f"\n反序列化成功: {parsed_order.order_id}")
        print(f"嵌套字段访问成功: {parsed_order.items[0].product_name}")
        
        return True
    except Exception as e:
        print(f"测试 OrderCreated 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    product_test_success = test_product_added()
    order_test_success = test_order_created()
    
    if product_test_success and order_test_success:
        print("\n所有测试都成功完成！")
        sys.exit(0)
    else:
        print("\n测试失败！")
        sys.exit(1) 