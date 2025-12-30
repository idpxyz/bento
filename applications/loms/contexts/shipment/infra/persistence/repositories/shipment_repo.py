"""Shipment Repository using Bento's RepositoryAdapter."""

from loms.contexts.shipment.domain.model.shipment import Shipment
from loms.contexts.shipment.infra.persistence.mappers.shipment_mapper import (
    ShipmentMapper,
)
from loms.contexts.shipment.infra.persistence.models import ShipmentORM
from sqlalchemy.ext.asyncio import AsyncSession

from bento.core.ids import ID
from bento.infrastructure.repository import RepositoryAdapter, repository_for
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository import BaseRepository


@repository_for(Shipment)
class ShipmentRepository(RepositoryAdapter[Shipment, ShipmentORM, ID]):
    """Shipment Repository using Bento's RepositoryAdapter.

    Provides:
    - AR <-> PO mapping via ShipmentMapper
    - TenantFilterMixin for multi-tenant queries
    - Specification pattern support
    - Pagination support
    """

    # Enable multi-tenant filtering
    tenant_enabled = True

    def __init__(self, session: AsyncSession):
        base_repo: BaseRepository[ShipmentORM, ID] = BaseRepository(
            session=session,
            po_type=ShipmentORM,
            actor="system",
            interceptor_chain=create_default_chain("system"),
        )
        mapper = ShipmentMapper()
        super().__init__(repository=base_repo, mapper=mapper)

    # Note: get(), save(), find_all(), etc. now automatically support
    # multi-tenant filtering via RepositoryAdapter base class when
    # tenant_enabled = True


# Backwards compatibility alias
ShipmentRepositoryImpl = ShipmentRepository
