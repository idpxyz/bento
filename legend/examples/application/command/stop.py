"""站点相关的命令"""
from dataclasses import dataclass
from typing import Optional

from idp.framework.examples.domain.vo.contact import Contact
from idp.framework.examples.domain.vo.location import Location


@dataclass
class CreateStopCommand:
    """创建站点命令"""
    name: str
    address: str
    location: Location
    contact: Contact
    description: Optional[str] = None
    is_active: bool = True
    tenant_id: str = None


@dataclass
class UpdateStopCommand:
    """更新站点命令"""
    stop_id: str
    name: str
    address: str
    location: Location
    contact: Contact
    description: Optional[str] = None
    is_active: bool = True
    tenant_id: str = None


@dataclass
class UpdateStopLocationCommand:
    """更新站点位置命令"""
    stop_id: str
    location: Location
    tenant_id: str = None


@dataclass
class UpdateStopContactCommand:
    """更新站点联系人命令"""
    stop_id: str
    contact: Contact
    tenant_id: str = None


@dataclass
class DeactivateStopCommand:
    """停用站点命令"""
    stop_id: str
    tenant_id: str = None


@dataclass
class ActivateStopCommand:
    """激活站点命令"""
    stop_id: str
    tenant_id: str = None
