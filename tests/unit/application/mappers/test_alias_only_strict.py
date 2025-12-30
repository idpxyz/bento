from dataclasses import dataclass

import pytest

from bento.application.mappers import AutoMapper


@dataclass
class Domain:
    id: str
    customerId: str
    note: str


@dataclass
class PO:
    id: str
    customer_id: str
    # intentionally missing 'note' to test only_fields behavior


class Mapper(AutoMapper[Domain, PO]):
    def __init__(self, *, strict: bool = False):
        super().__init__(Domain, PO, strict=strict)


def test_alias_field_and_only_fields_mapping():
    mapper = Mapper()
    # alias domain.customerId -> po.customer_id
    mapper.alias_field("customerId", "customer_id").only_fields("id", "customerId")

    d = Domain(id="o1", customerId="c9", note="ignored")
    po = mapper.map(d)

    assert po.id == "o1"
    assert po.customer_id == "c9"
    # 'note' is not in only_fields, should not be required in PO


def test_strict_mode_raises_with_suggestions():
    mapper = Mapper(strict=True)
    # Ask to map a non-existent/unmappable field to trigger strict mode
    with pytest.raises(ValueError) as exc:
        mapper.only_fields("missingField")

    msg = str(exc.value)
    assert "AutoMapper strict mode" in msg
    assert "missingField" in msg
