"""路线计划命令

定义路线计划相关的命令。
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CreateRoutePlanCommand:
    """创建路线计划命令"""
    stops: List[str]
    tenant_id: Optional[str] = None


@dataclass
class UpdateRoutePlanCommand:
    """更新路线计划命令"""
    id: str
    stops: List[str]
    tenant_id: Optional[str] = None


@dataclass
class ChangeRoutePlanStatusCommand:
    """更改路线计划状态命令"""
    id: str
    trigger: str
    reason: Optional[str] = None
    metadata: Optional[dict] = None
