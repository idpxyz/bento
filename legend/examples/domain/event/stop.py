"""站点相关的领域事件"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from idp.framework.domain.event import DomainEvent
from idp.framework.examples.domain.vo.contact import Contact
from idp.framework.examples.domain.vo.location import Location


@dataclass
class StopCreated(DomainEvent):
    """站点创建事件"""
    stop_id: str
    name: str
    address: str
    location: Location
    contact: Optional[Contact]
    tenant_id: str
    timestamp: datetime = datetime.now()

    def get_payload(self) -> Dict[str, Any]:
        """获取事件负载

        Returns:
            Dict[str, Any]: 事件负载
        """
        return {
            "stop_id": self.stop_id,
            "name": self.name,
            "address": self.address,
            "location": {
                "latitude": self.location.latitude,
                "longitude": self.location.longitude
            } if self.location else None,
            "contact": {
                "name": self.contact.name,
                "phone": self.contact.phone,
                "email": self.contact.email
            } if self.contact else None,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class StopLocationUpdated(DomainEvent):
    """站点位置更新事件"""
    stop_id: str
    old_location: Location
    new_location: Location
    timestamp: datetime = datetime.now()

    def get_payload(self) -> Dict[str, Any]:
        """获取事件负载

        Returns:
            Dict[str, Any]: 事件负载
        """
        return {
            "stop_id": self.stop_id,
            "old_location": self.old_location.to_dict() if self.old_location else None,
            "new_location": self.new_location.to_dict() if self.new_location else None,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class StopContactUpdated(DomainEvent):
    """站点联系人更新事件"""
    stop_id: str
    old_contact: Optional[Contact]
    new_contact: Contact
    timestamp: datetime = datetime.now()

    def get_payload(self) -> Dict[str, Any]:
        """获取事件负载

        Returns:
            Dict[str, Any]: 事件负载
        """
        return {
            "stop_id": self.stop_id,
            "old_contact": self.old_contact.to_dict() if self.old_contact else None,
            "new_contact": self.new_contact.to_dict() if self.new_contact else None,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class StopDeactivated(DomainEvent):
    """站点停用事件"""
    stop_id: str
    timestamp: datetime = datetime.now()

    def get_payload(self) -> Dict[str, Any]:
        """获取事件负载

        Returns:
            Dict[str, Any]: 事件负载
        """
        return {
            "stop_id": self.stop_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class StopActivated(DomainEvent):
    """站点启用事件"""
    stop_id: str
    timestamp: datetime = datetime.now()

    def get_payload(self) -> Dict[str, Any]:
        """获取事件负载

        Returns:
            Dict[str, Any]: 事件负载
        """
        return {
            "stop_id": self.stop_id,
            "timestamp": self.timestamp.isoformat()
        }
