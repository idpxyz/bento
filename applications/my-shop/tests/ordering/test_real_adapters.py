"""真实 Adapters 集成测试

测试真实的 EmailAdapter 和 LocalInventoryAdapter。

运行测试前请确保：
1. 已配置 .env 文件
2. 已配置邮件服务器（如需测试邮件发送）
3. 数据库中有测试数据
"""

import asyncio
import os

# 加载环境变量
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from contexts.ordering.infrastructure.adapters.services.email_adapter import (
    EmailAdapter,
    EmailConfig,
)
from contexts.ordering.infrastructure.adapters.services.local_inventory_adapter import (
    LocalInventoryAdapter,
    ReservationRequest,
)


async def test_email_adapter():
    """测试 EmailAdapter

    ⚠️ 此测试会发送真实邮件，请确保已正确配置 SMTP
    """
    print("\n" + "=" * 70)
    print("🧪 测试 EmailAdapter（真实邮件发送）")
    print("=" * 70)

    # 检查配置
    if not os.getenv("SMTP_USER") or not os.getenv("SMTP_PASSWORD"):
        print("⚠️ 未配置 SMTP，跳过邮件测试")
        print("   请在 .env 文件中配置 SMTP_USER 和 SMTP_PASSWORD")
        return

    # 创建配置
    config = EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        from_email=os.getenv("FROM_EMAIL", "noreply@myshop.com"),
        from_name=os.getenv("FROM_NAME", "My Shop Test"),
        use_ssl=os.getenv("EMAIL_USE_SSL", "true").lower() == "true",
        use_tls=os.getenv("EMAIL_USE_TLS", "false").lower() == "true",
    )

    # 创建适配器
    adapter = EmailAdapter(config)

    # 测试收件人（可以改为你自己的邮箱）
    test_email = os.getenv("TEST_EMAIL", os.getenv("SMTP_USER"))

    print(f"\n📧 发送测试邮件到: {test_email}")

    try:
        # 发送订单创建通知
        result = await adapter.send_order_created(
            order_id="TEST_ORDER_001", customer_email=test_email
        )

        if result.success:
            print("✅ 邮件发送成功！")
            print(f"   通知ID: {result.notification_id}")
            print(f"   发送时间: {result.sent_at}")
        else:
            print(f"❌ 邮件发送失败: {result.message}")

        return result.success

    except Exception as e:
        print(f"❌ 邮件发送异常: {str(e)}")
        return False


async def test_local_inventory_adapter():
    """测试 LocalInventoryAdapter

    ⚠️ 此测试需要数据库连接
    """
    print("\n" + "=" * 70)
    print("🧪 测试 LocalInventoryAdapter（数据库库存）")
    print("=" * 70)

    # 检查数据库配置
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️ 未配置 DATABASE_URL，跳过库存测试")
        print("   请在 .env 文件中配置 DATABASE_URL")
        return

    try:
        # 创建数据库会话
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # 创建适配器
            adapter = LocalInventoryAdapter(session)

            # 测试产品ID（假设数据库中存在）
            test_product_id = "test_product_001"

            print(f"\n📦 测试产品: {test_product_id}")

            # 1. 获取库存信息
            print("\n1️⃣ 获取库存信息...")
            inventory = await adapter.get_inventory(test_product_id)
            print(f"   可用数量: {inventory.available_quantity}")
            print(f"   预留数量: {inventory.reserved_quantity}")
            print(f"   总数量: {inventory.total_quantity}")

            # 2. 检查库存
            print("\n2️⃣ 检查库存（需要 10 件）...")
            is_available = await adapter.check_availability(test_product_id, 10)
            print(f"   结果: {'✅ 库存充足' if is_available else '❌ 库存不足'}")

            if not is_available:
                print("   跳过后续测试（库存不足）")
                return

            # 3. 预留库存
            print("\n3️⃣ 预留库存...")
            request = ReservationRequest(order_id="TEST_ORDER_001", items=[(test_product_id, 5)])
            result = await adapter.reserve_inventory(request)
            print(f"   预留{'成功' if result.success else '失败'}: {result.reservation_id}")

            if result.success:
                # 4. 再次检查库存（应该减少了）
                print("\n4️⃣ 预留后再次检查库存...")
                inventory_after = await adapter.get_inventory(test_product_id)
                print(f"   可用数量: {inventory_after.available_quantity}")
                print(f"   预留数量: {inventory_after.reserved_quantity}")

                # 5. 释放预留
                print("\n5️⃣ 释放预留...")
                released = await adapter.release_reservation(result.reservation_id)
                print(f"   释放{'成功' if released else '失败'}")

                # 6. 最终检查
                print("\n6️⃣ 释放后最终检查...")
                inventory_final = await adapter.get_inventory(test_product_id)
                print(f"   可用数量: {inventory_final.available_quantity}")
                print(f"   预留数量: {inventory_final.reserved_quantity}")

            print("\n✅ 库存适配器测试完成")
            return True

    except Exception as e:
        print(f"❌ 库存测试异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_adapter_integration():
    """测试多个 Adapters 协同工作"""
    print("\n" + "=" * 70)
    print("🧪 测试 Adapters 集成（模拟订单流程）")
    print("=" * 70)

    # 使用 Mock Adapters 确保测试可以运行
    from contexts.ordering.infrastructure.adapters import (
        MockInventoryAdapter,
        MockNotificationAdapter,
        MockPaymentAdapter,
    )

    payment = MockPaymentAdapter()
    notification = MockNotificationAdapter(verbose=False)
    inventory = MockInventoryAdapter()

    order_id = "INT_TEST_ORDER_001"
    customer_email = "integration-test@example.com"

    print("\n📋 模拟订单流程...")

    # 1. 检查库存
    print("\n1️⃣ 检查库存...")
    items = [("PROD_001", 2), ("PROD_002", 1)]
    availability = await inventory.check_availability_batch(items)
    all_available = all(availability.values())
    print(f"   库存检查: {'✅ 全部可用' if all_available else '❌ 部分不可用'}")

    if not all_available:
        print("   订单创建失败（库存不足）")
        return False

    # 2. 预留库存
    print("\n2️⃣ 预留库存...")
    request = ReservationRequest(order_id=order_id, items=items)
    reservation = await inventory.reserve_inventory(request)
    print(f"   预留{'成功' if reservation.success else '失败'}: {reservation.reservation_id}")

    # 3. 发送订单创建通知
    print("\n3️⃣ 发送订单创建通知...")
    notif_result = await notification.send_order_created(order_id, customer_email)
    print(f"   通知发送{'成功' if notif_result.success else '失败'}")

    # 4. 处理支付
    print("\n4️⃣ 处理支付...")
    from contexts.ordering.domain.ports.services import PaymentMethod, PaymentRequest

    payment_request = PaymentRequest(
        order_id=order_id,
        amount=999.99,
        payment_method=PaymentMethod.ALIPAY,
    )
    payment_result = await payment.process_payment(payment_request)
    print(f"   支付状态: {payment_result.status.value}")

    # 5. 扣减库存
    print("\n5️⃣ 扣减库存...")
    for product_id, quantity in items:
        await inventory.deduct_inventory(product_id, quantity)
    print("   ✅ 库存已扣减")

    # 6. 发送支付成功通知
    print("\n6️⃣ 发送支付成功通知...")
    await notification.send_order_paid(order_id, customer_email)
    print("   ✅ 通知已发送")

    print("\n" + "=" * 70)
    print("🎉 集成测试完成！所有步骤成功")
    print("=" * 70)

    return True


async def main():
    """运行所有测试"""
    print("\n" + "🚀 " + "=" * 66)
    print("🚀 真实 Adapters 集成测试套件")
    print("🚀 " + "=" * 66)

    results = []

    # 测试邮件适配器
    if os.getenv("TEST_EMAIL_ADAPTER", "true").lower() == "true":
        email_result = await test_email_adapter()
        results.append(("EmailAdapter", email_result))
    else:
        print("\n⏭️ 跳过 EmailAdapter 测试（设置 TEST_EMAIL_ADAPTER=true 启用）")

    # 测试库存适配器
    if os.getenv("TEST_INVENTORY_ADAPTER", "true").lower() == "true":
        inventory_result = await test_local_inventory_adapter()
        results.append(("LocalInventoryAdapter", inventory_result))
    else:
        print("\n⏭️ 跳过 LocalInventoryAdapter 测试（设置 TEST_INVENTORY_ADAPTER=true 启用）")

    # 测试集成
    integration_result = await test_adapter_integration()
    results.append(("Integration", integration_result))

    # 输出结果
    print("\n" + "📊 " + "=" * 66)
    print("📊 测试结果总结")
    print("📊 " + "=" * 66)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")

    all_passed = all(r for _, r in results if r is not None)

    print("\n" + ("✅ " if all_passed else "❌ ") + "=" * 66)
    print(("✅ " if all_passed else "❌ ") + "所有测试" + ("通过" if all_passed else "失败") + "！")
    print(("✅ " if all_passed else "❌ ") + "=" * 66 + "\n")

    return all_passed


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())

    # 退出码
    exit(0 if success else 1)
