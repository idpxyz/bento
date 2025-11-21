"""测试 Mock Adapters

演示如何使用 Mock Adapters 进行开发和测试。
"""

import asyncio

from contexts.ordering.domain.ports.services import (
    PaymentMethod,
    PaymentRequest,
)
from contexts.ordering.infrastructure.adapters import (
    MockInventoryAdapter,
    MockNotificationAdapter,
    MockPaymentAdapter,
)
from contexts.ordering.infrastructure.adapters.services.mock_inventory_adapter import (
    ReservationRequest,
)


async def test_mock_payment_adapter():
    """测试 MockPaymentAdapter"""
    print("\n" + "=" * 70)
    print("🧪 测试 MockPaymentAdapter")
    print("=" * 70)

    # 创建适配器
    payment = MockPaymentAdapter()

    # 1. 处理支付
    payment_request = PaymentRequest(
        order_id="ORDER_001",
        amount=999.99,
        currency="CNY",
        payment_method=PaymentMethod.ALIPAY,
        description="测试订单支付",
    )

    result = await payment.process_payment(payment_request)
    print("\n✅ 支付成功！")
    print(f"   交易ID: {result.transaction_id}")
    print(f"   状态: {result.status}")
    print(f"   金额: ${result.amount:.2f}")

    # 2. 查询支付
    query_result = await payment.query_payment(result.transaction_id)
    print(f"\n🔍 查询支付状态: {query_result.status}")

    # 3. 退款
    refund_result = await payment.refund_payment(result.transaction_id, 500.0)
    print("\n💰 退款成功！")
    print(f"   退款ID: {refund_result.transaction_id}")
    print(f"   退款金额: ${refund_result.amount:.2f}")


async def test_mock_notification_adapter():
    """测试 MockNotificationAdapter"""
    print("\n" + "=" * 70)
    print("🧪 测试 MockNotificationAdapter")
    print("=" * 70)

    # 创建适配器
    notification = MockNotificationAdapter(verbose=True)

    # 1. 订单创建通知
    result1 = await notification.send_order_created(
        order_id="ORDER_001", customer_email="customer@example.com"
    )
    print(f"✅ 通知发送成功: {result1.notification_id}")

    # 2. 订单支付通知
    result2 = await notification.send_order_paid(
        order_id="ORDER_001", customer_email="customer@example.com"
    )
    print(f"✅ 通知发送成功: {result2.notification_id}")

    # 3. 订单发货通知
    result3 = await notification.send_order_shipped(
        order_id="ORDER_001", customer_email="customer@example.com", tracking_number="SF1234567890"
    )
    print(f"✅ 通知发送成功: {result3.notification_id}")

    # 查看通知历史
    history = notification.get_notification_history()
    print(f"\n📊 总共发送了 {len(history)} 条通知")


async def test_mock_inventory_adapter():
    """测试 MockInventoryAdapter"""
    print("\n" + "=" * 70)
    print("🧪 测试 MockInventoryAdapter")
    print("=" * 70)

    # 创建适配器
    inventory = MockInventoryAdapter(default_quantity=100)

    # 1. 检查库存
    product_id = "PROD_001"
    is_available = await inventory.check_availability(product_id, 10)
    print(f"\n✅ 库存检查: {'充足' if is_available else '不足'}")

    # 2. 获取库存信息
    inventory_item = await inventory.get_inventory(product_id)
    print("\n📦 库存信息:")
    print(f"   产品ID: {inventory_item.product_id}")
    print(f"   可用数量: {inventory_item.available_quantity}")
    print(f"   预留数量: {inventory_item.reserved_quantity}")
    print(f"   总数量: {inventory_item.total_quantity}")

    # 3. 预留库存
    reservation_request = ReservationRequest(
        order_id="ORDER_001", items=[("PROD_001", 10), ("PROD_002", 5)]
    )
    reservation_result = await inventory.reserve_inventory(reservation_request)
    print(f"\n✅ 库存预留: {reservation_result.reservation_id}")
    print(f"   成功: {reservation_result.success}")

    # 4. 扣减库存
    deduct_success = await inventory.deduct_inventory("PROD_001", 10)
    print(f"\n✅ 库存扣减: {'成功' if deduct_success else '失败'}")

    # 5. 恢复库存
    restore_success = await inventory.restore_inventory("PROD_001", 5)
    print(f"✅ 库存恢复: {'成功' if restore_success else '失败'}")

    # 6. 释放预留
    release_success = await inventory.release_reservation(reservation_result.reservation_id)
    print(f"✅ 预留释放: {'成功' if release_success else '失败'}")


async def test_all_adapters_together():
    """测试所有 Adapters 协同工作"""
    print("\n" + "=" * 70)
    print("🧪 测试所有 Adapters 协同工作（模拟完整订单流程）")
    print("=" * 70)

    # 创建所有适配器
    payment = MockPaymentAdapter()
    notification = MockNotificationAdapter(verbose=False)  # 关闭详细输出
    inventory = MockInventoryAdapter()

    order_id = "ORDER_FULL_001"
    customer_email = "customer@example.com"
    product_items = [("PROD_001", 2), ("PROD_002", 1)]

    # 1. 检查库存
    print("\n📦 步骤 1: 检查库存...")
    availability = await inventory.check_availability_batch(product_items)
    all_available = all(availability.values())

    if not all_available:
        print("❌ 库存不足，订单创建失败")
        return

    print("✅ 库存充足")

    # 2. 预留库存
    print("\n🔒 步骤 2: 预留库存...")
    reservation_request = ReservationRequest(order_id=order_id, items=product_items)
    reservation_result = await inventory.reserve_inventory(reservation_request)

    if not reservation_result.success:
        print("❌ 库存预留失败")
        return

    print(f"✅ 库存已预留: {reservation_result.reservation_id}")

    # 3. 发送订单创建通知
    print("\n📧 步骤 3: 发送订单创建通知...")
    await notification.send_order_created(order_id, customer_email)
    print("✅ 通知已发送")

    # 4. 处理支付
    print("\n💳 步骤 4: 处理支付...")
    payment_request = PaymentRequest(
        order_id=order_id,
        amount=1299.99,
        payment_method=PaymentMethod.ALIPAY,
    )
    payment_result = await payment.process_payment(payment_request)
    print(f"✅ 支付成功: {payment_result.transaction_id}")

    # 5. 扣减库存
    print("\n➖ 步骤 5: 扣减库存...")
    for product_id, quantity in product_items:
        await inventory.deduct_inventory(product_id, quantity)
    print("✅ 库存已扣减")

    # 6. 发送支付成功通知
    print("\n📧 步骤 6: 发送支付成功通知...")
    await notification.send_order_paid(order_id, customer_email)
    print("✅ 通知已发送")

    # 7. 发送发货通知
    print("\n📦 步骤 7: 发送发货通知...")
    await notification.send_order_shipped(order_id, customer_email, "SF9876543210")
    print("✅ 通知已发送")

    print("\n" + "=" * 70)
    print("🎉 完整订单流程测试完成！")
    print("=" * 70)


async def main():
    """运行所有测试"""
    print("\n" + "🚀 " + "=" * 66)
    print("🚀 Mock Adapters 测试套件")
    print("🚀 " + "=" * 66)

    # 单独测试每个 Adapter
    await test_mock_payment_adapter()
    await test_mock_notification_adapter()
    await test_mock_inventory_adapter()

    # 测试协同工作
    await test_all_adapters_together()

    print("\n" + "✅ " + "=" * 66)
    print("✅ 所有测试完成！")
    print("✅ " + "=" * 66 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
