from __future__ import annotations

from bento.domain.specification import AndSpecification, Specification, and_spec


class TrueSpec(Specification[object]):
    def is_satisfied_by(self, candidate: object) -> bool:  # type: ignore[override]
        return True


class FalseSpec(Specification[object]):
    def is_satisfied_by(self, candidate: object) -> bool:  # type: ignore[override]
        return False


def test_and_specification_and_helper():
    a = AndSpecification(TrueSpec(), TrueSpec())
    b = AndSpecification(TrueSpec(), FalseSpec())

    assert a.is_satisfied_by(object()) is True
    assert b.is_satisfied_by(object()) is False

    s = and_spec(TrueSpec(), TrueSpec())
    assert isinstance(s, AndSpecification)
    assert s.is_satisfied_by(object()) is True
