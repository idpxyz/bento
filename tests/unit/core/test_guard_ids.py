from __future__ import annotations

import pytest

from bento.core.guard import require
from bento.core.ids import ID


def test_guard_require_pass_and_fail():
    require(True)
    with pytest.raises(ValueError):
        require(False, "boom")


def test_id_behaves_like_str():
    id1 = ID("abc")
    id2 = ID("abc")
    assert id1 == id2
    assert id1 == "abc"
    assert "a" in id1
    assert id1.startswith("a")
    assert id1.endswith("c")
    assert id1.lower() == "abc"
    assert id1.upper() == "ABC"
    assert id1.replace("a", "z") == "zbc"
    assert f"{id1}" == "abc"
    assert id1 + "x" == "abcx"
    assert "x" + id1 == "xabc"
    assert id1[:2] == "ab"
    assert len(id1) == 3
