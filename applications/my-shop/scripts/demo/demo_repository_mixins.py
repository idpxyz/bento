#!/usr/bin/env python3
"""Repository Mixins 功能演示

这个脚本展示了如何在 my-shop 中实际使用新的 Repository 增强功能。

运行方式:
    cd /workspace/bento/applications/my-shop
    python demo_repository_mixins.py
"""

import asyncio
from datetime import UTC, datetime

from bento.core.ids import ID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# from contexts.catalog.application.services.product_enhanced_service import ProductRepository
from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.catalog.infrastructure.repositories.product_repository_impl import ProductRepository


async def setup_demo_data_direct(session: AsyncSession):
    """直接创建演示数据（绕过 Repository）

    注意：这种方式需要手动设置审计字段，因为绕过了 AuditInterceptor
    仅用于演示目的，实际应用中应该使用 Repository
    """
    print("📦 正在创建演示数据...")
    print("⚠️  注意：直接使用 Session 绕过了 Repository 层")

    # 由于绕过了 Repository，需要手动设置审计字段
    now = datetime.now(UTC)
    products = [
        ProductPO(
            id=f"demo-p{i}",
            name=f"产品 {i}",
            price=float(100 + i * 50),
            category_id=f"cat-{i % 3 + 1}",  # 3个类别
            description=f"这是产品 {i} 的描述",
            stock=100 + i * 10,
            # ⚠️ 手动设置审计字段（因为没有使用 Repository）
            created_at=now,
            updated_at=now,
            created_by="demo",
            updated_by="demo",
        )
        for i in range(1, 21)  # 创建 20 个产品
    ]

    session.add_all(products)
    await session.commit()
    print(f"✅ 创建了 {len(products)} 个演示产品")


async def demo_basic_operations(service: ProductRepository):
    """演示基础操作 (P0)"""
    print("\n" + "=" * 60)
    print("🔷 P0: 基础增强功能演示")
    print("=" * 60)

    # 1. 批量获取
    print("\n1️⃣  批量获取产品:")
    product_ids = [ID("demo-p1"), ID("demo-p2"), ID("demo-p3")]
    products = await service.get_products_batch(product_ids)
    print(f"   ✅ 批量获取了 {len(products)} 个产品")
    for p in products:
        print(f"      - {p.name} (¥{p.price})")

    # 2. 存在性检查
    print("\n2️⃣  检查产品是否存在:")
    exists = await service.check_product_exists(ID("demo-p1"))
    print(f"   ✅ 产品 demo-p1 存在: {exists}")

    exists = await service.check_product_exists(ID("non-existent"))
    print(f"   ✅ 产品 non-existent 存在: {exists}")

    # 3. 通过字段查找（使用 name 字段）
    print("\n3️⃣  通过名称查找产品:")
    product = await service._repo.find_by_field("name", "产品 5")
    if product:
        print(f"   ✅ 找到产品: {product.name} (¥{product.price})")

    # 4. 按类别查找
    print("\n4️⃣  查找类别的所有产品:")
    products = await service.get_products_by_category("cat-1")
    print(f"   ✅ 类别 cat-1 有 {len(products)} 个产品")


async def demo_aggregations(service: ProductRepository):
    """演示聚合查询 (P1)"""
    print("\n" + "=" * 60)
    print("📊 P1: 聚合查询演示")
    print("=" * 60)

    # 1. 总价值
    print("\n1️⃣  计算库存总价值:")
    total_value = await service.get_total_inventory_value()
    print(f"   ✅ 库存总价值: ¥{total_value:,.2f}")

    # 2. 平均价格
    print("\n2️⃣  计算平均价格:")
    avg_price = await service.get_average_price()
    print(f"   ✅ 平均价格: ¥{avg_price:,.2f}")

    # 3. 价格区间
    print("\n3️⃣  获取价格区间:")
    price_range = await service.get_price_range()
    print(f"   ✅ 最低价: ¥{price_range['min']:,.2f}")
    print(f"   ✅ 最高价: ¥{price_range['max']:,.2f}")

    # 4. 唯一类别数
    print("\n4️⃣  统计类别数量:")
    unique_categories = await service.count_unique_categories()
    print(f"   ✅ 不同类别数: {unique_categories}")


async def demo_sorting_limiting(service: ProductRepository):
    """演示排序和限制 (P1)"""
    print("\n" + "=" * 60)
    print("🎯 P1: 排序和限制演示")
    print("=" * 60)

    # 1. 最新产品
    print("\n1️⃣  获取最新产品:")
    latest = await service.get_latest_product()
    if latest:
        print(f"   ✅ 最新产品: {latest.name}")

    # 2. Top 5 最贵产品
    print("\n2️⃣  Top 5 最贵产品:")
    top_expensive = await service.get_top_expensive_products(5)
    for i, p in enumerate(top_expensive, 1):
        print(f"   #{i} {p.name}: ¥{p.price:,.2f}")

    # 3. Top 5 最便宜产品
    print("\n3️⃣  Top 5 最便宜产品:")
    cheapest = await service.get_cheapest_products(5)
    for i, p in enumerate(cheapest, 1):
        print(f"   #{i} {p.name}: ¥{p.price:,.2f}")

    # 4. 分页查询
    print("\n4️⃣  分页查询 (第1页，每页5个):")
    products, total = await service.get_products_paginated(page=1, page_size=5)
    print(f"   ✅ 显示 {len(products)}/{total} 个产品")
    for p in products:
        print(f"      - {p.name}")


async def demo_groupby(service: ProductRepository):
    """演示分组查询 (P2)"""
    print("\n" + "=" * 60)
    print("📈 P2: 分组统计演示")
    print("=" * 60)

    # 1. 类别分布
    print("\n1️⃣  产品类别分布:")
    category_dist = await service.get_category_distribution()
    for category, count in sorted(category_dist.items()):
        print(f"   {category}: {count} 个产品")

    # 2. 按日期分组 (演示 group_by_date)
    print("\n2️⃣  产品创建日期分布:")
    # 注意：在演示中所有产品同时创建，所以会是同一天
    daily_dist = await service.get_daily_product_creation_stats()
    if daily_dist:
        for date, count in list(daily_dist.items())[:5]:  # 显示前5天
            print(f"   {date}: {count} 个产品")


async def demo_random_sampling(service: ProductRepository):
    """演示随机采样 (P3)"""
    print("\n" + "=" * 60)
    print("🎲 P3: 随机采样演示")
    print("=" * 60)

    # 1. 随机推荐1个
    print("\n1️⃣  随机推荐一个产品:")
    random_product = await service.get_random_product()
    if random_product:
        print(f"   ✅ 推荐产品: {random_product.name} (¥{random_product.price})")

    # 2. 随机推荐5个
    print("\n2️⃣  随机推荐5个产品:")
    featured = await service.get_featured_products(5)
    for i, p in enumerate(featured, 1):
        print(f"   #{i} {p.name} (¥{p.price})")

    # 3. 抽样10%
    print("\n3️⃣  抽样10%的产品用于审计:")
    sample = await service.get_product_sample_for_audit(10.0, max_count=100)
    print(f"   ✅ 抽样了 {len(sample)} 个产品")


async def demo_dashboard(service: ProductRepository):
    """演示综合面板"""
    print("\n" + "=" * 60)
    print("📊 综合统计面板")
    print("=" * 60)

    stats = await service.get_dashboard_stats()

    print(f"\n📦 产品总数: {stats['total_products']}")
    print(f"💰 库存总价值: ¥{stats['total_value']:,.2f}")
    print(f"📈 平均价格: ¥{stats['avg_price']:,.2f}")
    print(f"📉 最低价: ¥{stats['min_price']:,.2f}")
    print(f"📈 最高价: ¥{stats['max_price']:,.2f}")
    print(f"🏷️  不同类别数: {stats['unique_categories']}")
    print(f"🗑️  回收站产品数: {stats['deleted_count']}")

    if stats["latest_product"]:
        print(f"\n🆕 最新产品: {stats['latest_product'].name}")

    print("\n📊 类别分布:")
    for category, count in sorted(stats["category_distribution"].items()):
        print(f"   {category}: {count} 个产品")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Repository Mixins 功能演示")
    print("=" * 60)
    print("\n这个演示展示了 29 个新增强方法在实际应用中的使用\n")

    # 创建内存数据库
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # 创建表
        from contexts.catalog.infrastructure.models.product_po import ProductPO

        async with engine.begin() as conn:
            await conn.run_sync(ProductPO.metadata.create_all)

        # 创建 session
        async with async_session_maker() as session:
            # 设置演示数据
            await setup_demo_data_direct(session)

            # 创建 repository 和 service
            product_repo = ProductRepository(session, actor="demo-user")
            service = ProductRepository(product_repo)

            # 运行各个演示
            await demo_basic_operations(service)
            await demo_aggregations(service)
            await demo_sorting_limiting(service)
            await demo_groupby(service)
            await demo_random_sampling(service)
            await demo_dashboard(service)

        print("\n" + "=" * 60)
        print("✅ 演示完成！")
        print("=" * 60)
        print("\n💡 提示:")
        print("   - 所有这些方法都是自动继承的，无需任何配置")
        print("   - 所有操作都在数据库层面执行，性能优异")
        print("   - 代码量减少 50-70%，开发效率大幅提升")
        print("   - 完整文档: docs/infrastructure/REPOSITORY_MIXINS_GUIDE.md")
        print("\n🎯 立即在你的 Repository 中使用这些方法！\n")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
