# =========================================
# Package: ganzhi_utils
# A minimal, modular toolkit for Chinese Heavenly Stem / Earthly Branch
# (天干地支) computations: constants, calendrical conversion, four‑pillars
# generation, and common relational checks (六合、三合、冲等).
#
# The code is 100 % typed, ready for unit‑testing, and free of
# third‑party dependencies except for the optional `sxtwl` library
# (寿星天文历). If `sxtwl` is not installed the advanced
# `four_pillars_from_datetime` helper raises `RuntimeError`, while
# year‑pillar calculation still works via a pure‑Python fallback.
#
# ├── ganzhi_utils/
# │   ├── __init__.py
# │   ├── constants.py
# │   ├── calendars.py
# │   ├── pillars.py
# │   ├── relations.py
# │   ├── scoring.py
# │   └── py.typed          # marker for PEP 561 typing support
# └── README.md             # (optional) usage guide
# =========================================

# -------- File: ganzhi_utils/__init__.py -------------------------------
"""Top‑level package exports for *ganzhi_utils*.

>>> import datetime as dt
>>> from ganzhi_utils import FourPillars
>>> print(FourPillars.from_datetime(dt.datetime(2025, 7, 31, 6)))
甲辰 丁未 乙巳 戊辰
"""
from __future__ import annotations

from .calendars import four_pillars_from_datetime, year_ganzhi
from .constants import GAN, GAN2IDX, JIA_ZI, NAYIN_MAP, ZHI, ZHI2IDX
from .luck import current_luck_pillar, start_luck_info
from .pillars import FourPillars
from .relations import (
    in_sanhe,
    is_chong,
    is_hai,
    is_liuhe,
    is_po,
    is_xing,
    relation_type,
)
from .scoring import five_element_score
from .strength import apply_strength_corrections, season_strength
from .tengods import ten_god

__all__: list[str] = [
    # constants
    "GAN",
    "ZHI",
    "GAN2IDX",
    "ZHI2IDX",
    "JIA_ZI",
    "NAYIN_MAP",
    # calendrical helpers
    "year_ganzhi",
    "four_pillars_from_datetime",
    # core dataclass
    "FourPillars",
    # relation utilities
    "is_liuhe",
    "is_chong",
    "in_sanhe",
    "is_xing",
    "is_hai",
    "is_po",
    "relation_type",
    # ten‑god
    "ten_god",
    # scoring helpers
    "five_element_score",
    # hidden helpers
    "hidden_five_element_score",
    "hidden_stems",
    "season_strength",
    "apply_strength_corrections",
    # luck helpers
    "start_luck_info"
    "luck_pillars",
    "current_luck_pillar",
    # useful helpers
    "useful_god",
    # advice helpers
    "fengshui_advice",
]
