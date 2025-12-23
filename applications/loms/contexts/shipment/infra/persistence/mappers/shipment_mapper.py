from loms.contexts.shipment.domain.model.shipment import Shipment
from loms.contexts.shipment.domain.vo.ids import TenantId, ShipmentId
from loms.contexts.shipment.domain.vo.codes import ShipmentStatus
from loms.contexts.shipment.infra.persistence.models import ShipmentORM

class ShipmentMapper:
    @staticmethod
    def to_domain(o: ShipmentORM) -> Shipment:
        return Shipment(
            tenant_id=TenantId(o.tenant_id),
            shipment_id=ShipmentId(o.id),
            shipment_code=o.shipment_code,
            status=ShipmentStatus(o.status_code),
            version=o.version,
        )

    @staticmethod
    def from_domain(d: Shipment) -> ShipmentORM:
        return ShipmentORM(
            id=d.shipment_id.value,
            tenant_id=d.tenant_id.value,
            shipment_code=d.shipment_code,
            status_code=d.status.value,
            version=d.version,
        )
