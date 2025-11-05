"""SQLAlchemy仓储基类（科学排序版）

提供基础设施层的仓储实现，专注于PO（持久化对象）操作。
不继承领域抽象接口，保持关注点分离。
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypedDict, TypeVar
from typing import cast as type_cast
from typing import get_args, get_origin

from infrastructure.persistence.specification.core.base import Specification
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.infrastructure.persistence.specification import Page, PageParams
from idp.framework.infrastructure.persistence.specification.core.type import (
    Statistic,
    StatisticalFunction,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.base import (
    BatchInterceptorChain,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import (
    OperationType,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import (
    InterceptorContext,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.factory import (
    InterceptorConfig,
    InterceptorFactory,
)
from idp.framework.infrastructure.persistence.sqlalchemy.po.base import BasePO
from idp.framework.infrastructure.persistence.sqlalchemy.repository.delegate import (
    RepositoryDelegate,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.audit import (
    fill_audit_fields,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.diff import (
    has_entity_changed,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
    FieldResolver,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.json_spec_parser import (
    JsonSpecParser,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.query_builder import (
    QueryBuilder,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.soft_delete import (
    mark_soft_deleted,
)

PO = TypeVar("PO", bound=BasePO)
ID = TypeVar("ID", bound=str)


class ContextData(TypedDict, total=False):
    soft_deleted: bool
    version: int
    audit_info: Dict[str, Any]
    cache_key: str
    cache_ttl: int
    skip_interceptors: List[str]
    custom_data: Dict[str, Any]


class BaseRepository(Generic[PO, ID], RepositoryDelegate[PO, ID]):
    """
    SQLAlchemy仓储基类
    提供基础设施层的仓储实现，专注于PO（持久化对象）操作。
    不继承领域抽象接口，保持关注点分离。
    """

    # 1. 构造方法与属性相关
    def __init__(
        self,
        session: AsyncSession,
        model_class: Optional[Type[PO]] = None,
        actor: str = "system",
        enable_cache: bool = True,
        enable_optimistic_lock: bool = True,
        enable_audit: bool = True,
        enable_soft_delete: bool = True,
        enable_logging: bool = False,
        enable_sql_logging: bool = False,
        custom_interceptors: Optional[List[Any]] = None,
        context_data: Optional[ContextData] = None,
    ):
        if not session:
            raise ValueError("Database session is required")
        self.session = session
        self.actor = actor
        self.context_data = context_data or {}
        self.enable_logging = enable_logging
        self.enable_sql_logging = enable_sql_logging
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if model_class:
            self._entity_type = model_class
        else:
            self._entity_type = self._resolve_entity_type()
        config = InterceptorConfig(
            session=session,
            actor=actor,
            enable_cache=enable_cache,
            enable_optimistic_lock=enable_optimistic_lock,
            enable_audit=enable_audit,
            enable_soft_delete=enable_soft_delete,
            enable_logging=enable_logging,
            custom_interceptors=custom_interceptors or [],
            context_data=self.context_data
        )
        self.interceptor_chain = InterceptorFactory.create_chain(config)
        batch_config = InterceptorConfig(
            session=session,
            actor=actor,
            enable_cache=enable_cache,
            enable_optimistic_lock=False,
            enable_audit=enable_audit,
            enable_soft_delete=enable_soft_delete,
            enable_logging=enable_logging,
            custom_interceptors=custom_interceptors or [],
            context_data=self.context_data
        )
        self.batch_interceptor_chain = type_cast(
            BatchInterceptorChain[PO],
            InterceptorFactory.create_chain(batch_config)
        )
        self.field_resolver = FieldResolver(self.entity_type)
        self.query_builder = QueryBuilder(self.entity_type)
        self.spec_parser = JsonSpecParser(self.entity_type)
        self._query_builder_pool = []
        self._count_builder_pool = []
        self._pool_size = 5

    @property
    def entity_type(self) -> Type[PO]:
        return self._entity_type

    def _resolve_entity_type(self) -> Type[PO]:
        orig = getattr(self, "__orig_class__", None)
        if orig is not None:
            return get_args(orig)[0]
        for base in getattr(self.__class__, "__orig_bases__", []):
            if get_origin(base) is BaseRepository:
                return get_args(base)[0]
        raise RuntimeError(
            "Cannot resolve entity_type automatically. "
            "Consider passing model_class explicitly in constructor."
        )

    def _get_query_builder_from_pool(self):
        if self._query_builder_pool:
            return self._query_builder_pool.pop()
        return self.query_builder.build_query()

    def _return_query_builder_to_pool(self, builder):
        if len(self._query_builder_pool) < self._pool_size:
            builder.reset()
            self._query_builder_pool.append(builder)

    def _get_count_builder_from_pool(self):
        if self._count_builder_pool:
            return self._count_builder_pool.pop()
        return self.query_builder.build_count_query()

    def _return_count_builder_to_pool(self, builder):
        if len(self._count_builder_pool) < self._pool_size:
            builder.reset()
            self._count_builder_pool.append(builder)

    async def get_po_by_id(self, id: ID) -> Optional[PO]:
        """按主键获取 PO，利用 session.get() 实现最高性能的查询"""
        try:
            return await self.session.get(self.entity_type, id)
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to get PO by id {id}: {e}")
            raise

    # 2. 核心查询方法
    async def query_po_by_spec(self, spec: Specification[PO]) -> List[PO]:
        try:
            params = spec.to_query_params()
            if self.enable_logging:
                self.logger.debug(f'[query_by_spec] params: {params}')
            is_count_query = any(stat.function == StatisticalFunction.COUNT for stat in (
                params.get('statistics') or []))
            if is_count_query:
                count_builder = self._get_count_builder_from_pool()
                try:
                    if params.get('filters'):
                        count_builder.apply_filters(
                            params['filters'], self.field_resolver.resolve)
                    if params.get('groups'):
                        count_builder.apply_groups(
                            params['groups'], self.field_resolver.resolve)
                    stmt = count_builder.build(params.get(
                        'joins'), params.get('statistics'))
                finally:
                    self._return_count_builder_to_pool(count_builder)
            else:
                query_builder = self._get_query_builder_from_pool()
                try:
                    stmt = (
                        query_builder
                        .apply_filters(params.get('filters'), self.field_resolver.resolve)
                        .apply_groups(params.get('groups'), self.field_resolver.resolve)
                        .apply_sorts(params.get('sorts'), self.field_resolver.resolve)
                        .apply_joins(params.get('joins'))
                        .apply_pagination(params.get('page'))
                        .apply_field_selection(params.get('fields'), self.field_resolver.resolve)
                        .apply_eager_loading(params.get('includes'))
                        .apply_grouping(params.get('group_by'), self.field_resolver.resolve)
                        .apply_having(params.get('having'), self.field_resolver.resolve)
                        .apply_statistics(params.get('statistics'), self.field_resolver.resolve)
                        .build()
                    )
                finally:
                    self._return_query_builder_to_pool(query_builder)
            if self.enable_sql_logging:
                self.logger.debug(
                    f'[query_by_spec] SQL: {str(stmt.compile(compile_kwargs={"literal_binds": True}))}')
            result = await self.session.execute(stmt)
            if is_count_query:
                count_result = result.scalar()
                return [count_result] if count_result is not None else [0]
            else:
                return result.unique().scalars().all()
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to query by spec: {e}")
            raise

    # 3. 便捷查询方法
    async def query_one_po_by_spec(self, spec: Specification[PO]) -> Optional[PO]:
        spec.page = Page.create(items=[], total=0, page=1, size=1)
        results = await self.query_po_by_spec(spec)
        return results[0] if results else None

    async def query_all_po_by_spec(self, spec: Specification[PO]) -> List[PO]:
        spec.page = None
        return await self.query_po_by_spec(spec)

    async def query_po_page_by_spec(
        self,
        spec: Specification[PO],
        page_params: PageParams,
        order_by: Optional[List[Any]] = None,
        projection: Optional[List[Any]] = None,
    ) -> Page[PO]:
        query_spec = copy.deepcopy(spec)
        if order_by:
            query_spec.sorts = order_by
        if projection:
            query_spec.fields = projection

        count_spec = self._build_count_spec(spec)
        total_results = await self.query_po_by_spec(count_spec)
        total = self._extract_count(total_results)

        if total == 0:
            return Page.create(items=[], total=0, page=1, size=page_params.size)

        query_spec.page = Page.create(
            items=[], total=0, page=page_params.page, size=page_params.size)
        items = await self.query_po_by_spec(query_spec)

        return Page.create(
            items=items,
            total=total,
            page=page_params.page,
            size=page_params.size
        )

    async def query_count_po_by_spec(self, spec: Specification[PO]) -> int:
        count_spec = self._build_count_spec(spec)
        results = await self.query_po_by_spec(count_spec)
        return self._extract_count(results)

    async def query_exists_po_by_spec(self, spec: Specification[PO]) -> bool:
        return await self.query_count_po_by_spec(spec) > 0

    # 4. 查询辅助方法

    def _build_count_spec(self, spec: Specification[PO]) -> Specification[PO]:
        count_spec = copy.deepcopy(spec)
        count_spec.page = None
        count_spec.fields = []
        count_spec.sorts = []
        count_spec.includes = []
        count_spec.group_by = []
        count_spec.having = []
        count_spec.statistics = [
            Statistic(field="id", function=StatisticalFunction.COUNT, distinct=True)]
        return count_spec

    def _extract_count(self, results: List[Any]) -> int:
        if not results:
            return 0
        count_value = results[0]
        if isinstance(count_value, (int, float)):
            return int(count_value)
        elif hasattr(count_value, 'count'):
            return count_value.count
        else:
            try:
                return int(count_value)
            except (TypeError, ValueError):
                return 0

    # 5. 写操作/批量操作方法
    async def create_po(self, entity: PO) -> PO:
        context = InterceptorContext(
            session=self.session,
            entity_type=self.entity_type,
            operation=OperationType.CREATE,
            entity=entity,
            actor=self.actor,
            context_data=self.context_data
        )

        async def operation(ctx: InterceptorContext[PO]) -> PO:
            return await self._do_create(ctx.entity)
        return await self.interceptor_chain.execute(context, operation)

    async def _do_create(self, entity: PO) -> PO:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update_po(self, entity: PO) -> PO:
        try:
            current = await self.session.get(self.entity_type, entity.id)
            if not current:
                raise ValueError("object not found")
            if not has_entity_changed(entity, current, self.entity_type.__mapper__):
                return current
            merged = await self.session.merge(entity)
            fill_audit_fields(merged, self.actor)
            await self.session.flush()
            return merged
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to update entity {entity.id}: {e}")
            raise

    async def delete_po(self, entity: PO) -> None:
        try:
            mark_soft_deleted(entity, self.actor)
            merged = await self.session.merge(entity)
            await self.session.flush()
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to delete entity {entity.id}: {e}")
            raise

    async def batch_po_create(self, entities: List[PO]) -> List[PO]:
        try:
            for entity in entities:
                fill_audit_fields(entity, self.actor)
                self.session.add(entity)
            await self.session.flush()
            return entities
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to batch create entities: {e}")
            raise

    async def batch_po_update(self, entities: List[PO]) -> List[PO]:
        try:
            for entity in entities:
                fill_audit_fields(entity, self.actor)
            mappings = [
                {c.name: getattr(entity, c.name)
                 for c in self.entity_type.__table__.columns}
                for entity in entities
            ]

            def sync_bulk_update(session):
                session.bulk_update_mappings(self.entity_type, mappings)
            await self.session.run_sync(sync_bulk_update)
            await self.session.flush()
            return entities
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to batch update entities: {e}")
            raise

    async def batch_po_delete(self, entities: List[PO]) -> None:
        try:
            for entity in entities:
                mark_soft_deleted(entity, self.actor)
                self.session.add(entity)
            await self.session.flush()
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to batch delete entities: {e}")
            raise
