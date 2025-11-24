from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from bento.domain.domain_event import DomainEvent
from bento.persistence.outbox.record import OutboxRecord


@dataclass(frozen=True, kw_only=True)
class MyEvent(DomainEvent):
    u: str
    when: datetime
    price: Decimal
    nested: dict


def test_outboxrecord_from_domain_event_serialization():
    evt = MyEvent(
        u=str(uuid4()),
        when=datetime(2024, 1, 2, 3, 4, 5),
        price=Decimal("12.34"),
        nested={
            "id": uuid4(),
            "ts": datetime(2024, 5, 6, 7, 8, 9),
            "arr": [uuid4(), Decimal("1.23")],
        },
    )
    object.__setattr__(evt, "tenant_id", "t1")
    object.__setattr__(evt, "aggregate_id", "agg-1")
    object.__setattr__(evt, "schema_id", "order")
    object.__setattr__(evt, "schema_version", 2)

    rec = OutboxRecord.from_domain_event(evt)

    # id is string
    assert isinstance(rec.id, str) and len(rec.id) > 0
    assert rec.tenant_id == "t1"
    assert rec.aggregate_id == "agg-1"
    assert rec.type == "MyEvent"
    assert rec.schema_id == "order"
    assert rec.schema_ver == 2

    # payload serialization checks
    payload = rec.payload
    assert isinstance(payload["u"], str)
    assert isinstance(payload["when"], str) and payload["when"].startswith("2024-01-02T03:04:05")
    assert isinstance(payload["price"], float)
    assert isinstance(payload["nested"]["id"], str)
    assert isinstance(payload["nested"]["ts"], str)
    assert payload["nested"]["arr"][1] == 1.23
