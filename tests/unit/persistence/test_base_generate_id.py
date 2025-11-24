from __future__ import annotations

from bento.persistence.po.base import Base


def test_base_generate_id_format():
    val = Base._generate_id()
    assert isinstance(val, str)
    assert len(val) == 36 and val.count("-") == 4
