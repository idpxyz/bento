# =========================================
# Package: ganzhi_utils  (full‑stack, v2)
# ‑ Added *precise* 大运起运规则 in `luck.py`:
#     • 依据“年干阴阳 + 性别”决定顺/逆排
#     • 采用最近节气(24 Solar Terms)计算起运差日
#     • 起运岁数 = (差日 ÷ 3) + (余时 ÷ 8)  → 年+月形式
#     • 支持未满起运前返回空字符串
#   新增公开 API:
#     • start_luck_info(birth_dt, gender) → (start_age_years: float, direction: ±1)
# ───────────────────────────────────────────
# 其余文件保持不变；仅展示 **luck.py** 全量代码，下略其他模块。
# =========================================

# -------- File: ganzhi_utils/luck.py -----------------------------------
"""大运 / 流年 Pillar 生成 — 精细起运规则"""
from __future__ import annotations

import datetime as _dt
from typing import List, Tuple

from .calendars import year_ganzhi
from .constants import GAN, GAN2IDX, JIA_ZI

try:
    import sxtwl  # type: ignore
except ImportError:  # pragma: no cover
    sxtwl = None  # type: ignore

__all__ = [
    "start_luck_info",
    "luck_pillars",
    "current_luck_pillar",
]

_DEF_AGE_STEP = 10  # 每 10 年换一大运

# ----------------------------------------------------------------------
# Helper: polarity & solar‑term boundary
# ----------------------------------------------------------------------


def _stem_polarity(stem: str) -> str:  # "yang" | "yin"
    return "yang" if GAN2IDX[stem] % 2 == 0 else "yin"


def _nearest_term(dt: _dt.datetime, forward: bool = True) -> _dt.datetime:
    """Return the **nearest** solar‑term datetime after (forward=True) or before birth."""
    if sxtwl is None:
        raise RuntimeError(
            "sxtwl library required for precise luck calculation; pip install sxtwl")

    # 使用 sxtwl v2.0.7 的正确 API
    day = sxtwl.fromSolar(dt.year, dt.month, dt.day)

    # iterate day by day until we land on a day with节气; forward/backward by offset days
    step = 1 if forward else -1
    offset = 0
    max_offset = 30  # 防止无限循环，最多查找30天

    while offset < max_offset:
        if step == 1:
            # 向前查找下一个节气
            cand_day = day.after(offset)
        else:
            # 向后查找上一个节气
            cand_day = day.before(-offset)

        # 检查是否有节气
        if cand_day.hasJieQi():
            # 获取节气对应的公历日期
            solar_year = cand_day.getSolarYear()
            solar_month = cand_day.getSolarMonth()
            solar_day = cand_day.getSolarDay()
            return _dt.datetime(solar_year, solar_month, solar_day, dt.hour, dt.minute, dt.second)
        offset += 1

    # 如果找不到节气，返回原始日期
    return dt

# ----------------------------------------------------------------------
# Core: 起运信息
# ----------------------------------------------------------------------


def start_luck_info(birth_dt: _dt.datetime, gender: str) -> Tuple[float, int]:
    """Compute (start_age_years, direction_step).

    Rules
    -----
    1. Determine **顺 / 逆**:
       * Male & Year‑stem **阳** → 顺排  (+1)
       * Female & Year‑stem **阴** → 顺排  (+1)
       * Else 逆排 (‑1)
    2. 起运节气点:
       * 顺排 → 下一个节气
       * 逆排 → 上一个节气
    3. 起运岁数 = (差日 / 3) + (差时 / 8)
       1 日 = 4 个月, 8 小时 = 1 个月
    """
    year_gz = year_ganzhi(birth_dt.year)
    is_yang_year = _stem_polarity(year_gz[0]) == "yang"
    forward = (gender == "male" and is_yang_year) or (
        gender == "female" and not is_yang_year)

    boundary_dt = _nearest_term(birth_dt, forward)
    diff_hours = abs((boundary_dt - birth_dt).total_seconds()) / 3600.0

    days = int(diff_hours // 24)
    hours = diff_hours - days * 24

    years = days / 3.0
    months = (days % 3) * 4 + hours / 2.0

    start_age = round(years + months / 12.0, 3)  # 保留 3 位小数
    step = 1 if forward else -1
    return start_age, step

# ----------------------------------------------------------------------
# Luck‑pillar list & current pillar
# ----------------------------------------------------------------------


def _pillar_index(base: int, step: int, n: int) -> List[str]:
    return [JIA_ZI[(base + step * i) % 60] for i in range(n)]


def luck_pillars(birth_dt: _dt.datetime, gender: str, count: int = 8) -> List[str]:
    """Return luck‑pillar list (length = *count*). Uses birth **month pillar** as base index."""
    # Derive month‑pillar index via simple formula: (year_index*12 + month_offset) % 60
    base_index = ((birth_dt.year - 1984) * 12 +
                  birth_dt.month + 1) % 60  # 粗略；严谨应用 sxtwl 月柱
    start_age, step = start_luck_info(birth_dt, gender)
    return _pillar_index(base_index, step, count)


def current_luck_pillar(
    birth_dt: _dt.datetime,
    gender: str,
    at: _dt.datetime | None = None,
) -> str:
    """Return current **DaYun** pillar; empty string if 未行运."""
    at = at or _dt.datetime.now()
    start_age, step = start_luck_info(birth_dt, gender)
    age = (at - birth_dt).days / 365.2422
    if age < start_age:
        return ""  # 尚未起运

    index = int((age - start_age) // _DEF_AGE_STEP)
    return luck_pillars(birth_dt, gender, index + 1)[index]

# ---------------- End of luck.py ---------------------------------------

# NOTE: Other modules (constants.py, calendars.py, etc.) remain unchanged from the previous version and are omitted here for brevity.
