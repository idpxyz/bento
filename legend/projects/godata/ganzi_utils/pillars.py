# -*- coding: utf‑8 -*-
"""Dataclass wrapper for the **Four Pillars of Destiny** (四柱八字)."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .calendars import four_pillars_from_datetime
from .relations import is_liuhe


@dataclass(frozen=True, slots=True)
class FourPillars:
    """Immutable representation of the four pillars."""

    year: str
    month: str
    day: str
    hour: str

    # ------------------------------------------------------------------
    # Constructors & helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_datetime(cls, dt: _dt.datetime) -> "FourPillars":
        """Instantiate from a *datetime* (true solar time)."""
        y, m, d, h = four_pillars_from_datetime(dt)
        return cls(y, m, d, h)

    def as_tuple(self) -> tuple[str, str, str, str]:
        """Return (year, month, day, hour)."""
        return self.year, self.month, self.day, self.hour

    # ------------------------------------------------------------------
    # Quick relation checks
    # ------------------------------------------------------------------
    def is_love_match(self, spouse_hour_branch: str) -> bool:
        """Check if *self.hour* branch 六合 with *spouse_hour_branch*."""
        return is_liuhe(self.hour[1], spouse_hour_branch)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------
    def __str__(self) -> str:  # pragma: no cover
        return " ".join(self.as_tuple())
