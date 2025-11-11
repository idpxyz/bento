"""Tests for type conversions: ID, Enum, Optional, Annotated."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

import pytest

from bento.application.mapper import AutoMapper
from bento.core.ids import ID, EntityId


class OrderStatus(Enum):
    NEW = "NEW"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Order:
    id: ID
    entity_id: EntityId | None
    status: OrderStatus
    priority: Priority
    annotated_id: Annotated[ID, "primary key"]
    optional_status: OrderStatus | None = None


@dataclass
class OrderModel:
    id: str
    entity_id: str | None = None  # Make optional with default
    status: str = "NEW"
    priority: int = 1
    annotated_id: str = "annotated-1"
    optional_status: str | None = None


class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self) -> None:
        super().__init__(Order, OrderModel)


def test_id_conversion():
    """Test ID/EntityId ↔ str conversion."""
    mapper = OrderMapper()

    order = Order(
        id=ID("order-123"),
        entity_id=EntityId("entity-456"),
        status=OrderStatus.NEW,
        priority=Priority.MEDIUM,
        annotated_id=ID("annotated-789"),
    )

    po = mapper.map(order)
    assert po.id == "order-123"
    # entity_id should be converted to str (not EntityId)
    assert po.entity_id == "entity-456"
    assert po.annotated_id == "annotated-789"

    # Reverse mapping
    domain = mapper.map_reverse(po)
    assert isinstance(domain.id, ID)
    assert domain.id.value == "order-123"
    assert isinstance(domain.entity_id, EntityId)
    assert domain.entity_id.value == "entity-456"


def test_enum_to_str_conversion():
    """Test Enum ↔ str conversion."""
    mapper = OrderMapper()

    order = Order(
        id=ID("order-1"),
        entity_id=None,
        status=OrderStatus.PAID,
        priority=Priority.HIGH,
        annotated_id=ID("id-1"),
    )

    po = mapper.map(order)
    assert po.status == "PAID"

    domain = mapper.map_reverse(po)
    assert domain.status == OrderStatus.PAID


def test_enum_to_int_conversion():
    """Test Enum ↔ int conversion."""
    mapper = OrderMapper()

    order = Order(
        id=ID("order-1"),
        entity_id=None,
        status=OrderStatus.NEW,
        priority=Priority.MEDIUM,  # value = 2
        annotated_id=ID("id-1"),
    )

    po = mapper.map(order)
    assert po.priority == 2  # Enum value as int

    domain = mapper.map_reverse(po)
    assert domain.priority == Priority.MEDIUM


def test_optional_fields():
    """Test Optional fields mapping."""
    mapper = OrderMapper()

    # With None
    order = Order(
        id=ID("order-1"),
        entity_id=None,
        status=OrderStatus.NEW,
        priority=Priority.LOW,
        annotated_id=ID("id-1"),
        optional_status=None,
    )

    po = mapper.map(order)
    assert po.entity_id is None
    assert po.optional_status is None

    # With value
    order2 = Order(
        id=ID("order-2"),
        entity_id=EntityId("entity-2"),
        status=OrderStatus.PAID,
        priority=Priority.HIGH,
        annotated_id=ID("id-2"),
        optional_status=OrderStatus.CANCELLED,
    )

    po2 = mapper.map(order2)
    assert po2.entity_id == "entity-2"
    assert po2.optional_status == "CANCELLED"

    domain2 = mapper.map_reverse(po2)
    assert domain2.optional_status == OrderStatus.CANCELLED


def test_annotated_types():
    """Test Annotated types are properly unwrapped."""
    mapper = OrderMapper()

    order = Order(
        id=ID("order-1"),
        entity_id=None,
        status=OrderStatus.NEW,
        priority=Priority.LOW,
        annotated_id=ID("annotated-1"),
    )

    po = mapper.map(order)
    assert po.annotated_id == "annotated-1"

    domain = mapper.map_reverse(po)
    assert isinstance(domain.annotated_id, ID)
    assert domain.annotated_id.value == "annotated-1"


def test_enum_invalid_value_raises_error():
    """Test that invalid enum values raise descriptive errors."""
    mapper = OrderMapper()

    po = OrderModel(
        id="order-1",
        entity_id=None,
        status="INVALID_STATUS",  # Invalid enum value
        priority=1,
        annotated_id="id-1",
    )

    with pytest.raises(ValueError) as exc:
        mapper.map_reverse(po)

    msg = str(exc.value)
    assert "Invalid OrderStatus" in msg
    assert "INVALID_STATUS" in msg
    assert "Allowed values" in msg or "Allowed names" in msg
