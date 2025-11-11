from __future__ import annotations

from .constants import GAN

# element & polarity tables ------------------------------------------------
_STEM_ELEMENT = {
    "甲": "Wood", "乙": "Wood", "丙": "Fire", "丁": "Fire", "戊": "Earth",
    "己": "Earth", "庚": "Metal", "辛": "Metal", "壬": "Water", "癸": "Water",
}
_STEM_POLARITY = {
    "甲": "Yang", "乙": "Yin", "丙": "Yang", "丁": "Yin", "戊": "Yang",
    "己": "Yin", "庚": "Yang", "辛": "Yin", "壬": "Yang", "癸": "Yin",
}

# Five‑element generation & control
_GEN = {"Wood": "Fire", "Fire": "Earth",
        "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
_CTRL = {"Wood": "Earth", "Earth": "Water",
         "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}
_REV_GEN = {v: k for k, v in _GEN.items()}
_REV_CTRL = {v: k for k, v in _CTRL.items()}

_TEN_GOD = {
    "比肩": "Friend", "劫财": "RobWealth", "食神": "EatingGod", "伤官": "HurtingOfficer",
    "偏财": "IndirectWealth", "正财": "DirectWealth", "七杀": "SevenKillings", "正官": "ProperOfficer",
    "偏印": "IndirectResource", "正印": "ProperResource",
}

__all__ = ["ten_god"]


def ten_god(day_stem: str, target_stem: str) -> str:
    """Return Ten‑God relationship between *day_stem* (日主) and *target_stem*."""
    if day_stem not in GAN or target_stem not in GAN:
        raise ValueError("Input must be heavenly stems (甲‑癸)")
    delem = _STEM_ELEMENT[day_stem]
    telem = _STEM_ELEMENT[target_stem]
    same_pol = _STEM_POLARITY[day_stem] == _STEM_POLARITY[target_stem]
    # 同一元素
    if telem == delem:
        return "比肩" if same_pol else "劫财"
    # DM produces target
    if _GEN[delem] == telem:
        return "食神" if same_pol else "伤官"
    # DM controls target
    if _CTRL[delem] == telem:
        return "偏财" if same_pol else "正财"
    # Target controls DM
    if _REV_CTRL[delem] == telem:
        return "七杀" if same_pol else "正官"
    # Target generates DM
    if _REV_GEN[delem] == telem:
        return "偏印" if same_pol else "正印"
    raise RuntimeError("Unexpected element relationship")
