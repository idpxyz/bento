"""Tests for advanced features: override, ignore, batch mapping, etc."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from bento.application.mapper import AutoMapper


@dataclass
class Product:
    id: str
    name: str
    price: Decimal
    created_at: datetime
    uuid: UUID
    updated_at: date | None = None
    internal_id: str = "default"  # Should be ignored
    computed_value: str = "default"  # Should use override


@dataclass
class ProductModel:
    id: str
    name: str
    price: str = "0"  # Stored as string
    created_at: str = ""  # Stored as ISO string
    updated_at: str | None = None
    uuid: str = ""
    computed_value: str = ""


class ProductMapper(AutoMapper[Product, ProductModel]):
    def __init__(self) -> None:
        super().__init__(Product, ProductModel)
        self.ignore_fields("internal_id")
        # Set overrides before analysis (or rebuild after)
        self.override_field(
            "price",
            to_po=lambda p: str(p),
            from_po=lambda v: Decimal(v),
        )
        self.override_field(
            "created_at",
            to_po=lambda dt: dt.isoformat(),
            from_po=lambda v: datetime.fromisoformat(v),
        )
        self.override_field(
            "updated_at",
            to_po=lambda d: d.isoformat() if d else None,
            from_po=lambda v: date.fromisoformat(v) if v else None,
        )
        self.override_field(
            "uuid",
            to_po=lambda u: str(u),
            from_po=lambda v: UUID(v),
        )
        # computed_value is handled in before_map hook, so just pass through
        self.override_field(
            "computed_value",
            to_po=lambda v: v,  # Pass through (already computed in before_map)
            from_po=lambda v: v.replace("computed_", "") if v else "",
        )
        # Rebuild mappings to apply overrides
        self.rebuild_mappings()

    def before_map(self, domain: Product) -> None:
        """Hook to compute computed_value based on name."""
        # Store original value for reverse mapping
        if hasattr(domain, "computed_value"):
            # Store original in a temporary attribute
            domain._original_computed_value = domain.computed_value  # type: ignore[attr-defined]
            # Compute based on name field
            if hasattr(domain, "name"):
                domain.computed_value = f"computed_{domain.name}"

    def after_map(self, domain: Product, po: ProductModel) -> None:
        """Store original computed_value in PO for reverse mapping."""
        # Store original value in PO for later restoration
        if hasattr(domain, "_original_computed_value"):
            po._original_computed_value = domain._original_computed_value  # type: ignore[attr-defined]

    def after_map_reverse(self, po: ProductModel, domain: Product) -> None:
        """Restore original computed_value after reverse mapping."""
        # Restore the original value from PO
        if hasattr(po, "_original_computed_value"):
            domain.computed_value = po._original_computed_value  # type: ignore[attr-defined]


def test_ignore_fields():
    """Test that ignored fields are not mapped."""
    mapper = ProductMapper()

    product = Product(
        id="p1",
        name="Product 1",
        price=Decimal("99.99"),
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=date(2024, 1, 2),
        uuid=UUID("12345678-1234-5678-1234-567812345678"),
        internal_id="internal-123",  # Should be ignored
        computed_value="original",
    )

    po = mapper.map(product)

    # internal_id should not be in PO
    assert not hasattr(po, "internal_id") or getattr(po, "internal_id", None) is None


def test_override_field():
    """Test that override_field() customizes conversion."""
    mapper = ProductMapper()

    product = Product(
        id="p1",
        name="Test",
        price=Decimal("99.99"),
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=date(2024, 1, 2),
        uuid=UUID("12345678-1234-5678-1234-567812345678"),
        internal_id="ignored",
        computed_value="original",
    )

    po = mapper.map(product)
    assert po.price == "99.99"  # Converted to string
    assert po.created_at == "2024-01-01T12:00:00"  # ISO format
    assert po.computed_value == "computed_Test"  # Custom logic

    # Reverse mapping
    domain = mapper.map_reverse(po)
    assert domain.price == Decimal("99.99")
    assert domain.created_at == datetime(2024, 1, 1, 12, 0, 0)
    assert domain.computed_value == "original"  # Reversed


def test_simple_type_extensions():
    """Test that datetime, UUID, Decimal are handled (via override in this case)."""
    mapper = ProductMapper()

    product = Product(
        id="p1",
        name="Test",
        price=Decimal("99.99"),
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=date(2024, 1, 2),
        uuid=UUID("12345678-1234-5678-1234-567812345678"),
        internal_id="ignored",
        computed_value="original",
    )

    po = mapper.map(product)

    # Verify types are converted
    assert isinstance(po.price, str)
    assert isinstance(po.created_at, str)
    assert isinstance(po.uuid, str)

    domain = mapper.map_reverse(po)
    assert isinstance(domain.price, Decimal)
    assert isinstance(domain.created_at, datetime)
    assert isinstance(domain.uuid, UUID)
    assert isinstance(domain.updated_at, date)


def test_batch_mapping():
    """Test map_list() and map_reverse_list() batch operations."""
    mapper = ProductMapper()

    products = [
        Product(
            id=f"p{i}",
            name=f"Product {i}",
            price=Decimal(f"{i}.99"),
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=date(2024, 1, 2),
            uuid=UUID("12345678-1234-5678-1234-567812345678"),
            internal_id="ignored",
            computed_value="original",
        )
        for i in range(3)
    ]

    # Batch map
    pos = mapper.map_list(products)
    assert len(pos) == 3
    assert all(isinstance(po, ProductModel) for po in pos)
    assert pos[0].id == "p0"
    assert pos[2].id == "p2"

    # Batch reverse map
    domains = mapper.map_reverse_list(pos)
    assert len(domains) == 3
    assert all(isinstance(d, Product) for d in domains)
    assert domains[0].id == "p0"
    assert domains[2].id == "p2"


def test_runtime_type_validation():
    """Test that map() and map_reverse() validate types at runtime."""
    mapper = ProductMapper()

    # Wrong type for map()
    with pytest.raises(TypeError) as exc:
        mapper.map("not a product")  # type: ignore[arg-type]

    assert "Expected instance of" in str(exc.value)
    assert "Product" in str(exc.value)

    # Wrong type for map_reverse()
    with pytest.raises(TypeError) as exc:
        mapper.map_reverse("not a model")  # type: ignore[arg-type]

    assert "Expected instance of" in str(exc.value)
    assert "ProductModel" in str(exc.value)


def test_construction_fallback():
    """Test that construction falls back to setattr when __init__ fails."""

    class NoInitPO:
        def __init__(self) -> None:
            pass  # No parameters

        id: str = ""
        name: str = ""

    @dataclass
    class SimpleDomain:
        id: str
        name: str

    class FallbackMapper(AutoMapper[SimpleDomain, NoInitPO]):
        def __init__(self) -> None:
            super().__init__(SimpleDomain, NoInitPO)

    mapper = FallbackMapper()

    domain = SimpleDomain(id="d1", name="Test")

    # Should use fallback strategy (no-arg + setattr)
    po = mapper.map(domain)
    assert po.id == "d1"
    assert po.name == "Test"
