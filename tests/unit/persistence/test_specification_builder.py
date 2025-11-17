import pytest

from bento.persistence.specification.builder.base import SpecificationBuilder
from bento.persistence.specification.core.base import (
    CompositeSpecification,
    Filter,
    Sort,
)
from bento.persistence.specification.core.types import FilterOperator, Page, SortDirection


def test_where_operators_and_build():
    builder = SpecificationBuilder[dict]()

    spec = (
        builder.equals("age", 18)
        .not_equals("status", "inactive")
        .greater_than("score", 10)
        .less_than("score", 100)
        .between("created_at", "2024-01-01", "2024-12-31")
        .in_list("country", ["US", "CN"])
        .is_null("deleted_at")
        .is_not_null("updated_at")
        .contains("name", "john")
        .order_by("created_at", "desc")
        .paginate(page=2, size=25)
        .build()
    )

    assert isinstance(spec, CompositeSpecification)
    assert spec.filters is not None
    ops = [f.operator for f in spec.filters if isinstance(f, Filter)]
    assert FilterOperator.EQUALS in ops
    assert FilterOperator.NOT_EQUALS in ops
    assert FilterOperator.GREATER_THAN in ops
    assert FilterOperator.LESS_THAN in ops
    assert FilterOperator.BETWEEN in ops
    assert FilterOperator.IN in ops
    assert FilterOperator.IS_NULL in ops
    assert FilterOperator.IS_NOT_NULL in ops
    assert FilterOperator.ILIKE in ops  # contains uses ILIKE

    # sorts (CompositeSpecification.sorts is a tuple)
    assert spec.sorts == (Sort(field="created_at", direction=SortDirection.DESC),)
    # page converted from PageParams
    assert isinstance(spec.page, Page)
    assert spec.page.page == 2 and spec.page.size == 25


def test_grouping_and_end_group_build():
    builder = SpecificationBuilder[dict]()
    builder.group("OR").equals("status", "active").equals("status", "pending").end_group()
    spec = builder.build()
    assert spec.groups is not None and len(spec.groups) == 1
    grp = spec.groups[0]
    assert grp.operator.value == "or"
    assert len(grp.filters) == 2


def test_build_raises_with_open_group():
    builder = SpecificationBuilder[dict]()
    builder.group("AND").equals("status", "active")
    with pytest.raises(ValueError):
        _ = builder.build()


def test_unknown_operator_raises():
    builder = SpecificationBuilder[dict]()
    with pytest.raises(ValueError):
        builder.where("x", "~~", 1)
