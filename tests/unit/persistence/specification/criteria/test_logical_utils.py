from __future__ import annotations

from bento.persistence.specification.core.types import Filter, FilterOperator, LogicalOperator
from bento.persistence.specification.criteria.base import (
    AndCriterion,
    CompositeCriterion,
    Criterion,
)
from bento.persistence.specification.criteria.logical import And, Or, to_filter_group


class C1(Criterion):
    def to_filter(self) -> Filter:
        return Filter("x", FilterOperator.EQUALS, 1)


class C2(Criterion):
    def to_filter(self) -> Filter:
        return Filter("y", FilterOperator.GREATER_THAN, 2)


def test_and_or_wrappers_and_to_filter_group():
    a = And(C1(), C2())
    o = Or(C1(), C2())

    assert isinstance(a, AndCriterion)

    g = to_filter_group(a)
    assert g.operator == LogicalOperator.AND and len(g.filters) == 2

    g2 = to_filter_group(o)
    assert g2.operator == LogicalOperator.OR and len(g2.filters) == 2


def test_composite_criterion_empty_raises():
    try:
        CompositeCriterion([], LogicalOperator.AND)  # type: ignore[arg-type]
        raise AssertionError("should raise")
    except ValueError:
        pass
