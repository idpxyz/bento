"""仓储示例运行器

演示如何使用数据库连接API与仓储模式集成。
"""

import asyncio
import logging
import random
import uuid
from typing import Dict, List, Optional

from exception.classified import InfrastructureException
from sqlalchemy import text

from idp.framework.domain.repository import PageParams
from idp.framework.infrastructure.db import (
    Database,
    cleanup_database,
    get_database,
    initialize_database,
)
from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
    DatabaseType,
    PoolConfig,
    ReadWriteConfig,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.impl.version_change_logger import (
    VersionChangeLogger,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.demo.domain.user import (
    User,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.demo.domain.user_id import (
    UserId,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.demo.example import (
    UserQueryRepository,
    UserRepositoryImpl,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.demo.user_po import (
    UserPO,
)

from idp.framework.shared.utils.date_time import utc_now

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('repository_demo.log')
    ]
)
logger = logging.getLogger(__name__)


async def create_tables(db: Database):
    """创建数据库表

    Args:
        db: 数据库实例
    """
    try:
        # 创建表
        engine = db.connection_manager.engine._engine  # 获取实际的 SQLAlchemy 引擎
        async with engine.begin() as conn:
            # 只创建 UserPO 的表
            await conn.run_sync(UserPO.metadata.create_all)
        logger.info("UserPO 表创建成功")
    except Exception as e:
        logger.error(f"创建数据库表时出错: {e}")
        raise


async def populate_test_data(repo: UserRepositoryImpl, session):
    """填充测试数据

    Args:
        repo: 用户仓储
        session: 数据库会话

    Returns:
        创建的用户列表
    """
    # 获取表名
    table_name = UserPO.__tablename__

    try:
        # 创建测试用户
        test_users = [
            User(
                id=None,
                username="admin" +
                str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
                email="admin" + str(random.randint(1, 1000000)) +
                "@example.com",  # 修改邮箱以避免冲突
                full_name="Admin User",
                is_active=True,
                is_admin=True
            ),
            User(
                id=None,
                username="john.doe" +
                str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
                email="john.doe" +
                str(random.randint(1, 1000000))+"@example.com",  # 修改邮箱以避免冲突
                full_name="John Doe",
                is_active=True,
                is_admin=False
            ),
            User(
                id=None,
                username="jane.smith" +
                str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
                email="jane.smith" +
                str(random.randint(1, 1000000))+"@example.com",  # 修改邮箱以避免冲突
                full_name="Jane Smith",
                is_active=True,
                is_admin=False
            ),
            User(
                id=None,
                username="inactive.user" +
                str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
                email="inactive" +
                str(random.randint(1, 1000000))+"@example.com",  # 修改邮箱以避免冲突
                full_name="Inactive User",
                is_active=False,
                is_admin=False
            ),
            User(
                id=None,
                username="test.gmail" +
                str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
                email="test" + str(random.randint(1, 1000000)) +
                "@gmail.com",  # 修改邮箱以避免冲突
                full_name="Gmail Test User",
                is_active=True,
                is_admin=False
            )
        ]

        # 尝试使用仓储保存用户
        created_users = []
        try:
            # 方法1: 使用仓储API保存
            logger.info("尝试使用仓储API保存用户...")
            for user in test_users:
                # 检查用户是否已存在
                logger.info(
                    f"检查用户是否存在: username={user.username}, email={user.email}")
                existing_user = await repo.find_one_by_json({
                    "filters": [
                        {
                            "field": "username",
                            "operator": "eq",
                            "value": user.username
                        },
                        {
                            "field": "email",
                            "operator": "eq",
                            "value": user.email
                        },
                        {
                            "field": "deleted_at",
                            "operator": "is_null",
                            "value": None
                        }
                    ],
                    "page": {
                        "offset": 0,
                        "limit": 1
                    }
                })

                if existing_user:
                    logger.info(f"用户已存在: {existing_user}")
                    continue

                logger.info(f"创建新用户: {user}")
                created_user = await repo.save(user)
                created_users.append(created_user)
                logger.info(f"用户创建成功: {created_user}")

        except Exception as e:
            logger.error(f"使用仓储API保存用户失败: {e}")

            # 方法2: 直接使用SQL插入
            try:
                logger.info("尝试使用直接SQL插入用户...")
                created_users = []
                for i, user in enumerate(test_users):
                    # 检查用户是否已存在
                    check_sql = f"""
                    SELECT id FROM {table_name} WHERE username = :username
                    """
                    result = await session.execute(text(check_sql), {"username": user.username})
                    if result.scalar():
                        logger.info(f"用户 {user.username} 已存在，跳过创建")
                        continue

                    user_id = str(uuid.uuid4())
                    # 使用带时区的时间戳
                    now = utc_now()

                    insert_sql = f"""
                    INSERT INTO {table_name} 
                    (id, username, email, full_name, is_active, is_admin, version)
                    VALUES 
                    (:id, :username, :email, :full_name, :is_active, :is_admin, 1)
                    """
                    await session.execute(text(insert_sql), {
                        "id": user_id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "is_active": user.is_active,
                        "is_admin": user.is_admin
                    })

                    # 手动创建领域对象
                    user.id = UserId(user_id)  # 设置生成的ID
                    created_users.append(user)
                    logger.info(f"使用SQL创建用户: {user}")

                # 提交更改
                await session.commit()
                logger.info("用户数据插入成功并已提交")

            except Exception as e:
                logger.error(f"使用SQL插入用户失败: {e}")
                raise

        return created_users

    except Exception as e:
        logger.error(f"填充测试数据时出错: {e}")
        raise


async def demonstrate_queries(
    query_repo: UserQueryRepository,
    created_users: List[User]
):
    """演示查询操作

    Args:
        query_repo: 查询仓储
        created_users: 已创建的用户列表
    """
    logger.info("===== 基本查询操作 =====")

    if not created_users:
        logger.error("没有可用的测试用户数据进行查询演示")
        return

    try:
        # 按ID查询
        first_user_id = created_users[0].id
        logger.info(f"尝试按ID查询，ID={first_user_id}")
        user_by_id = await query_repo.get_by_id(str(first_user_id))
        logger.info(f"按ID查询结果: {user_by_id}")

        # 查询管理员用户
        logger.info("尝试查询管理员用户")
        admin_users = await query_repo.find_active_admins(page=1, page_size=20)
        logger.info(f"管理员用户数量: {admin_users.total}")
        for user in admin_users.items:
            logger.info(f"管理员用户: {user.email}")

        # 分页查询
        logger.info("尝试分页查询")
        page_result = await query_repo.find_active_users(
            page=1,
            page_size=20,
            sort_by="created_at",
            sort_order="desc"
        )
        logger.info(
            f"分页查询: 总数={page_result.total}, 当前页数据数量={len(page_result.items)}")

        # 查询活跃用户
        logger.info("尝试查询活跃用户")
        active_users = await query_repo.find_active_users(page=1, page_size=20)
        logger.info(f"活跃用户数量: {active_users.total}")

        # 查询Gmail用户
        logger.info("尝试查询Gmail用户")
        gmail_users = await query_repo.find_by_email_domain(
            "gmail.com",
            page=1,
            page_size=20
        )
        logger.info(f"Gmail用户数量: {gmail_users.total}")

        # 查询最近注册的用户
        logger.info("尝试查询最近注册的用户")
        recent_users = await query_repo.find_recent_users(
            days=30,
            page=1,
            page_size=20
        )
        logger.info(f"最近注册用户数量: {recent_users.total}")

        # 综合搜索
        logger.info("\n===== 综合搜索操作 =====")
        logger.info("尝试搜索'john'")
        search_results = await query_repo.search_users(
            search_term="john",
            status_filter="active",
            role_filter=None,
            page=1,
            page_size=10
        )
        logger.info(f"搜索'john'的结果: {search_results.total}条")

        # 复杂搜索
        logger.info("尝试复杂搜索")
        complex_results = await query_repo.search_users(
            search_term="admin",
            status_filter="active",
            role_filter=None,
            sort_by="username",
            sort_order="asc",
            page=1,
            page_size=10
        )
        logger.info(f"复杂搜索结果: {complex_results.total}条")

    except Exception as e:
        logger.error(f"查询演示过程中发生异常: {e}")
        raise


async def demonstrate_modifications(
    repo: UserRepositoryImpl,
    query_repo: UserQueryRepository
):
    """演示修改操作

    Args:
        repo: 仓储
        query_repo: 查询仓储
    """
    logger.info("\n===== 修改操作 =====")

    try:
        # 创建新用户
        logger.info("尝试创建新用户")
        new_user = User(
            id=None,
            username="new.user" +
            str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
            email="new.user" +
            str(random.randint(1, 1000000))+"@example.com",  # 修改邮箱以避免冲突
            full_name="New Test User",
            is_active=True,
            is_admin=False,
        )
        created_user = await repo.save(new_user)
        logger.info(f"创建新用户成功: {created_user}")

        # 验证用户是否真的被创建并保存到数据库
        saved_user = await repo.find_by_id(created_user.id)
        logger.info(f"验证用户是否保存成功: {saved_user is not None}")

        if saved_user:
            # 更新用户
            logger.info("尝试更新用户")

            # 获取当前版本号
            current_po = await repo.session.get(UserPO, str(saved_user.id))
            if current_po:
                # 设置正确的版本号
                # saved_user.version = current_po.version

                # 更新用户信息
                saved_user.update_profile(
                    full_name="Updated User Name" +
                    str(random.randint(1, 1000000)),  # 修改用户名以避免冲突
                    email="updated.email" +
                    str(random.randint(1, 1000000))+"@example.com"  # 修改邮箱以避免冲突
                )

                try:
                    updated_user = await repo.save(saved_user)
                    logger.info(f"更新用户成功: {updated_user}")

                    # 再次验证用户是否正确保存
                    updated_in_db = await repo.find_by_id(updated_user.id)
                    logger.info(
                        f"验证用户是否更新成功: {updated_in_db is not None}, "
                        f"email={updated_in_db.email if updated_in_db else 'N/A'}, "
                    )

                    # 删除用户
                    logger.info("\n--- 软删除测试 ---")
                    try:
                        # 检查事务状态并确保在活跃的事务中
                        if not repo.session.is_active:
                            await repo.session.begin()
                            logger.info("开始新事务进行软删除测试")

                        # 首先检查用户是否存在于数据库中
                        entity_to_delete = await repo.find_by_id(updated_user.id)
                        if entity_to_delete:
                            logger.info(f"找到要删除的用户: {entity_to_delete}")

                            # 打印删除前的详细状态
                            po = repo._to_po(entity_to_delete)
                            logger.info(
                                f"删除前实体状态: id={po.id}, deleted_at={po.deleted_at}, "
                                f"version={getattr(po, 'version', None)}"
                            )

                            # 设置软删除标记到上下文数据
                            repo.context_data["soft_deleted"] = True

                            # 执行软删除 - 单次调用，不重复
                            logger.info("执行软删除操作")
                            await repo.delete(entity_to_delete)
                            logger.info(f"删除用户成功: ID={entity_to_delete.id}")

                            # 提交事务以确保更改被持久化
                            await repo.session.commit()
                            logger.info("软删除事务已提交")

                            # 在新事务中验证软删除结果
                            await repo.session.begin()
                            logger.info("开始新事务验证软删除结果")

                            # 验证删除
                            deleted_user = await repo.find_by_id(updated_user.id)

                            # 直接SQL查询检查数据库中的记录状态，不依赖仓储方法
                            sql_check_query = """
                            SELECT id, email, deleted_at, version
                            FROM {table_name}
                            WHERE id = :id
                            """.format(table_name=repo.entity_type.__tablename__)

                            db_check_result = await repo.session.execute(
                                text(sql_check_query),
                                {"id": str(updated_user.id)}
                            )
                            db_record = db_check_result.fetchone()

                            if db_record:
                                logger.info(
                                    f"数据库记录状态: id={db_record[0]}, email={db_record[1]}, "
                                    f"deleted_at={db_record[2]}, "
                                    f"version={db_record[3]}"
                                )

                                # 检查数据库记录是否标记为已删除
                                if db_record[2]:  # deleted_at为True
                                    logger.info("数据库验证: 记录已被正确标记为删除")
                                else:
                                    logger.warning("数据库验证: 记录未被标记为删除")
                            else:
                                logger.warning("数据库验证: 无法找到记录")

                            # 检查仓储API是否正确过滤了软删除的记录
                            if deleted_user is None:
                                logger.info("仓储验证成功: 软删除的用户被正确过滤")
                            else:
                                logger.warning(
                                    f"仓储验证失败: 软删除的用户仍然可见，当前状态={deleted_user}"
                                )

                    except Exception as e:
                        logger.error(f"软删除测试失败: {e}", exc_info=True)
                        raise

                except Exception as e:
                    logger.error(f"更新用户失败: {e}", exc_info=True)
                    raise

    except Exception as e:
        logger.error(f"修改操作演示失败: {e}", exc_info=True)
        raise


async def run_example():
    """运行完整示例"""
    db = None

    try:
        # 数据库配置
        config = DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            connection=ConnectionConfig(
                host="192.168.8.195",
                port=5432,
                database="mydb",
                application_name="repository_example"
            ),
            credentials=CredentialsConfig(
                username="postgres",
                password="thends",
            ),
            pool=PoolConfig(
                min_size=5,
                max_size=20,
                pre_ping=True
            ),
            read_write=ReadWriteConfig(
                enable_read_write_split=False
            )
        )

        # 初始化数据库
        logger.info("初始化数据库...")
        await initialize_database(config)
        db = get_database()

        # 确保表的时间戳列使用带时区类型
        if hasattr(db, 'ensure_timezone_columns'):
            logger.info("检查并确保时间戳列使用带时区类型...")
            result = await db.ensure_timezone_columns()
            if "error" in result:
                logger.warning(f"检查时间戳列时出错: {result['error']}")
            else:
                logger.info(f"已检查 {len(result['checked'])} 个表")
                if result['modified']:
                    logger.info(
                        f"已修改 {len(result['modified'])} 个列: {', '.join(result['modified'])}")
                else:
                    logger.info("所有时间戳列已经使用带时区类型")

        # 确保用户仓储表准备就绪
        logger.info("=== 阶段1: 准备数据库表 ===")
        await create_tables(db)

        # 阶段2: 数据操作
        logger.info("=== 阶段2: 数据操作 ===")

        # 使用会话管理事务
        async with db.session() as session:
            try:
                # 显式开始事务
                await session.begin()

                # 创建及初始化仓储
                logger.info("初始化仓储...")
                # 创建版本变更日志拦截器
                version_logger = VersionChangeLogger()

                # 创建仓储并添加自定义拦截器
                user_repo = UserRepositoryImpl(
                    session=session,
                    actor="test_script",
                    custom_interceptors=[version_logger]
                )
                query_repo = UserQueryRepository(
                    session=session,
                    actor="test_script"
                )

                # 检查仓储元数据表映射是否正确
                target_table = UserPO.__tablename__
                logger.info(f"仓储使用表: {target_table}")

                # 填充测试数据
                logger.info("填充测试数据...")
                created_users = await populate_test_data(user_repo, session)
                logger.info(f"已创建 {len(created_users)} 个测试用户")

                if not created_users:
                    raise Exception("未能创建测试用户")

                # 提交数据变更
                await session.commit()
                logger.info("用户创建已提交")

                # 开始新事务进行查询演示
                await session.begin()

                # 演示查询操作
                logger.info("执行查询演示...")
                await demonstrate_queries(query_repo, created_users)

                # 提交查询事务
                await session.commit()

                # 开始新事务进行修改演示
                await session.begin()

                # 演示修改操作
                logger.info("执行修改演示...")
                await demonstrate_modifications(user_repo, query_repo)

                # 提交修改事务
                await session.commit()

                # 批量更新示例
                # logger.info("执行批量更新示例...")
                # await session.begin()
                # await user_repo.batch_update_users()
                # await session.commit()
                # logger.info("所有操作已完成并提交")

            except Exception as e:
                logger.error(f"执行示例时出错: {e}", exc_info=True)
                await session.rollback()
                raise

    except Exception as e:
        logger.error(f"运行示例时出错: {e}", exc_info=True)
        raise

    finally:
        if db:
            logger.info("清理数据库...")
            await cleanup_database()
            logger.info("数据库清理完成")


if __name__ == "__main__":
    asyncio.run(run_example())
