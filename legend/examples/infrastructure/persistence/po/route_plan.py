"""Route Plan 持久化对象

定义路线计划的数据库映射。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from idp.framework.examples.domain.aggregate.route_plan import RoutePlan
from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.infrastructure.persistence.po.stop import route_plan_stop
from idp.framework.infrastructure.persistence.sqlalchemy.po import FullFeatureBasePO


class RoutePlanPO(FullFeatureBasePO):
    """路线计划持久化对象"""

    __tablename__ = "route_plan"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # 定义与站点的多对多关系
    stops = relationship(
        "StopPO",
        secondary=route_plan_stop,
        back_populates="route_plans",
        lazy="joined",
        primaryjoin="and_(RoutePlanPO.id==route_plan_stop.c.route_plan_id, RoutePlanPO.deleted_at==None)",
        secondaryjoin="and_(StopPO.id==route_plan_stop.c.stop_id, StopPO.deleted_at==None)"
    )
