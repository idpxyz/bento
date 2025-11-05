#!/usr/bin/env python3
"""
测试 Proto 到 Pydantic 模型转换器的功能
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent.parent))

# 导入生成器
from src.idp.framework.infrastructure.schema.cli.generators.proto_generator import (
    generate_pydantic_from_proto,
    parse_proto_file,
)


def import_module_from_path(module_name, file_path):
    """从文件路径导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

class TestProtoGenerator(unittest.TestCase):
    """测试 Proto 到 Pydantic 模型转换器"""
    
    def setUp(self):
        """准备测试环境"""
        # 创建临时目录用于存放测试文件
        self.temp_dir = tempfile.mkdtemp()
        
        # 测试用 Proto 文件内容 - 包含嵌套类型和注释选项
        self.proto_content = """
        syntax = "proto3";
        
        package test;
        
        import "google/protobuf/timestamp.proto";
        
        // 订单创建事件
        message OrderCreated {
            string order_id = 1;                        // 订单ID
            string customer_id = 2;                     // 客户ID
            repeated OrderItem items = 3;               // 订单项目
            double total_amount = 4;                    // 总金额
            string currency = 5;                        // 货币
            string status = 6;                          // 订单状态 选项: "pending", "paid", "shipped", "completed", "cancelled"
            google.protobuf.Timestamp created_at = 7;   // 创建时间
            
            // 支付方式
            enum PaymentMethod {
                CREDIT_CARD = 0;    // 信用卡
                DEBIT_CARD = 1;     // 借记卡
                ALIPAY = 2;         // 支付宝
                WECHAT = 3;         // 微信支付
                OTHER = 4;          // 其他
            }
            
            PaymentMethod payment_method = 8;          // 支付方式
            string channel = 9;                        // 销售渠道 选项: "web", "mobile", "store", "partner"
        }
        
        // 订单项目
        message OrderItem {
            string product_id = 1;                      // 产品ID
            string product_name = 2;                    // 产品名称
            int32 quantity = 3;                         // 数量
            double unit_price = 4;                      // 单价
            double subtotal = 5;                        // 小计
            
            // 产品类型
            string product_type = 6;                    // 产品类型 选项: "physical", "digital", "service", "subscription"
            
            // 折扣信息
            message Discount {
                string discount_id = 1;                 // 折扣ID
                string discount_name = 2;               // 折扣名称
                double discount_amount = 3;             // 折扣金额
                string discount_type = 4;               // 折扣类型 选项: "percentage", "fixed", "coupon"
            }
            
            // 商品折扣
            Discount discount = 7;                      // 折扣信息
        }
        """
        
        # 创建测试 Proto 文件
        self.proto_path = os.path.join(self.temp_dir, "test_order.proto")
        with open(self.proto_path, "w") as f:
            f.write(self.proto_content)
        
        # 设置输出路径
        self.output_path = os.path.join(self.temp_dir, "test_order.py")
    
    def tearDown(self):
        """清理测试环境"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir)
    
    def test_parse_proto_file(self):
        """测试 Proto 文件解析功能"""
        package, messages, enums = parse_proto_file(self.proto_path)
        
        # 检查包名
        self.assertEqual(package, "test")
        
        # 检查消息数量 (OrderCreated, OrderItem, Discount)
        self.assertEqual(len(messages), 3)
        
        # 检查枚举数量 - 可能有多个，我们只需要确保PaymentMethod在其中
        enum_names = [enum["simple_name"] for enum in enums]
        self.assertIn("PaymentMethod", enum_names)
        
        # 验证消息名称
        message_names = [msg["simple_name"] for msg in messages]
        self.assertIn("OrderCreated", message_names)
        self.assertIn("OrderItem", message_names)
        self.assertIn("Discount", message_names)
        
        # 验证嵌套结构
        for msg in messages:
            if msg["simple_name"] == "Discount":
                self.assertEqual(msg["parent"], "OrderItem")
    
    def test_generate_pydantic_from_proto(self):
        """测试 Pydantic 模型生成功能"""
        # 生成 Pydantic 模型
        generate_pydantic_from_proto(self.proto_path, self.output_path)
        
        # 验证生成的文件存在
        self.assertTrue(os.path.exists(self.output_path))
        
        # 导入生成的模块
        module = import_module_from_path("test_order", self.output_path)
        
        # 验证类是否存在
        self.assertTrue(hasattr(module, "OrderCreated"))
        self.assertTrue(hasattr(module, "OrderItem"))
        self.assertTrue(hasattr(module, "Discount"))
        self.assertTrue(hasattr(module, "PaymentMethod"))
        
        # 测试创建实例
        try:
            # 创建折扣实例
            discount = module.Discount(
                discount_id="DISC123",
                discount_name="年终促销",
                discount_amount=10.0,
                discount_type="percentage"
            )
            
            # 创建订单项目实例
            item = module.OrderItem(
                product_id="PROD456",
                product_name="智能手机",
                quantity=1,
                unit_price=999.99,
                subtotal=999.99,
                product_type="physical",
                discount=discount
            )
            
            # 创建订单实例
            order = module.OrderCreated(
                order_id="ORD789",
                customer_id="CUST123",
                items=[item],
                total_amount=999.99,
                currency="CNY",
                status="paid",
                created_at=datetime.now(),
                payment_method=module.PaymentMethod.ALIPAY,
                channel="mobile"
            )
            
            # 序列化和反序列化测试
            json_data = order.model_dump_json()
            parsed_order = module.OrderCreated.model_validate_json(json_data)
            
            # 验证字段值
            self.assertEqual(parsed_order.order_id, "ORD789")
            self.assertEqual(parsed_order.items[0].product_name, "智能手机")
            self.assertEqual(parsed_order.items[0].discount.discount_name, "年终促销")
            self.assertEqual(parsed_order.payment_method, "alipay")
            
            # 测试枚举验证
            with self.assertRaises(Exception):
                module.OrderCreated(
                    order_id="test",
                    payment_method="INVALID_METHOD"
                )
            
            # 测试 Literal 验证
            with self.assertRaises(Exception):
                module.OrderCreated(
                    order_id="test",
                    status="invalid_status"
                )
            
            # 验证有效的 Literal 值
            valid_statuses = ["pending", "paid", "shipped", "completed", "cancelled"]
            for status in valid_statuses:
                # 不应该抛出异常
                module.OrderCreated(order_id="test", status=status)
                
        except Exception as e:
            self.fail(f"创建实例失败: {e}")

if __name__ == "__main__":
    unittest.main() 