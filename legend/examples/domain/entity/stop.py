"""站点实体"""
from dataclasses import dataclass, field
from typing import List, Optional

from idp.framework.domain.base import BaseEntity
from idp.framework.examples.domain.event.stop import (
    StopActivated,
    StopContactUpdated,
    StopCreated,
    StopDeactivated,
    StopLocationUpdated,
)
from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.domain.vo.contact import Contact
from idp.framework.examples.domain.vo.location import Location


@dataclass
class Stop(BaseEntity):
    """站点实体"""

    name: str
    address: str
    location: Optional[Location] = None
    contact: Optional[Contact] = None
    description: Optional[str] = None
    is_active: bool = True
    tenant_id: str = field(init=False)
    events: List[object] = field(default_factory=list, init=False)
    id_generator: IdGenerator = field(init=False)
    id: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        """初始化后处理"""
        # 初始化事件列表
        if not hasattr(self, 'events'):
            self.events = []

    @classmethod
    def create(
        cls,
        name: str,
        address: str,
        location: Optional[Location] = None,
        contact: Optional[Contact] = None,
        description: Optional[str] = None,
        tenant_id: str = None,
        id_generator: IdGenerator = None,
    ) -> "Stop":
        """创建站点

        Args:
            name: 站点名称
            address: 站点地址
            location: 站点位置
            contact: 站点联系人
            description: 站点描述
            tenant_id: 租户ID
            id_generator: ID生成器

        Returns:
            Stop: 站点实体
        """
        stop = cls(
            name=name,
            address=address,
            location=location,
            contact=contact,
            description=description,
        )
        # 设置非初始化字段
        stop.tenant_id = tenant_id
        stop.id_generator = id_generator
        stop.id = stop.id_generator.generate()

        # 验证和事件处理
        stop._validate()
        stop.events.append(
            StopCreated(
                stop_id=stop.id,
                name=stop.name,
                address=stop.address,
                location=stop.location,
                contact=stop.contact,
                tenant_id=stop.tenant_id,
            )
        )
        return stop

    def _validate(self):
        """验证站点属性"""
        if not self.name:
            raise ValueError("站点名称不能为空")
        if not self.address:
            raise ValueError("站点地址不能为空")
        if not self.tenant_id:
            raise ValueError("租户ID不能为空")

    def update_location(self, location: Location):
        """更新站点位置

        Args:
            location: 站点位置

        Returns:
            Stop: 更新后的站点
        """
        old_location = self.location
        self.location = location
        self.events.append(
            StopLocationUpdated(
                stop_id=self.id,
                old_location=old_location,
                new_location=location,
            )
        )
        return self

    def update_contact(self, contact: Contact):
        """更新站点联系人

        Args:
            contact: 站点联系人

        Returns:
            Stop: 更新后的站点
        """
        old_contact = self.contact
        self.contact = contact
        self.events.append(
            StopContactUpdated(
                stop_id=self.id,
                old_contact=old_contact,
                new_contact=contact,
            )
        )
        return self

    def deactivate(self):
        """停用站点"""
        if not self.is_active:
            return
        self.is_active = False
        self.events.append(StopDeactivated(stop_id=self.id))

    def activate(self):
        """启用站点"""
        if self.is_active:
            return
        self.is_active = True
        self.events.append(StopActivated(stop_id=self.id))
