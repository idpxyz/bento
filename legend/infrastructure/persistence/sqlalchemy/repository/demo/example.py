"""仓储实现示例

演示如何实现和使用仓储。
"""

import asyncio
import copy
import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Union
from uuid import UUID

from exception.classified import InfrastructureException
from exception.code.repository import RepositoryErrorCode
from infrastructure.db.config.base import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
    DatabaseType,
    PoolConfig,
    ReadWriteConfig,
)
from infrastructure.db.database import cleanup_database, initialize_database
from infrastructure.persistence.specification.core.type import SortDirection
from infrastructure.persistence.sqlalchemy.repository.base import (
    BaseRepository,
    ContextData,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.domain.repository import PageParams, PaginatedResult
from idp.framework.infrastructure.persistence.specification.builder import (
    SpecificationBuilder,
)
from idp.framework.infrastructure.persistence.specification.core.base import (
    Specification,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import (
    InterceptorContext,
    OperationType,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.demo.domain import (
    User,
    UserId,
    UserRepository,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.demo.user_po import (
    UserPO,
)
from idp.framework.shared.utils.date_time import utc_now

logger = logging.getLogger(__name__)


class UserRepositoryImpl(BaseRepository[UserPO], UserRepository):
    """用户仓储实现

    将领域接口适配到基础设施实现。
    """
    model = UserPO

    def __init__(
        self,
        session: AsyncSession,
        actor: str = "system",
        custom_interceptors: Optional[List[Any]] = None,
        context_data: Optional[ContextData] = None,
    ):
        """初始化用户仓储

        Args:
            session: 数据库会话
            actor: 当前操作者
            custom_interceptors: 自定义拦截器列表
            context_data: 上下文数据
        """
        super().__init__(
            session=session,
            actor=actor,
            enable_cache=True,
            enable_optimistic_lock=True,
            enable_audit=True,
            enable_soft_delete=True,
            enable_logging=True,
            custom_interceptors=custom_interceptors,
            context_data=context_data
        )

    def _to_entity(self, po: UserPO) -> User:
        """将持久化对象转换为领域实体

        Args:
            po: 持久化对象

        Returns:
            领域实体

        Raises:
            ValueError: 当持久化对象无效时
        """
        if not po:
            raise ValueError("Persistent object cannot be None")

        try:
            return User(
                id=UUID(po.id) if po.id else None,
                username=po.username,
                email=po.email,
                full_name=po.full_name,
                is_active=po.is_active,
                is_admin=po.is_admin
            )
        except Exception as e:
            logger.error(f"Error converting PO to entity: {str(e)}")
            raise

    def _to_po(self, entity: User) -> UserPO:
        """将领域实体转换为持久化对象

        Args:
            entity: 领域实体

        Returns:
            持久化对象

        Raises:
            ValueError: 当领域实体无效时
        """
        if not entity:
            raise ValueError("Entity cannot be None")

        try:
            po = UserPO(
                id=str(entity.id) if entity.id else None,
                username=entity.username,
                email=entity.email,
                full_name=entity.full_name,
                is_active=entity.is_active,
                is_admin=entity.is_admin
            )
            return po
        except Exception as e:
            logger.error(f"Error converting entity to PO: {str(e)}")
            raise

    async def save(self, user: User) -> User:
        """保存用户

        Args:
            user: 用户领域实体

        Returns:
            保存后的用户领域实体

        Raises:
            InfrastructureException: 当发生乐观锁冲突或其他基础设施错误时
            ValueError: 当用户数据无效时
        """
        if not user:
            raise ValueError("User cannot be None")

        try:
            # 转换为持久化对象
            user_po = self._to_po(user)

            # 保存实体
            if not user_po.id:
                saved_po = await self.create(user_po)
            else:
                saved_po = await self.update(user_po)

            return self._to_entity(saved_po)

        except InfrastructureException as e:
            logger.error(
                f"Failed to save user due to infrastructure error: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Invalid user data: {str(e)}")
            raise
        except Exception as e:
            # 处理数据库唯一约束冲突
            if "already exists" in str(e).lower():
                raise ValueError(f"Username {user_po.username} already exists")
            logger.error(f"Unexpected error while saving user: {str(e)}")
            raise

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """根据ID查找用户

        Args:
            user_id: 用户ID

        Returns:
            用户领域实体或None
        """
        user_po = await self.get_by_id(str(user_id))
        return self._to_entity(user_po) if user_po else None

    async def find_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户

        Args:
            username: 用户名

        Returns:
            用户领域实体或None

        Raises:
            ValueError: 当用户名无效时
        """
        if not username:
            raise ValueError("Username cannot be empty")

        try:
            user_po = await self.find_one_by_json({
                "filters": [
                    {
                        "field": "username",
                        "operator": "EQUALS",
                        "value": username
                    },
                    {
                        "field": "deleted_at",
                        "operator": "IS_NULL",
                        "value": None
                    }
                ]
            })

            if not user_po:
                return None

            # 转换为领域实体
            return self._to_entity(user_po)

        except Exception as e:
            logger.error(
                f"Error finding user by username {username}: {str(e)}")
            raise

    async def delete(self, user: User) -> None:
        """删除用户

        Args:
            user: 要删除的用户实体
        """
        user_po = self._to_po(user)
        await super().delete(user_po)

    async def batch_update_users(self):
        """演示 UserPO 批量更新的用法"""
        # 1. 查询所有活跃用户
        json_spec = {
            "filters": [
                {"field": "is_active", "operator": "eq", "value": True},
                {"field": "deleted_at", "operator": "IS_NULL", "value": None}
            ]
        }
        users: list[UserPO] = await self.find_all_by_json(json_spec)
        logger.info(f"查询到 {len(users)} 个活跃用户")
        # 2. 批量修改属性
        for user in users:
            user.is_active = False
            user.full_name = (user.full_name or "") + " [批量更新]"

        # 3. 批量更新
        await self.batch_update(users)

        # 4. 验证批量更新结果
        updated_users = await self.find_all_by_json({
            "filters": [
                {"field": "is_active", "operator": "eq", "value": False},
                {"field": "deleted_at", "operator": "IS_NULL", "value": None}
            ]
        })
        print(f"批量更新后用户数: {len(updated_users)}")
        for u in updated_users:
            print(u)


class UserQueryRepository(BaseRepository[UserPO]):
    """用户查询仓储

    提供用户查询功能，包括高级查询和分页功能。
    遵循CQRS原则，专注于查询操作。
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        """初始化用户查询仓储

        Args:
            session: 数据库会话
            actor: 当前操作者
        """
        super().__init__(
            session=session,
            actor=actor,
            enable_cache=True,
            enable_optimistic_lock=False,
            enable_audit=False,
            enable_soft_delete=True,
            enable_logging=True
        )

    async def find_active_users(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[List[dict]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> PaginatedResult[UserPO]:
        """查找活跃用户

        Args:
            page: 页码
            page_size: 每页记录数
            filters: 额外的过滤条件
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            分页结果
        """
        # 创建 filters 的副本以避免修改原始对象
        filters = copy.deepcopy(filters) if filters is not None else []

        # 基础过滤条件 - 只添加一次
        base_filters = [
            {"field": "is_active", "operator": "eq", "value": True},
            {"field": "deleted_at", "operator": "IS_NULL", "value": None}
        ]

        # 合并过滤条件，确保不重复
        all_filters = base_filters + [
            f for f in filters
            if not any(
                bf["field"] == f["field"] and bf["operator"] == f["operator"]
                for bf in base_filters
            )
        ]

        json_spec = {
            "filters": all_filters,
            "sorts": [{"field": sort_by, "direction": sort_order.upper()}]
        }

        page_params = PageParams(page=page, page_size=page_size)
        return await self.find_page_by_json(json_spec, page_params)

    async def find_active_admins(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> PaginatedResult[UserPO]:
        """查找活跃管理员用户

        Args:
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            分页结果
        """
        # 构建基础过滤条件
        base_filters = [
            {"field": "is_active", "operator": "eq", "value": True},
            {"field": "deleted_at", "operator": "IS_NULL", "value": None},
            {"field": "is_admin", "operator": "eq", "value": True}
        ]

        json_spec = {
            "filters": base_filters,
            "sorts": [{"field": sort_by, "direction": sort_order.upper()}]
        }

        page_params = PageParams(page=page, page_size=page_size)
        return await self.find_page_by_json(json_spec, page_params)

    async def find_recent_users(
        self,
        days: int = 30,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> PaginatedResult[UserPO]:
        """查找最近注册的用户

        Args:
            days: 最近天数
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            分页结果
        """
        cutoff_date = utc_now() - timedelta(days=days)
        filters = [
            {
                "field": "created_at",
                "operator": ">=",
                "value": cutoff_date
            }
        ]
        return await self.find_active_users(page, page_size, filters, sort_by, sort_order)

    async def find_by_email_domain(
        self,
        domain: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[List[dict]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> PaginatedResult[UserPO]:
        """查找指定邮箱域名的用户

        Args:
            domain: 邮箱域名
            page: 页码
            page_size: 每页记录数
            filters: 额外的过滤条件
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            分页结果
        """
        # 创建 filters 的副本以避免修改原始对象
        filters = copy.deepcopy(filters) if filters is not None else []

        domain_filter = {
            "field": "email",
            "operator": "LIKE",
            "value": f'%@{domain}'
        }

        # 使用 find_active_users 方法，它会正确处理基础过滤条件
        return await self.find_active_users(
            page=page,
            page_size=page_size,
            filters=[domain_filter] + filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def search_users(
        self,
        search_term: Optional[str] = None,
        status_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> PaginatedResult[UserPO]:
        """综合搜索用户

        Args:
            search_term: 搜索关键词
            status_filter: 状态过滤 (active/inactive)
            role_filter: 角色过滤 (admin/regular)
            from_date: 开始日期
            to_date: 结束日期
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            分页结果
        """
        # 创建基础过滤条件
        filters = [{"field": "deleted_at",
                    "operator": "IS_NULL", "value": None}]
        groups = []

        # 搜索条件
        if search_term:
            groups.append({
                "operator": "OR",
                "filters": [
                    {"field": "username", "operator": "contains",
                        "value": search_term},
                    {"field": "email", "operator": "contains", "value": search_term},
                    {"field": "full_name", "operator": "contains", "value": search_term}
                ]
            })

        # 状态过滤
        if status_filter == "active":
            filters.append(
                {"field": "is_active", "operator": "eq", "value": True})
        elif status_filter == "inactive":
            filters.append(
                {"field": "is_active", "operator": "eq", "value": False})

        # 角色过滤
        if role_filter == "admin":
            filters.append(
                {"field": "is_admin", "operator": "eq", "value": True})
        elif role_filter == "regular":
            filters.append(
                {"field": "is_admin", "operator": "eq", "value": False})

        # 日期范围过滤
        if from_date:
            filters.append(
                {"field": "created_at", "operator": ">=", "value": from_date})
        if to_date:
            filters.append(
                {"field": "created_at", "operator": "<=", "value": to_date})

        json_spec = {
            "filters": filters,
            "groups": groups,
            "sorts": [{"field": sort_by, "direction": sort_order.upper()}]
        }

        page_params = PageParams(page=page, page_size=page_size)
        return await self.find_page_by_json(json_spec, page_params)


# 使用示例
async def example_usage(session: AsyncSession):
    """演示仓储的使用

    Args:
        session: 数据库会话
    """
    # 创建查询仓储
    query_repo = UserQueryRepository(session)

    # 使用内置的查询方法
    active_users = await query_repo.find_active_users(page=1, page_size=10)
    active_admins = await query_repo.find_active_admins(page=1, page_size=10)
    recent_users = await query_repo.find_recent_users(days=30, page=1, page_size=10)
    gmail_users = await query_repo.find_by_email_domain("gmail.com", page=1, page_size=10)

    # 使用综合搜索
    search_results = await query_repo.search_users(
        search_term="john",
        status_filter="active",
        role_filter="admin",
        from_date="2023-01-01",
        sort_by="username",
        sort_order="asc",
        page=1,
        page_size=20
    )

    # 创建写入仓储
    user_repo = UserRepositoryImpl(session)

    # 创建用户
    new_user = User(
        id=None,
        username="johndoe",
        email="johndoe@example.com",
        full_name="John Doe",
        is_active=True,
        is_admin=False,
    )

    # 保存新用户
    created_user = await user_repo.save(new_user)
    print(f"Created user: {created_user}")

    # 查找用户
    user_by_id = await user_repo.find_by_id(created_user.id)
    user_by_username = await user_repo.find_by_username("johndoe")

    # 提升用户为管理员
    if user_by_username:
        user_by_username.promote_to_admin()
        promoted_user = await user_repo.save(user_by_username)
        print(f"Promoted user to admin: {promoted_user}")

    # 更新用户
    if user_by_id:
        updated_user = User(
            id=user_by_id.id,
            username="new.user",
            email="updated.email@example.com",
            full_name="Updated User Name",
            is_active=True,
            is_admin=False,
            updated_at=None,
        )
        saved_user = await user_repo.save(updated_user)
        print(f"Updated user: {saved_user}")

    # 删除用户
    if user_by_username:
        await user_repo.delete(user_by_username)
        print(f"Deleted user: {user_by_username}")

    return {
        "active_users": active_users,
        "active_admins": active_admins,
        "recent_users": recent_users,
        "gmail_users": gmail_users,
        "search_results": search_results
    }


async def main():
    config = DatabaseConfig(
        type=DatabaseType.POSTGRESQL,
        connection=ConnectionConfig(
            host="192.168.8.137",
            port=5438,
            database="idp",
            application_name="database_example"
        ),
        credentials=CredentialsConfig(
            username="topsx",
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

    try:
        # Initialize database
        print("Initializing database...")
        db = await initialize_database(config)
        print("Database initialized successfully.")
        # session = db.session()
        # asyncio.run(example_usage(session))
    finally:
        print("Cleaning up database...")
        await cleanup_database()
        print("Database cleaned up successfully.")

if __name__ == "__main__":
    asyncio.run(main())
