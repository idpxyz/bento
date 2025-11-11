from __future__ import annotations

from typing import Dict

from .strength import apply_strength_corrections

__all__ = ["useful_god"]

_PRIORITY = ["Wood", "Fire", "Earth", "Metal", "Water"]  # 当作示例优先级


def useful_god(scores: Dict[str, int]) -> str:
    corrected = apply_strength_corrections(scores)
    # 找最弱元素作为“用神”
    weakest = min(_PRIORITY, key=lambda e: corrected[e])
    return weakest
