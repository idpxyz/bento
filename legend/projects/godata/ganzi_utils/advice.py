"""根据用神输出颜色 / 方位 / 元素调理建议"""
from __future__ import annotations

_ADVICE = {
    "Wood": {"color": "green", "direction": "east", "element": "木"},
    "Fire": {"color": "red", "direction": "south", "element": "火"},
    "Earth": {"color": "yellow", "direction": "center", "element": "土"},
    "Metal": {"color": "white", "direction": "west", "element": "金"},
    "Water": {"color": "black", "direction": "north", "element": "水"},
}

__all__ = ["fengshui_advice"]


def fengshui_advice(useful_element: str) -> dict[str, str]:
    return _ADVICE[useful_element]
