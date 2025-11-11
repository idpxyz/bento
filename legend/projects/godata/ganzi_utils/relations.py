# -*- coding: utf‑8 -*-
"""Utility functions for 六合 / 六冲 / 三合 等关系判断."""
from __future__ import annotations

from .constants import HAI, LIU_CHONG, LIU_HE, PO, SAN_HE, XING

__all__ = [
    "is_liuhe", "is_chong", "in_sanhe", "is_xing", "is_hai", "is_po", "relation_type",
]


def _dual_dict_match(table: dict[str, str], a: str, b: str) -> bool:
    return table.get(a) == b or table.get(b) == a


def is_liuhe(a: str, b: str):
    return _dual_dict_match(LIU_HE, a, b)


def is_chong(a: str, b: str):
    return _dual_dict_match(LIU_CHONG, a, b)


def in_sanhe(*branches: str):
    s = set(branches)
    return any(s.issubset(g) for g in SAN_HE)


def is_xing(a: str, b: str):
    return _dual_dict_match(XING, a, b)


def is_hai(a: str, b: str):
    return _dual_dict_match(HAI, a, b)


def is_po(a: str, b: str):
    return _dual_dict_match(PO, a, b)


_REL_FUNS = {
    "六合": is_liuhe,
    "冲": is_chong,
    "刑": is_xing,
    "害": is_hai,
    "破": is_po,
}


def relation_type(a: str, b: str) -> str | None:
    """Return first matching relation name between *a* and *b* or None."""
    for name, fn in _REL_FUNS.items():
        if fn(a, b):
            return name
    return None
