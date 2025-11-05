# idp/infrastructure/persistence/sqlalchemy/repo_adapter.py
from __future__ import annotations

import logging
from typing import Any, Dict, Generic, List, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.domain.base.entity import BaseAggregateRoot
from idp.framework.domain.repository.base import RepositoryProtocol
from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.mapper import MapperExceptionCode
from idp.framework.infrastructure.mapper import POMapper
from idp.framework.infrastructure.persistence.specification.core.base import (
    Specification,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    Page,
    PageParams,
)
from idp.framework.infrastructure.persistence.sqlalchemy.po.base import BasePO
from idp.framework.infrastructure.persistence.sqlalchemy.repository.base import (
    BaseRepository,
)

PO = TypeVar("PO", bound=BasePO)
AR = TypeVar("AR", bound=BaseAggregateRoot)
ID = TypeVar("ID")


class BaseAdapter(Generic[AR, PO, ID], RepositoryProtocol[AR, ID]):
    """
    通用适配器 - 使用 Framework Mapper 架构：
    * 使用 Framework 的 POMapper 进行对象映射
    * 类型安全的映射器接口
    * 更清晰的依赖注入
    * 更好的错误处理
    * 保持完整的仓储功能
    * 性能优化：高效转换，错误处理
    """

    def __init__(self, session: AsyncSession, po_cls: type[PO], mapper: POMapper[AR, PO]) -> None:
        self._delegate = BaseRepository(session, po_cls)
        self.session = session
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 使用 Framework 的 POMapper
        self._mapper = mapper

    def _safe_convert_to_domain(self, po: PO | None) -> AR | None:
        """安全转换PO到AR"""
        if po is None:
            return None
        try:
            return self._mapper.to_domain(po)
        except Exception as e:
            self.logger.error(f"Failed to convert PO to AR: {e}")
            raise InfrastructureException(
                code=MapperExceptionCode.MAPPER_TYPE_CONVERSION_FAILED,
                details={"message": f"Failed to convert PO to AR: {e}",
                         "source_type": type(po).__name__, "target_type": "AR"},
                cause=e
            )

    def _safe_convert_from_domain(self, ar: AR) -> PO:
        """安全转换AR到PO"""
        try:
            return self._mapper.to_po(ar)
        except Exception as e:
            self.logger.error(f"Failed to convert AR to PO: {e}")
            raise InfrastructureException(
                code=MapperExceptionCode.MAPPER_TYPE_CONVERSION_FAILED,
                details={"message": f"Failed to convert AR to PO: {e}",
                         "source_type": type(ar).__name__, "target_type": "PO"},
                cause=e
            )

    def _batch_convert_to_domain(self, pos: List[PO]) -> List[AR]:
        """批量转换PO列表到AR列表 - 性能优化版本"""
        if not pos:
            return []
        try:
            # 使用 Framework Mapper 的批量转换方法
            return self._mapper.to_domains(pos)
        except Exception as e:
            self.logger.error(f"Failed to batch convert PO to AR: {e}")
            raise InfrastructureException(
                code=MapperExceptionCode.MAPPER_BATCH_PROCESSING_FAILED,
                details={"message": f"Failed to batch convert PO to AR: {e}",
                         "source_type": f"List[{type(pos[0]).__name__ if pos else 'PO'}]", "target_type": "List[AR]"},
                cause=e
            )

    def _batch_convert_from_domain(self, ars: List[AR]) -> List[PO]:
        """批量转换AR列表到PO列表 - 性能优化版本"""
        if not ars:
            return []
        try:
            # 使用 Framework Mapper 的批量转换方法
            return self._mapper.to_pos(ars)
        except Exception as e:
            self.logger.error(f"Failed to batch convert AR to PO: {e}")
            raise InfrastructureException(
                code=MapperExceptionCode.MAPPER_BATCH_PROCESSING_FAILED,
                details={"message": f"Failed to batch convert AR to PO: {e}",
                         "source_type": f"List[{type(ars[0]).__name__ if ars else 'AR'}]", "target_type": "List[PO]"},
                cause=e
            )

    # ---- RepositoryProtocol implementation ----

    async def create(self, aggregate: AR) -> None:
        try:
            po = self._safe_convert_from_domain(aggregate)
            await self._delegate.create_po(po)
        except Exception as e:
            self.logger.error(f"Failed to create entity: {e}")
            raise

    async def update(self, aggregate: AR) -> None:
        try:
            po = self._safe_convert_from_domain(aggregate)
            await self._delegate.update_po(po)
        except Exception as e:
            self.logger.error(f"Failed to update entity: {e}")
            raise

    async def delete(self, aggregate: AR) -> None:
        try:
            po = self._safe_convert_from_domain(aggregate)
            await self._delegate.delete_po(po)
        except Exception as e:
            self.logger.error(f"Failed to delete entity: {e}")
            raise

    async def batch_create(self, aggregates: List[AR]) -> None:
        try:
            pos = self._batch_convert_from_domain(aggregates)
            await self._delegate.batch_po_create(pos)
        except Exception as e:
            self.logger.error(f"Failed to batch create entities: {e}")
            raise

    async def batch_update(self, where_clause: Any, values: Dict[str, Any]) -> int:
        try:
            return await self._delegate.batch_po_update(where_clause, values)
        except Exception as e:
            self.logger.error(f"Failed to batch update entities: {e}")
            raise

    async def batch_delete(self, aggregates: List[AR]) -> None:
        try:
            pos = self._batch_convert_from_domain(aggregates)
            await self._delegate.batch_po_delete(pos)
        except Exception as e:
            self.logger.error(f"Failed to batch delete entities: {e}")
            raise

    async def get_by_id(self, id: ID) -> Optional[AR]:
        """按主键加载聚合根，委托给底层的 get_po_by_id 以获得最佳性能"""
        try:
            po = await self._delegate.get_po_by_id(id)
            return self._safe_convert_to_domain(po)
        except Exception as e:
            self.logger.error(f"Failed to get entity by id {id}: {e}")
            raise

    async def query_by_spec(self, spec: Specification[AR]) -> List[AR]:
        try:
            po_spec = spec.with_type(PO)
            pos = await self._delegate.query_po_by_spec(po_spec)
            return self._batch_convert_to_domain(pos)
        except Exception as e:
            self.logger.error(f"Failed to query by spec: {e}")
            raise

    async def query_one_by_spec(self, spec: Specification[AR]) -> Optional[AR]:
        """使用规范查询单个实体"""
        try:
            po_spec = spec.with_type(PO)
            po = await self._delegate.query_one_po_by_spec(po_spec)
            return self._safe_convert_to_domain(po)
        except Exception as e:
            self.logger.error(f"Failed to find one by spec: {e}")
            raise

    async def query_all_by_spec(self, spec: Specification[AR]) -> List[AR]:
        """使用规范查询所有实体"""
        try:
            po_spec = spec.with_type(PO)
            pos = await self._delegate.query_all_po_by_spec(po_spec)
            return self._batch_convert_to_domain(pos)
        except Exception as e:
            self.logger.error(f"Failed to find all by spec: {e}")
            raise

    async def query_page_by_spec(
        self,
        spec: Specification[AR],
        page_params: 'PageParams',
        order_by: Optional[List[Any]] = None,
        projection: Optional[List[Any]] = None
    ) -> Page[AR]:
        """分页查询（新版，使用 PageParams）"""
        try:
            po_spec = spec.with_type(PO)
            page_po = await self._delegate.query_po_page_by_spec(
                spec=po_spec, page_params=page_params, order_by=order_by, projection=projection
            )
            converted_items = self._batch_convert_to_domain(page_po.items)
            return Page.create(
                items=converted_items,
                total=page_po.total,
                page=page_po.page,
                size=page_po.size,
            )
        except Exception as e:
            self.logger.error(f"Failed to find page by spec: {e}")
            raise

    async def query_count_by_spec(self, spec: Specification[AR]) -> int:
        """使用规范统计实体数量"""
        try:
            po_spec = spec.with_type(PO)
            return await self._delegate.query_count_po_by_spec(po_spec)
        except Exception as e:
            self.logger.error(f"Failed to count by spec: {e}")
            raise

    async def query_exists_by_spec(self, spec: Specification[AR]) -> bool:
        try:
            po_spec = spec.with_type(PO)
            return await self._delegate.query_exists_po_by_spec(po_spec)
        except Exception as e:
            self.logger.error(f"Failed to check entity existence by spec: {e}")
            raise
