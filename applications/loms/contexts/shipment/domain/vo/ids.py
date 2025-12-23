from dataclasses import dataclass

@dataclass(frozen=True)
class TenantId:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) > 64:
            raise ValueError("invalid tenant_id")

@dataclass(frozen=True)
class ShipmentId:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) > 64:
            raise ValueError("invalid shipment_id")
