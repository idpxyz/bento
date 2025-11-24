from __future__ import annotations

from bento.persistence.specification.core.types import Filter, FilterOperator, LogicalOperator
from bento.persistence.specification.criteria.base import AndCriterion, Criterion, OrCriterion


class FieldEqualsOne(Criterion):
    def __init__(self, field: str = "a"):
        self.field = field

    def to_filter(self) -> Filter:
        return Filter(self.field, FilterOperator.EQUALS, 1)


class FieldGreaterTwo(Criterion):
    def __init__(self, field: str = "b"):
        self.field = field

    def to_filter(self) -> Filter:
        return Filter(self.field, FilterOperator.GREATER_THAN, 2)


def test_composite_criterion_to_filter_and_group():
    c1 = FieldEqualsOne()
    c2 = FieldGreaterTwo()

    andc = AndCriterion(c1, c2)
    orc = OrCriterion(c1, c2)

    # to_filter returns first sub-criterion's filter
    f = andc.to_filter()
    assert f.field == "a" and f.operator == FilterOperator.EQUALS and f.value == 1

    # to_filter_group builds group with both filters and operator
    g1 = andc.to_filter_group()
    assert g1.operator == LogicalOperator.AND and len(g1.filters) == 2

    g2 = orc.to_filter_group()
    assert g2.operator == LogicalOperator.OR and len(g2.filters) == 2
