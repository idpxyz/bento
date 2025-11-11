"""旺衰/生克修正分数"""
from __future__ import annotations

from typing import Dict

_SEASON_TABLE: dict[str, dict[str, int]] = {
    # element → score (旺=5 相=3 休=1 囚=‑1 死=‑3) – 可自行微调
    "寅": {"Wood": 5, "Fire": 3, "Earth": 1, "Metal": -1, "Water": -3},
    "卯": {"Wood": 5, "Fire": 3, "Earth": 1, "Metal": -1, "Water": -3},
    "辰": {"Wood": 3, "Fire": 1, "Earth": 5, "Metal": -1, "Water": -3},
    "巳": {"Fire": 5, "Earth": 3, "Wood": 1, "Metal": -1, "Water": -3},
    "午": {"Fire": 5, "Earth": 3, "Wood": 1, "Metal": -1, "Water": -3},
    "未": {"Fire": 3, "Earth": 5, "Wood": 1, "Metal": -1, "Water": -3},
    "申": {"Metal": 5, "Water": 3, "Earth": 1, "Wood": -1, "Fire": -3},
    "酉": {"Metal": 5, "Water": 3, "Earth": 1, "Wood": -1, "Fire": -3},
    "戌": {"Metal": 3, "Earth": 5, "Water": 1, "Wood": -1, "Fire": -3},
    "亥": {"Water": 5, "Wood": 3, "Metal": 1, "Earth": -1, "Fire": -3},
    "子": {"Water": 5, "Wood": 3, "Metal": 1, "Earth": -1, "Fire": -3},
    "丑": {"Water": 3, "Earth": 5, "Metal": 1, "Wood": -1, "Fire": -3},
}

_GEN = {"Wood": "Fire", "Fire": "Earth",
        "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
_CTRL = {"Wood": "Earth", "Earth": "Water",
         "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}

__all__ = ["season_strength", "apply_strength_corrections"]


def season_strength(month_branch: str, base_scores: Dict[str, int]) -> Dict[str, int]:
    """Apply seasonal modifier based on *month_branch* (月支)."""
    mod = _SEASON_TABLE[month_branch]
    return {e: base_scores[e] + mod.get(e, 0) for e in base_scores}


def apply_strength_corrections(scores: Dict[str, int]) -> Dict[str, int]:
    """一次生克迭代：被生 +1，被克 ‑1。"""
    corrected = scores.copy()
    for elem, val in scores.items():
        corrected[_GEN[elem]] += val // 4  # 生助权重，可按需调整
        corrected[_CTRL[elem]] -= val // 4  # 被克减分
    return corrected
