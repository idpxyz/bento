"""Tests for domain event cleanup."""

from dataclasses import dataclass, field

from bento.application.mappers import AutoMapper, BaseMapper


@dataclass
class Order:
    id: str
    status: str
    _events: list[object] = field(default_factory=list)

    def clear_events(self) -> None:
        self._events.clear()


@dataclass
class OrderModel:
    id: str
    status: str


class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self) -> None:
        super().__init__(Order, OrderModel)


def test_auto_clear_events_on_map_reverse():
    """Test that events are automatically cleared after map_reverse."""
    mapper = OrderMapper()

    # Create PO
    po = OrderModel(id="ord-1", status="NEW")

    # Map to domain (should have events cleared)
    domain = mapper.map_reverse(po)

    # Verify events list is empty (or was cleared)
    assert len(domain._events) == 0


def test_map_reverse_with_events():
    """Test map_reverse_with_events() explicitly clears events."""

    class OrderMapperBase(BaseMapper[Order, OrderModel]):
        def __init__(self) -> None:
            super().__init__(Order, OrderModel)

        def map(self, domain: Order) -> OrderModel:
            return OrderModel(id=domain.id, status=domain.status)

        def map_reverse(self, po: OrderModel) -> Order:
            return Order(id=po.id, status=po.status, _events=[object()])

    mapper = OrderMapperBase()

    po = OrderModel(id="ord-1", status="NEW")

    # Use map_reverse_with_events
    domain = mapper.map_reverse_with_events(po)

    # Events should be cleared
    assert len(domain._events) == 0


def test_clear_events_idempotent():
    """Test that clear_events() can be called multiple times safely."""
    order = Order(id="ord-1", status="NEW", _events=[object(), object()])

    # Call multiple times
    order.clear_events()
    assert len(order._events) == 0

    order.clear_events()  # Should not raise
    assert len(order._events) == 0


def test_domain_without_clear_events():
    """Test that domains without clear_events() don't cause errors."""

    @dataclass
    class SimpleOrder:
        id: str
        status: str

    @dataclass
    class SimpleOrderModel:
        id: str
        status: str

    class SimpleMapper(AutoMapper[SimpleOrder, SimpleOrderModel]):
        def __init__(self) -> None:
            super().__init__(SimpleOrder, SimpleOrderModel)

    mapper = SimpleMapper()

    po = SimpleOrderModel(id="ord-1", status="NEW")

    # Should not raise even though SimpleOrder has no clear_events()
    domain = mapper.map_reverse(po)
    assert domain.id == "ord-1"
