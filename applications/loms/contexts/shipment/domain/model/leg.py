"""Shipment Leg entity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bento.core.ids import ID


@dataclass
class Leg:
    """Shipment leg - a segment of the shipment journey."""

    id: ID
    shipment_id: ID
    leg_index: int
    origin_node_id: str
    destination_node_id: str
    planned_departure: datetime | None = None
    planned_arrival: datetime | None = None
    actual_departure: datetime | None = None
    actual_arrival: datetime | None = None
    carrier_code: str | None = None
    mode_code: str | None = None

    @property
    def is_departed(self) -> bool:
        return self.actual_departure is not None

    @property
    def is_arrived(self) -> bool:
        return self.actual_arrival is not None
