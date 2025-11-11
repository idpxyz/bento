# -*- coding: utf‑8 -*-
"""Very rudimentary five‑element scoring (五行平衡) based on stems & branches."""
from __future__ import annotations

from collections import Counter
from typing import Dict

from .constants import GAN, ZHI
from .tengods import _STEM_ELEMENT  # reuse

_BRANCH_ELEMENT = {
    "子": "Water", "丑": "Earth", "寅": "Wood", "卯": "Wood", "辰": "Earth",
    "巳": "Fire", "午": "Fire", "未": "Earth", "申": "Metal", "酉": "Metal",
    "戌": "Earth", "亥": "Water",
}
__all__ = ["five_element_score"]


def five_element_score(pillars: tuple[str, str, str, str]) -> Dict[str, int]:
    counter: Counter[str] = Counter(
        {e: 0 for e in ["Wood", "Fire", "Earth", "Metal", "Water"]})
    for gz in pillars:
        g, z = gz[0], gz[1]
        counter[_STEM_ELEMENT[g]] += 1
        counter[_BRANCH_ELEMENT[z]] += 1
    return dict(counter)
