"""应用服务基础模块

提供应用服务层的核心基类和工具。

组件说明：
- BaseQueryService: 查询服务基类，专注数据查询
- BaseApplicationService: 应用服务基类，协调查询和数据转换
- BaseAggregateQueryService: 聚合根查询服务基类
- BaseAggregateApplicationService: 聚合根应用服务基类

架构职责：
- QueryService: 专注查询逻辑，返回领域DTO
- ApplicationService: 协调服务，转换为API响应对象
- 通过泛型确保类型安全
- 提供统一的模式和扩展点
"""

from idp.framework.application.service.base_application_service import (
    BaseAggregateApplicationService,
    BaseApplicationService,
)
from idp.framework.application.service.base_query_service import (
    BaseAggregateQueryService,
    BaseQueryService,
)

__all__ = [
    # 查询服务基类
    "BaseQueryService",
    "BaseAggregateQueryService",
    # 应用服务基类
    "BaseApplicationService",
    "BaseAggregateApplicationService",
]
