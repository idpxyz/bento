"""藏干(地支内藏天干)及其五行计数"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .tengods import _STEM_ELEMENT

_HIDDEN_STEMS: dict[str, list[str]] = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}

__all__ = ["hidden_five_element_score", "hidden_stems"]


def hidden_stems(branch: str) -> List[str]:
    return _HIDDEN_STEMS[branch]


def hidden_five_element_score(branches: List[str]) -> Dict[str, int]:
    c: Counter[str] = Counter(
        {e: 0 for e in ["Wood", "Fire", "Earth", "Metal", "Water"]})
    for br in branches:
        for stem in _HIDDEN_STEMS[br]:
            c[_STEM_ELEMENT[stem]] += 1
    return dict(c)
