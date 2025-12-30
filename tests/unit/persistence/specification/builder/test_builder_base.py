from __future__ import annotations

import pytest

from bento.persistence.specification.builder.base import SpecificationBuilder
from bento.persistence.specification.core.types import LogicalOperator, Page


def test_builder_basic_chaining_and_build_page_conversion():
    b = (
        SpecificationBuilder()
        .equals("age", 18)
        .not_equals("role", "guest")
        .greater_than("score", 10)
        .less_than("score", 100)
        .between("created", 1, 2)
        .in_list("tag", ["a", "b"])
        .is_null("deleted_at")
        .is_not_null("updated_at")
        .contains("name", "foo")
        .order_by("created", "desc")
        .paginate(page=2, size=5)
        .select("f1", "f2")
        .include("rel1")
        .group_by("grp")
        .count("id", alias="c")
        .sum("amount", alias="s")
        .avg("score", alias="avg")
    )

    spec = b.build()
    # page converted via Page.create
    assert isinstance(spec.page, Page)
    assert spec.page.page == 2 and spec.page.size == 5


def test_builder_groups_and_errors():
    b = SpecificationBuilder()

    # start OR group -> add filters -> end
    b.group(LogicalOperator.OR).equals("status", "active").equals("status", "pending").end_group()
    spec = b.build()
    params = spec.to_query_params()
    assert "groups" in params and len(params["groups"]) == 1

    # error: start group twice
    b2 = SpecificationBuilder()
    b2.group("AND")
    with pytest.raises(ValueError):
        b2.group("OR")

    # error: end_group with no active group
    with pytest.raises(ValueError):
        b2.end_group()
        b2.end_group()

    # error: build with open group
    b3 = SpecificationBuilder().group("OR").equals("x", 1)
    with pytest.raises(ValueError):
        b3.build()
