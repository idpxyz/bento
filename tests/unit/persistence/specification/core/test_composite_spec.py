from __future__ import annotations

import pytest

from bento.persistence.specification.core.base import CompositeSpecification
from bento.persistence.specification.core.types import (
    Filter,
    FilterGroup,
    FilterOperator,
    Having,
    LogicalOperator,
    PageParams,
    Sort,
    SortDirection,
    Statistic,
    StatisticalFunction,
)


class Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_to_query_params_contains_all_sections():
    spec = CompositeSpecification(
        filters=[Filter("a", FilterOperator.EQUALS, 1)],
        groups=[FilterGroup(filters=(Filter("b", FilterOperator.GREATER_EQUAL, 2),))],
        sorts=[Sort("a", SortDirection.DESC)],
        page=PageParams(page=2, size=5),
        fields=["f1", "f2"],
        includes=["rel1"],
        statistics=[Statistic(StatisticalFunction.COUNT, "id")],
        group_by=["role"],
        having=[Having("cnt", FilterOperator.GREATER_THAN, 10)],
        joins=[{"table": "t", "on": "id"}],
    )

    params = spec.to_query_params()

    assert set(params.keys()) == {
        "filters",
        "groups",
        "sorts",
        "page",
        "fields",
        "includes",
        "statistics",
        "group_by",
        "having",
        "joins",
    }
    assert params["page"].page == 2 and params["page"].size == 5
    assert params["sorts"][0].field == "a" and params["sorts"][0].direction == SortDirection.DESC


def test_limit_offset_properties():
    page = PageParams(page=3, size=7)
    spec = CompositeSpecification(page=page)
    assert spec.limit == 7
    assert spec.offset == page.offset == 14


def test_is_satisfied_by_and_group_checks():
    # basic filters
    spec = CompositeSpecification(
        filters=[
            Filter("x", FilterOperator.EQUALS, 5),
            Filter("y", FilterOperator.GREATER_EQUAL, 2),
        ],
        groups=[
            FilterGroup(filters=(Filter("z", FilterOperator.IN, {1, 2, 3}),)),
        ],
    )

    assert spec.is_satisfied_by(Obj(x=5, y=3, z=2)) is True
    assert spec.is_satisfied_by(Obj(x=4, y=3, z=2)) is False

    # OR group succeeds if any filter ok
    or_group_spec = CompositeSpecification(
        groups=[
            FilterGroup(
                filters=(
                    Filter("a", FilterOperator.EQUALS, 1),
                    Filter("b", FilterOperator.EQUALS, 2),
                ),
                operator=LogicalOperator.OR,
            ),
        ]
    )
    assert or_group_spec.is_satisfied_by(Obj(a=0, b=2)) is True
    assert or_group_spec.is_satisfied_by(Obj(a=1, b=9)) is True
    assert or_group_spec.is_satisfied_by(Obj(a=0, b=0)) is False


def test_withers_and_combinators():
    base = CompositeSpecification(filters=[Filter("x", FilterOperator.EQUALS, 1)])
    with_more = base.with_filters([Filter("y", FilterOperator.IS_NOT_NULL, None)])
    assert len(with_more.filters) == 2

    sorted_spec = base.with_sorts([Sort("x", SortDirection.ASC)])
    assert len(sorted_spec.sorts) == 1 and sorted_spec.sorts[0].ascending is True

    paged = base.with_page(PageParams(page=1, size=10))
    assert paged.limit == 10 and paged.offset == 0

    other = CompositeSpecification(filters=[Filter("z", FilterOperator.LESS_EQUAL, 5)])
    both = base.and_(other)
    assert len(both.filters) == 2

    # or_ converts combined filters into an OR group and clears top-level filters
    or_spec = base.or_(other)
    params = or_spec.to_query_params()
    assert "groups" in params and len(params["groups"]) >= 1
    assert "filters" not in params  # filters moved into group


def test_not_raises_not_implemented():
    spec = CompositeSpecification()
    with pytest.raises(NotImplementedError):
        spec.not_()
