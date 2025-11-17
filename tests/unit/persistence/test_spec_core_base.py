from typing import Any

from bento.persistence.specification.core.base import CompositeSpecification
from bento.persistence.specification.core.types import (
    Filter,
    FilterGroup,
    FilterOperator,
    LogicalOperator,
    PageParams,
    Sort,
    SortDirection,
)


def test_composite_spec_to_query_params_and_withers():
    spec = CompositeSpecification[Any](
        filters=[Filter(field="status", operator=FilterOperator.EQUALS, value="active")],
        groups=[
            FilterGroup(
                filters=(
                    Filter(field="age", operator=FilterOperator.GREATER_EQUAL, value=18),
                    Filter(field="age", operator=FilterOperator.LESS_EQUAL, value=65),
                ),
                operator=LogicalOperator.AND,
            )
        ],
        sorts=[Sort(field="created_at", direction=SortDirection.DESC)],
        page=PageParams(page=2, size=20),
        fields=["id", "name"],
        includes=["items"],
    )

    params = spec.to_query_params()
    assert params["filters"][0].field == "status"
    assert params["groups"][0].operator == LogicalOperator.AND
    assert params["sorts"][0].direction == SortDirection.DESC
    assert params["page"].page == 2
    assert params["fields"] == ["id", "name"]
    assert params["includes"] == ["items"]

    # with_* builders
    spec2 = spec.with_filters([Filter("role", FilterOperator.EQUALS, "admin")])
    assert any(f.field == "role" for f in spec2.filters)

    spec3 = spec.with_sorts([Sort("name", SortDirection.ASC)])
    assert spec3.sorts == (Sort("name", SortDirection.ASC),)

    spec4 = spec.with_page(PageParams(page=3, size=5))
    assert spec4.page is not None and spec4.page.page == 3 and spec4.page.size == 5

    # and_ combination merges internals
    spec_and = spec.and_(spec2)
    assert len(spec_and.filters) >= len(spec.filters)

    # or_ turns combined filters into a group OR
    spec_or = spec.or_(spec2)
    assert spec_or.groups and any(g.operator == LogicalOperator.OR for g in spec_or.groups)


def test_is_satisfied_by_basic_and_group_logic():
    # Build a spec requiring status==active and (age>=18 AND age<65)
    spec = CompositeSpecification[Any](
        filters=[Filter("status", FilterOperator.EQUALS, "active")],
        groups=[
            FilterGroup(
                filters=(
                    Filter("age", FilterOperator.GREATER_EQUAL, 18),
                    Filter("age", FilterOperator.LESS_THAN, 65),
                ),
                operator=LogicalOperator.AND,
            )
        ],
    )

    class Obj:
        def __init__(self, status: str, age: int):
            self.status = status
            self.age = age

    assert spec.is_satisfied_by(Obj("active", 30)) is True
    assert spec.is_satisfied_by(Obj("inactive", 30)) is False
    assert spec.is_satisfied_by(Obj("active", 70)) is False
