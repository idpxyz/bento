"""应用层映射器模块

提供应用层统一的 Entity → DTO 映射器架构：
- ApplicationMapper: 映射器接口
- BaseApplicationMapper: 基础映射器实现
- PydanticApplicationMapper: Pydantic 优化映射器
- create_pydantic_mapper: 便捷工厂函数

设计目标：
- 统一应用层映射标准
- 简化 QueryService 实现
- 提供类型安全的映射接口
- 支持多种映射策略

使用示例：
```python
from idp.framework.application.mapper import create_pydantic_mapper

# 创建映射器
mapper = create_pydantic_mapper(OptionCategory, OptionCategoryDTO)

# 使用映射器
dto = mapper.map_entity_to_dto(entity)
dtos = mapper.map_entities_to_dtos(entities)
```
"""

from .base import (
    ApplicationMapper,
    BaseApplicationMapper,
    EntityToDTOMapper,
    PydanticApplicationMapper,
    create_pydantic_mapper,
)

__all__ = [
    # 核心接口
    'ApplicationMapper',
    'EntityToDTOMapper',  # 类型别名

    # 基础实现
    'BaseApplicationMapper',
    'PydanticApplicationMapper',

    # 工厂函数
    'create_pydantic_mapper',
]
