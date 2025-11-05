from idp.framework.examples.domain.aggregate.route_plan import RoutePlan
from idp.framework.examples.infrastructure.persistence.po.route_plan import RoutePlanPO
from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


def create_route_plan_mapper():
    return (
        MapperBuilder.for_types(RoutePlan, RoutePlanPO)
        .map('id', 'id')
        .map('tenant_id', 'tenant_id')
        .map('name', 'name')
        .map('description', 'description')
        .map('status', 'status')
        .map('is_active', 'is_active')
        # stops 关系由仓储层单独处理
        .build()
    )
