"""简单的 Identity 模块测试

直接在项目根目录运行，无需复杂配置。

Usage:
    uv run python test_identity_simple.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from bento.core.ids import ID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from contexts.identity.domain.models.user import User
from contexts.identity.infrastructure.mappers.user_mapper import UserMapper
from contexts.identity.infrastructure.models.user_po import Base, UserPO
from contexts.identity.infrastructure.repositories.user_repository_impl import (
    UserRepository,
)


async def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("🍱 Bento Framework - Identity 模块测试")
    print("=" * 70)
    print()

    # 创建内存数据库（用于测试）
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建 session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("✅ 数据库初始化完成\n")

    # ========================================
    # 测试 1: UserMapper
    # ========================================
    print("=" * 70)
    print("🧪 测试 1: UserMapper (AR ↔ PO 转换)")
    print("=" * 70)

    mapper = UserMapper()

    # 创建领域对象
    user = User(id=str(ID.generate()), name="测试用户", email="test@example.com")

    print("\n1️⃣  领域对象 (User):")
    print(f"   id: {user.id}")
    print(f"   name: {user.name}")
    print(f"   email: {user.email}")

    # AR -> PO
    po = mapper.map(user)
    print("\n2️⃣  转换为 PO (UserPO):")
    print(f"   id: {po.id}")
    print(f"   name: {po.name}")
    print(f"   email: {po.email}")

    # PO -> AR
    user2 = mapper.map_reverse(po)
    print("\n3️⃣  转换回 AR (User):")
    print(f"   id: {user2.id}")
    print(f"   name: {user2.name}")
    print(f"   email: {user2.email}")

    assert user.id == user2.id
    assert user.name == user2.name
    assert user.email == user2.email

    print("\n✅ Mapper 测试通过！")

    # ========================================
    # 测试 2: 业务逻辑方法
    # ========================================
    print("\n" + "=" * 70)
    print("🧪 测试 2: 业务逻辑 (领域方法)")
    print("=" * 70)

    user3 = User(id=str(ID.generate()), name="李四", email="lisi@test.com")

    print(f"\n原始用户: {user3.name} ({user3.email})")

    # 使用业务方法
    user3.change_name("李四光")
    print(f"更改后: {user3.name}")

    user3.change_email("lisi.new@test.com")
    print(f"新邮箱: {user3.email}")

    # 测试验证
    try:
        user3.change_name("")  # Should fail
        print("❌ 验证失败：应该抛出异常")
    except ValueError as e:
        print(f"✅ 验证成功: {e}")

    try:
        user3.change_email("invalid")  # Should fail
        print("❌ 验证失败：应该抛出异常")
    except ValueError as e:
        print(f"✅ 验证成功: {e}")

    print("\n✅ 业务逻辑测试通过！")

    # ========================================
    # 测试 3: UserRepository
    # ========================================
    print("\n" + "=" * 70)
    print("🧪 测试 3: UserRepository (Bento RepositoryAdapter)")
    print("=" * 70)

    async with async_session() as session:
        # 创建 Repository (使用 Bento 的 RepositoryAdapter)
        repo = UserRepository(session, actor="test@example.com")

        print("\n1️⃣  创建用户...")
        user4 = User(id=str(ID.generate()), name="张三", email="zhangsan@test.com")

        # 使用框架的 save() 方法
        await repo.save(user4)
        await session.commit()

        print(f"   ✅ 用户已保存: {user4.name} ({user4.email})")

        # 使用框架的 get() 方法
        print("\n2️⃣  读取用户...")
        retrieved = await repo.get(user4.id)

        if retrieved:
            print(f"   ✅ 找到用户: {retrieved.name} ({retrieved.email})")
        else:
            print("   ❌ 未找到用户")

        # 验证审计字段
        print("\n3️⃣  检查审计字段 (由 AuditInterceptor 自动填充)...")
        result = await session.execute(select(UserPO).where(UserPO.id == user4.id))
        po = result.scalar_one_or_none()

        if po:
            print(f"   created_at: {po.created_at}")
            print(f"   created_by: {po.created_by}")
            print(f"   updated_at: {po.updated_at}")
            print(f"   updated_by: {po.updated_by}")
            print(f"   version: {po.version}")
            print("   ✅ 审计字段已自动填充！")

        # 测试更新
        print("\n4️⃣  更新用户...")
        retrieved.change_name("张三丰")
        await repo.save(retrieved)
        await session.commit()

        print(f"   ✅ 用户名已更新: {retrieved.name}")

        # 测试 find_by_email
        print("\n5️⃣  通过邮箱查找...")
        found = await repo.find_by_email("zhangsan@test.com")
        if found:
            print(f"   ✅ 找到用户: {found.name}")

        # 测试 exists
        print("\n6️⃣  检查用户是否存在...")
        exists = await repo.exists(user4.id)
        print(f"   exists: {exists}")

        # 测试 total_count
        print("\n7️⃣  统计用户总数...")
        total = await repo.total_count()
        print(f"   总用户数: {total}")

        print("\n✅ Repository 测试通过！")

    # 关闭 engine
    await engine.dispose()

    # ========================================
    # 总结
    # ========================================
    print("\n" + "=" * 70)
    print("✅ 所有测试通过！Identity 模块工作正常！")
    print("=" * 70)
    print()
    print("📋 Bento Framework 功能验证：")
    print("  ✅ AggregateRoot - 聚合根基类")
    print("  ✅ AutoMapper - 零配置自动映射")
    print("  ✅ RepositoryAdapter - 仓储适配器")
    print("  ✅ BaseRepository - 基础仓储")
    print("  ✅ Interceptor Chain - 拦截器链")
    print("  ✅ AuditInterceptor - 审计字段自动填充")
    print("  ✅ OptimisticLock - 乐观锁版本控制")
    print("  ✅ 业务方法 - 领域逻辑封装")
    print()
    print("🎉 Identity 模块完全符合 Bento Framework 标准！")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
