from dataclasses import dataclass

@dataclass(frozen=True)
class HoldTypeCode:
    value: str
    def __post_init__(self):
        if not self.value or len(self.value) > 64:
            raise ValueError("invalid hold_type_code")

@dataclass(frozen=True)
class ShipmentStatus:
    value: str
