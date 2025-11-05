"""Domain‑event foundation with **schema registry integration**

Additions compared to v2
========================
* **`schema_id`** – points to external Schema Registry record; filled by
  Outbox interceptor or upstream service.  Keeps payload lean while enabling
  strong typing downstream.
* Hash / immutability logic unchanged – `schema_id` participates in canonical
  JSON if present.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ----------------------------- helpers -----------------------------
def _serialize_uuid(v: UUID) -> str:
    return str(v)


def _serialize_datetime(v: datetime) -> str:
    return v.isoformat()


def _canonical_json(obj: Dict[str, Any]) -> str:
    """Stable JSON for hashing (remove None, sort keys)."""
    clean = {k: v for k, v in obj.items() if v is not None}
    return json.dumps(clean, separators=(",", ":"), sort_keys=True, default=str)

# -------------------------- base event -----------------------------


class DomainEvent(BaseModel):
    """Base class for all domain events (immutable & hash‑signed)."""

    # ---- mandatory ids ----
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    # ---- routing aids ----
    aggregate_id: UUID | None = None
    tenant_id: str | None = None

    # ---- schema registry ----
    schema_version: int = 1                    # in‑app semantic version
    schema_id: str | None = None               # external registry id

    # ---- integrity ----
    content_hash: str | None = None            # auto‑filled SHA‑256

    model_config = ConfigDict(frozen=True)

    # ------------------ validators ------------------
    @model_validator(mode="after")
    def _fill_hash(self) -> "DomainEvent":
        if self.content_hash:
            return self
        data = self.model_dump(exclude={"content_hash"}, by_alias=False)
        self.__dict__["content_hash"] = hashlib.sha256(
            _canonical_json(data).encode()).hexdigest()
        return self

    # ------------------ helpers ---------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} id={self.event_id} v={self.schema_version} sid={self.schema_id}>"

    def to_payload(self) -> Dict[str, Any]:
        """Dict ready for JSON / Outbox serialization."""
        data = self.model_dump()
        # 手动序列化 UUID 和 datetime
        if self.event_id:
            data["event_id"] = _serialize_uuid(self.event_id)
        if self.aggregate_id:
            data["aggregate_id"] = _serialize_uuid(self.aggregate_id)
        if self.occurred_at:
            data["occurred_at"] = _serialize_datetime(self.occurred_at)
        return data
