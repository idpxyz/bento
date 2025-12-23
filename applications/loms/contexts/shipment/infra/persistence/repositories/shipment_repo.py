from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loms.contexts.shipment.domain.vo.ids import TenantId, ShipmentId
from loms.contexts.shipment.domain.model.shipment import Shipment
from loms.contexts.shipment.infra.persistence.mappers.shipment_mapper import ShipmentMapper, ShipmentORM

class ShipmentRepositoryImpl:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, tenant_id: TenantId, shipment_id: ShipmentId) -> Shipment | None:
        stmt = select(ShipmentORM).where(
            ShipmentORM.tenant_id == tenant_id.value,
            ShipmentORM.id == shipment_id.value,
        )
        row = (await self.session.execute(stmt)).scalars().first()
        return ShipmentMapper.to_domain(row) if row else None

    async def save(self, shipment: Shipment) -> None:
        # upsert-like behavior
        existing = await self.session.get(ShipmentORM, shipment.shipment_id.value)
        if existing and existing.tenant_id == shipment.tenant_id.value:
            existing.shipment_code = shipment.shipment_code
            existing.status_code = shipment.status.value
            existing.version = shipment.version
        else:
            self.session.add(ShipmentMapper.from_domain(shipment))
