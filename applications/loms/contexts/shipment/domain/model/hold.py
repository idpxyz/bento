"""Shipment Hold entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bento.core.ids import ID


@dataclass
class Hold:
    """Shipment hold - a temporary block on shipment processing."""

    id: ID
    shipment_id: ID
    hold_type_code: str
    reason: str | None
    placed_at: datetime
    placed_by: str | None = None
    released_at: datetime | None = None
    released_by: str | None = None
    release_reason: str | None = None

    @property
    def is_active(self) -> bool:
        return self.released_at is None
