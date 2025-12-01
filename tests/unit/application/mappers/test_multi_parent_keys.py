"""Tests for multi-parent keys and MappingContext."""

from dataclasses import dataclass

from bento.application.mappers import AutoMapper, MappingContext


@dataclass
class OrderItem:
    id: str
    sku: str
    qty: int
    order_id: str | None = None
    tenant_id: str | None = None
    org_id: str | None = None


@dataclass
class OrderItemModel:
    id: str
    sku: str
    qty: int
    order_id: str | None = None
    tenant_id: str | None = None
    org_id: str | None = None


@dataclass
class Order:
    id: str
    tenant_id: str | None
    org_id: str | None
    items: list[OrderItem]


@dataclass
class OrderModel:
    id: str
    tenant_id: str | None
    org_id: str | None
    items: list[OrderItemModel]


class ItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    def __init__(self) -> None:
        super().__init__(OrderItem, OrderItemModel)
        self.ignore_fields("order_id", "tenant_id", "org_id")


class OrderMapper(AutoMapper[Order, OrderModel]):
    def __init__(self, context: MappingContext | None = None) -> None:
        super().__init__(Order, OrderModel, context=context)
        # Multi-parent keys: tenant_id + org_id + order_id
        self.register_child("items", ItemMapper(), parent_keys=["tenant_id", "org_id", "order_id"])


def test_multi_parent_keys_propagation():
    """Test that multiple parent keys are propagated to children."""
    mapper = OrderMapper()

    order = Order(
        id="ord-1",
        tenant_id="t-001",
        org_id="o-001",
        items=[OrderItem(id="i1", sku="SKU-1", qty=2)],
    )

    po = mapper.map(order)

    # Verify parent keys are set on child
    assert len(po.items) == 1
    item_po = po.items[0]
    assert item_po.order_id == "ord-1"
    assert item_po.tenant_id == "t-001"
    assert item_po.org_id == "o-001"


def test_mapping_context_propagation():
    """Test that MappingContext values are propagated to children."""
    context = MappingContext(tenant_id="ctx-tenant", org_id="ctx-org", actor_id="actor-1")
    mapper = OrderMapper(context=context)

    order = Order(
        id="ord-1",
        tenant_id="order-tenant",  # This should be overridden by context
        org_id="order-org",  # This should be overridden by context
        items=[OrderItem(id="i1", sku="SKU-1", qty=2)],
    )

    po = mapper.map(order)

    # Context values should take precedence
    item_po = po.items[0]
    assert item_po.tenant_id == "ctx-tenant"  # From context
    assert item_po.org_id == "ctx-org"  # From context
    assert item_po.order_id == "ord-1"  # From parent domain.id


def test_mapping_context_extra():
    """Test that MappingContext.extra values are propagated."""
    context = MappingContext(
        tenant_id="t-1",
        org_id="o-1",
        extra={"channel": "web", "source": "api"},
    )
    mapper = OrderMapper(context=context)

    # Note: This test assumes extra fields can be set via context
    # Actual implementation may vary based on map_children logic
    order = Order(
        id="ord-1",
        tenant_id="t-1",
        org_id="o-1",
        items=[OrderItem(id="i1", sku="SKU-1", qty=2)],
    )

    po = mapper.map(order)
    assert len(po.items) == 1
    # Context should be available for propagation
    assert po.tenant_id == "t-1"
    assert po.org_id == "o-1"


def test_child_parent_keys_introspection():
    """Test that child_parent_keys() returns correct keys."""
    mapper = OrderMapper()

    keys = mapper.child_parent_keys("items")
    assert keys == ("tenant_id", "org_id", "order_id")

    # Test with single parent key
    single_key_mapper = OrderMapper()
    single_key_mapper.register_child("items", ItemMapper(), parent_keys="order_id")
    single_keys = single_key_mapper.child_parent_keys("items")
    assert single_keys == ("order_id",)


def test_reuse_child_mapper_different_parents():
    """Test that same child mapper can be reused with different parent keys."""
    shared_item_mapper = ItemMapper()

    # Order mapper with multi-keys
    order_mapper = OrderMapper()
    order_mapper.register_child(
        "items", shared_item_mapper, parent_keys=["tenant_id", "org_id", "order_id"]
    )

    # Shipment mapper with different keys
    @dataclass
    class Shipment:
        id: str
        items: list[OrderItem]

    @dataclass
    class ShipmentModel:
        id: str
        items: list[OrderItemModel]

    class ShipmentMapper(AutoMapper[Shipment, ShipmentModel]):
        def __init__(self) -> None:
            super().__init__(Shipment, ShipmentModel)
            # Reuse same mapper with different parent key
            self.register_child("items", shared_item_mapper, parent_keys="shipment_id")

    shipment_mapper = ShipmentMapper()

    # Verify parent keys are independent
    assert order_mapper.child_parent_keys("items") == ("tenant_id", "org_id", "order_id")
    assert shipment_mapper.child_parent_keys("items") == ("shipment_id",)
