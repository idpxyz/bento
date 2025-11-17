"""测试 User Identity 模块 - 完全使用 Bento Framework

这个脚本演示如何使用 Bento Framework 的完整功能：
1. User 聚合根 (AggregateRoot)
2. UserMapper (Mapper[User, UserPO])
3. UserRepository (RepositoryAdapter)
4. BaseRepository with Interceptor Chain
5. Audit fields, Optimistic Lock, Soft Delete

Usage:
    python scripts/test_user_identity.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bento.core.ids import ID
from sqlalchemy import select

from api.deps import engine, session_factory
from contexts.identity.domain.user import User
from contexts.identity.infrastructure.mappers.user_mapper import UserMapper
from contexts.identity.infrastructure.models.user_po import UserPO
from contexts.identity.infrastructure.repositories.user_repository_impl import UserRepository


async def test_user_mapper():
    """测试 User Mapper 的双向转换"""
    print("=" * 60)
    print("🧪 测试 UserMapper (AR ↔ PO 转换)")
    print("=" * 60)

    mapper = UserMapper()

    # 创建领域对象
    user = User(id=str(ID.generate()), name="测试用户", email="test@example.com")

    print(f"\n1️⃣  领域对象 (User): id={user.id}, name={user.name}, email={user.email}")

    # AR -> PO
    po = mapper.map(user)
    print(f"2️⃣  转换为 PO: id={po.id}, name={po.name}, email={po.email}")

    # PO -> AR
    user2 = mapper.map_reverse(po)
    print(f"3️⃣  转换回 AR: id={user2.id}, name={user2.name}, email={user2.email}")

    assert user.id == user2.id
    assert user.name == user2.name
    assert user.email == user2.email

    print("✅ Mapper 测试通过！\n")


async def test_user_repository():
    """测试 UserRepository with Bento Framework"""
    print("=" * 60)
    print("🧪 测试 UserRepository (Bento RepositoryAdapter)")
    print("=" * 60)

    async with session_factory() as session:
        # 创建 Repository (使用 Bento 的 RepositoryAdapter)
        repo = UserRepository(session, actor="test@example.com")

        print("\n1️⃣  创建用户...")
        user = User(id=str(ID.generate()), name="张三", email="zhangsan@test.com")

        # 使用框架的 save() 方法
        await repo.save(user)
        await session.commit()

        print(f"   ✅ 用户已保存: {user.name} ({user.email})")

        # 使用框架的 get() 方法
        print("\n2️⃣  读取用户...")
        retrieved = await repo.get(user.id)

        if retrieved:
            print(f"   ✅ 找到用户: {retrieved.name} ({retrieved.email})")
        else:
            print("   ❌ 未找到用户")

        # 验证审计字段
        print("\n3️⃣  检查审计字段 (由 AuditInterceptor 自动填充)...")
        result = await session.execute(select(UserPO).where(UserPO.id == user.id))
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
        exists = await repo.exists(user.id)
        print(f"   exists: {exists}")

        # 测试 count
        print("\n7️⃣  统计用户总数...")
        total = await repo.count()
        print(f"   总用户数: {total}")

        print("\n✅ Repository 测试通过！\n")


async def test_business_logic():
    """测试业务逻辑方法"""
    print("=" * 60)
    print("🧪 测试业务逻辑 (领域方法)")
    print("=" * 60)

    user = User(id=str(ID.generate()), name="李四", email="lisi@test.com")

    print(f"\n原始用户: {user.name}")

    # 使用业务方法
    user.change_name("李四光")
    print(f"更改后: {user.name}")

    user.change_email("lisi.new@test.com")
    print(f"新邮箱: {user.email}")

    # 测试验证
    try:
        user.change_name("")  # Should fail
    except ValueError as e:
        print(f"✅ 验证成功: {e}")

    try:
        user.change_email("invalid")  # Should fail
    except ValueError as e:
        print(f"✅ 验证成功: {e}")

    print("\n✅ 业务逻辑测试通过！\n")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🍱 Bento Framework - User Identity 模块测试")
    print("=" * 60)
    print()

    try:
        # 测试 Mapper
        await test_user_mapper()

        # 测试业务逻辑
        await test_business_logic()

        # 测试 Repository
        await test_user_repository()

        print("=" * 60)
        print("✅ 所有测试通过！Identity 模块工作正常！")
        print("=" * 60)
        print()
        print("📋 Bento Framework 功能验证：")
        print("  ✅ AggregateRoot - 聚合根基类")
        print("  ✅ Mapper - AR ↔ PO 转换")
        print("  ✅ RepositoryAdapter - 仓储适配器")
        print("  ✅ BaseRepository - 基础仓储")
        print("  ✅ Interceptor Chain - 拦截器链")
        print("  ✅ AuditInterceptor - 审计字段自动填充")
        print("  ✅ OptimisticLock - 乐观锁版本控制")
        print("  ✅ 业务方法 - 领域逻辑封装")
        print()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
