"""站点持久化对象

定义站点的数据库映射。
"""
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.domain.vo.contact import Contact
from idp.framework.examples.domain.vo.location import Location
from idp.framework.infrastructure.persistence.sqlalchemy.po import FullFeatureBasePO

# 定义关联表
route_plan_stop = Table(
    'route_plan_stop',
    FullFeatureBasePO.metadata,
    Column('route_plan_id', String(36), ForeignKey(
        'route_plan.id'), primary_key=True),
    Column('stop_id', String(36), ForeignKey('stop.id'), primary_key=True),
    Column('sequence', Integer, nullable=False, comment="站点顺序"),
    Column('tenant_id', String(36), nullable=False, comment="租户ID"),
    Column('created_at', DateTime, nullable=False,
           server_default=func.now(), comment="创建时间"),
    Column('updated_at', DateTime, nullable=False,
           server_default=func.now(), onupdate=func.now(), comment="更新时间"),
    Column('created_by', String(36), nullable=True, comment="创建人"),
    Column('updated_by', String(36), nullable=True, comment="更新人"),
    Column('version', Integer, nullable=False,
           server_default='0', comment="版本号"),
    Column('is_deleted', Boolean, nullable=False,
           server_default='false', comment="是否删除")
)


class StopPO(FullFeatureBasePO):
    """站点持久化对象"""

    __tablename__ = "stop"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    contact_name: Mapped[Optional[str]] = mapped_column(String(50))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    contact_email: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)

    # 定义与路线计划的多对多关系
    route_plans = relationship(
        "RoutePlanPO",
        secondary=route_plan_stop,
        back_populates="stops",
        lazy="selectin",
        primaryjoin="and_(StopPO.id==route_plan_stop.c.stop_id, StopPO.deleted_at==None)",
        secondaryjoin="and_(RoutePlanPO.id==route_plan_stop.c.route_plan_id, RoutePlanPO.deleted_at==None)"
    )
