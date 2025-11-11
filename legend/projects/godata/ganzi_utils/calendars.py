# -*- coding: utf‑8 -*-
"""Calendrical conversion helpers (干支 ⇆ 公历日期).

If *sxtwl* (寿星天文历) is available it is used for high‑precision
computations (立春、真太阳时). Otherwise only a simple **year‑pillar**
helper is provided.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Tuple

from .constants import GAN, ZHI
from .relations import is_liuhe

try:
    import sxtwl  # type: ignore
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "ganzhi_utils requires sxtwl>=2.0 — install via `pip install sxtwl`.") from e

_BASE_YEAR = 1984  # 甲子年 index 0

# ----------------------------------------------------------------------
# Internal helper
# ----------------------------------------------------------------------


def _get_day(y: int, m: int, d: int):
    """Return a *Day* object from sxtwl v2."""
    return sxtwl.fromSolar(y, m, d)  # type: ignore[attr-defined]

# ----------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------


def year_ganzhi(year: int, *, li_chun_based: bool = True) -> str:
    offset = (year - _BASE_YEAR) % 60
    return GAN[offset % 10] + ZHI[offset % 12]


def four_pillars_from_datetime(dt: _dt.datetime) -> Tuple[str, str, str, str]:
    day = _get_day(dt.year, dt.month, dt.day)

    y_gz = day.getYearGZ()   # type: ignore[attr-defined]
    m_gz = day.getMonthGZ()  # type: ignore[attr-defined]
    d_gz = day.getDayGZ()        # type: ignore[attr-defined]
    h_gz = day.getHourGZ(dt.hour)  # type: ignore[attr-defined]

    return (
        GAN[y_gz.tg] + ZHI[y_gz.dz],
        GAN[m_gz.tg] + ZHI[m_gz.dz],
        GAN[d_gz.tg] + ZHI[d_gz.dz],
        GAN[h_gz.tg] + ZHI[h_gz.dz],
    )


# -------- File: ganzhi_utils/pillars.py --------------------------------


@dataclass(frozen=True, slots=True)
class FourPillars:
    year: str
    month: str
    day: str
    hour: str

    @classmethod
    def from_datetime(cls, dt: _dt.datetime) -> "FourPillars":
        return cls(*four_pillars_from_datetime(dt))

    def as_tuple(self):
        return self.year, self.month, self.day, self.hour

    def is_love_match(self, spouse_branch: str):
        return is_liuhe(self.hour[1], spouse_branch)

    def __str__(self):  # pragma: no cover
        return " ".join(self.as_tuple())
