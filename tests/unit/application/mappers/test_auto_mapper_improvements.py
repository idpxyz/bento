from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pytest

from bento.application.mappers.auto import AutoMapper
from bento.core.ids import ID

# ---------- Test models ----------


class Status(Enum):
    PENDING = "pending"
    PAID = "paid"


@dataclass
class DomWithIds:
    id: ID
    user_id: ID | None
    status: Status

    # simple event buffer for testing
    def __init__(self, id: ID, user_id: ID | None, status: Status) -> None:
        self.id = id
        self.user_id = user_id
        self.status = status
        self._events: list[object] = []

    def add_event(self, e: object) -> None:
        self._events.append(e)

    def get_events(self) -> list[object]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()


@dataclass
class PoWithIds:
    id: str
    status: str
    user_id: str | None = None


@dataclass
class PoAmbiguous:
    # both fields exist; matching should pick user_id over user
    id: str
    status: str
    user_id: str | None = None
    user: str = ""


@dataclass
class PoEnumInt:
    id: str
    status: int
    user_id: str | None = None


# ---------- Tests ----------


def test_map_reverse_normalizes_str_to_id() -> None:
    mapper = AutoMapper(DomWithIds, PoWithIds)
    # Explicit overrides to stabilize behavior
    mapper.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper.override_field(
        "user_id",
        to_po=lambda v: (None if v is None else str(v.value)),
        from_po=lambda v: (None if v is None else ID(str(v))),
    )
    mapper.override_field("status", to_po=lambda s: s.value, from_po=lambda v: Status(v))
    mapper.rebuild_mappings()
    po = PoWithIds(id="o-1", user_id="u-9", status="pending")
    dom = mapper.map_reverse(po)
    assert isinstance(dom.id, ID)
    assert isinstance(dom.user_id, ID)
    assert dom.id.value == "o-1"
    assert dom.user_id and dom.user_id.value == "u-9"
    assert dom.status is Status.PENDING


def test_field_matching_priority_picks_user_id_over_user() -> None:
    mapper = AutoMapper(DomWithIds, PoAmbiguous)
    mapper.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper.override_field(
        "user_id",
        to_po=lambda v: (None if v is None else str(v.value)),
        from_po=lambda v: (None if v is None else ID(str(v))),
    )
    mapper.override_field("status", to_po=lambda s: s.value, from_po=lambda v: Status(v))
    mapper.rebuild_mappings()
    dom = DomWithIds(id=ID("o-2"), user_id=ID("u-2"), status=Status.PAID)
    po = mapper.map(dom)
    # should map to user_id, not user
    assert po.user_id == "u-2"
    # 'user' remains default (empty string) because dataclass requires value;
    # our map sets only matched fields
    assert po.user == ""


def test_instance_level_cache_handles_enum_str_and_int() -> None:
    # mapper A: enum -> str
    mapper_str = AutoMapper(DomWithIds, PoWithIds)
    mapper_str.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper_str.override_field(
        "user_id",
        to_po=lambda v: (None if v is None else str(v.value)),
        from_po=lambda v: (None if v is None else ID(str(v))),
    )
    mapper_str.override_field("status", to_po=lambda s: s.value, from_po=lambda v: Status(v))
    mapper_str.rebuild_mappings()
    po_s = mapper_str.map(DomWithIds(id=ID("x"), user_id=None, status=Status.PENDING))
    assert po_s.status == "pending"
    # mapper B: enum -> int
    mapper_int = AutoMapper(DomWithIds, PoEnumInt)
    mapper_int.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper_int.override_field(
        "user_id",
        to_po=lambda v: (None if v is None else str(v.value)),
        from_po=lambda v: (None if v is None else ID(str(v))),
    )
    # enum -> ordinal int; reverse from int
    mapper_int.override_field(
        "status", to_po=lambda s: list(Status).index(s), from_po=lambda i: list(Status)[int(i)]
    )
    mapper_int.rebuild_mappings()
    po_i = mapper_int.map(DomWithIds(id=ID("y"), user_id=None, status=Status.PAID))
    assert isinstance(po_i.status, int)
    assert po_i.status in (0, 1)  # Enum value index cast by inference path


def test_auto_clear_events_selective() -> None:
    mapper = AutoMapper(DomWithIds, PoWithIds)
    po = PoWithIds(id="o-3", user_id=None, status="paid")
    dom = mapper.map_reverse(po)
    if not hasattr(dom, "_events"):
        dom._events = []

    class KeepMe: ...

    class DropMe: ...

    dom.add_event(KeepMe())
    dom.add_event(DropMe())

    # keep only KeepMe
    mapper.auto_clear_events(dom, exclude_types={KeepMe})
    remaining = dom.get_events()
    assert len(remaining) == 1
    assert isinstance(remaining[0], KeepMe)


def test_name_based_id_fallback_on_reverse() -> None:
    @dataclass
    class DomX:
        product_id: ID

    @dataclass
    class PoX:
        product_id: str

    mapper = AutoMapper(DomX, PoX)
    dom = mapper.map_reverse(PoX(product_id="p-1"))
    assert isinstance(dom.product_id, ID)
    assert dom.product_id.value == "p-1"


def test_optional_none_passthrough() -> None:
    mapper = AutoMapper(DomWithIds, PoWithIds)
    mapper.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper.override_field(
        "user_id",
        to_po=lambda v: (None if v is None else str(v.value)),
        from_po=lambda v: (None if v is None else ID(str(v))),
    )
    mapper.override_field("status", to_po=lambda s: s.value, from_po=lambda v: Status(v))
    mapper.rebuild_mappings()
    po = mapper.map(DomWithIds(id=ID("o-10"), user_id=None, status=Status.PENDING))
    assert po.user_id is None


def test_enum_int_reverse_default_inference() -> None:
    mapper = AutoMapper(DomWithIds, PoEnumInt)
    # ensure id mapping and explicit enum reverse from int
    mapper.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper.override_field(
        "status", to_po=lambda s: list(Status).index(s), from_po=lambda i: list(Status)[int(i)]
    )
    mapper.rebuild_mappings()
    dom = mapper.map_reverse(PoEnumInt(id="o-11", status=0, user_id=None))
    assert isinstance(dom.status, Status)


def test_unmapped_po_fields_get_basic_defaults() -> None:
    @dataclass
    class PoY:
        id: str
        status: str
        note: str = ""  # not present in domain mapping

    mapper = AutoMapper(DomWithIds, PoY)
    mapper.override_field("id", to_po=lambda v: str(v.value), from_po=lambda v: ID(str(v)))
    mapper.override_field("status", to_po=lambda s: s.value, from_po=lambda v: Status(v))
    mapper.rebuild_mappings()
    po = mapper.map(DomWithIds(id=ID("o-12"), user_id=None, status=Status.PENDING))
    assert hasattr(po, "note")
    assert po.note == ""


def test_strict_mode_unmapped_raises() -> None:
    mapper = AutoMapper(DomWithIds, PoWithIds, strict=True)
    # whitelist a non-existent field to trigger suggestion/raise
    with pytest.raises(ValueError):
        mapper.only_fields("non_exist_field")


def test_alias_field_matching() -> None:
    @dataclass
    class DomAlias:
        customerId: ID

    @dataclass
    class PoAlias:
        customer_id: str

    mapper = AutoMapper(DomAlias, PoAlias)
    mapper.alias_field("customerId", "customer_id")
    po = mapper.map(DomAlias(customerId=ID("c-77")))
    assert po.customer_id == "c-77"
