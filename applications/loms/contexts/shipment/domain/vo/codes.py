from dataclasses import dataclass
from enum import Enum


class ShipmentStatusEnum(str, Enum):
    """Shipment status values from state machine."""

    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    ON_HOLD = "ON_HOLD"
    DELIVERED = "DELIVERED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = {ShipmentStatusEnum.CLOSED, ShipmentStatusEnum.CANCELLED}


@dataclass(frozen=True)
class ShipmentStatus:
    """Shipment status value object."""

    value: str

    def __post_init__(self) -> None:
        # Validate against enum
        if self.value not in [s.value for s in ShipmentStatusEnum]:
            raise ValueError(f"Invalid status: {self.value}")

    @property
    def is_terminal(self) -> bool:
        return self.value in {s.value for s in TERMINAL_STATES}

    @property
    def can_place_hold(self) -> bool:
        return self.value in {
            ShipmentStatusEnum.DRAFT.value,
            ShipmentStatusEnum.PLANNED.value,
            ShipmentStatusEnum.IN_TRANSIT.value,
        }

    @property
    def can_release_hold(self) -> bool:
        return self.value == ShipmentStatusEnum.ON_HOLD.value

    @property
    def can_close(self) -> bool:
        return self.value in {
            ShipmentStatusEnum.PLANNED.value,
            ShipmentStatusEnum.IN_TRANSIT.value,
            ShipmentStatusEnum.DELIVERED.value,
        }

    @property
    def can_cancel(self) -> bool:
        return self.value in {
            ShipmentStatusEnum.DRAFT.value,
            ShipmentStatusEnum.PLANNED.value,
        }

    @property
    def can_add_leg(self) -> bool:
        return self.value == ShipmentStatusEnum.DRAFT.value


@dataclass(frozen=True)
class HoldTypeCode:
    """Hold type code value object."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 64:
            raise ValueError("invalid hold_type_code")


@dataclass(frozen=True)
class ModeCode:
    """Transport mode code (AIR, SEA, ROAD, RAIL)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 32:
            raise ValueError("invalid mode_code")


@dataclass(frozen=True)
class ServiceLevelCode:
    """Service level code (EXPRESS, STANDARD, ECONOMY)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 32:
            raise ValueError("invalid service_level_code")


@dataclass(frozen=True)
class ShipmentTypeCode:
    """Shipment type code (INBOUND, OUTBOUND, TRANSFER)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 32:
            raise ValueError("invalid shipment_type_code")
