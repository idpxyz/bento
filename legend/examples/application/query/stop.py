"""站点相关的查询"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GetStopQuery:
    """获取站点查询"""
    stop_id: str


@dataclass
class ListStopsQuery:
    """列出站点查询"""
    name: Optional[str] = None
    address: Optional[str] = None
    skip: int = 0
    limit: int = 10
