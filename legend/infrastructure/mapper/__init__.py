"""映射器模块。

提供对象映射功能，支持领域对象与各种数据对象之间的转换。

映射器架构设计原则：
1. 清晰的职责分离：每个映射器负责特定类型之间的转换，遵循单一职责原则。
2. 组合优于继承：使用组合模式构建映射策略，而不是复杂的继承层次。
3. 接口与实现分离：通过接口定义映射器的行为，实现与接口分离。
4. 保护领域边界：映射器作为防腐层，保护领域模型不受外部数据结构的影响。
5. 可测试性：映射器设计便于单元测试，支持模拟和替换。

核心功能：
1. 自动映射同名属性
2. 支持自定义映射函数
3. 支持嵌套对象映射
4. 中央注册表管理映射器
5. 类型安全的泛型接口

使用示例：
```python
# 创建映射器构建器
builder = MapperBuilder()

# 配置映射器
mapper = (builder
    .for_types(User, UserPO)
    .auto_map()  # 自动映射同名属性
    .map("firstName", "first_name")  # 显式映射不同名属性
    .map_custom("full_name", lambda user: f"{user.firstName} {user.lastName}")  # 自定义映射函数
    .map_nested("address", "address", address_mapper)  # 嵌套对象映射
    .map_collection("orders", "orders", order_mapper)  # 集合映射
    .build())

# 使用映射器
user = User(id="1", firstName="John", lastName="Doe")
user_po = mapper.map_to_target(user)

# 反向映射
user = mapper.map_to_source(user_po)
```

主要组件：
1. 核心接口 (core/interfaces.py)
   - Mapper: 基础映射器接口
   - BidirectionalMapper: 双向映射器接口
   - ConfigurableMapper: 可配置映射器接口
   - MapperBuilder: 映射器构建器接口

2. 映射策略 (core/strategies.py)
   - AutoMappingStrategy: 自动映射策略
   - ExplicitMappingStrategy: 显式映射策略
   - CompositeMappingStrategy: 组合映射策略

3. 映射器实现 (core/mapper.py)
   - GenericMapper: 通用映射器实现
   - MapperBuilder: 映射器构建器实现

4. 特定映射器
   - POMapper: 持久化对象映射器
   - DTOMapper: 数据传输对象映射器
   - VOMapper: 值对象映射器

5. 注册表 (registry/)
   - MapperRegistry: 映射器注册表接口
   - POMapperRegistry: 持久化对象映射器注册表
   - DTOMapperRegistry: 数据传输对象映射器注册表
   - VOMapperRegistry: 值对象映射器注册表
"""

# 导出核心接口
from .core.interfaces import (
    Mapper, 
    BidirectionalMapper, 
    ConfigurableMapper, 
    NestedMapper,
    IMapperBuilder,
    MapperRegistry
)

# 导出映射器实现
from .core.mapper import GenericMapper, MapperBuilder


# 导出特定映射器
from .po import POMapper
from .dto import DTOMapper
from .vo import VOMapper

# 导出注册表
from .registry import (
    MapperRegistryImpl,
    POMapperRegistry,
    DTOMapperRegistry,
    VOMapperRegistry,
    po_mapper_registry,
    dto_mapper_registry,
    vo_mapper_registry
)

# Export the renamed interface and the implementation alias
__all__ = [
    # 核心接口
    'Mapper',
    'BidirectionalMapper',
    'ConfigurableMapper',
    'NestedMapper',
    'IMapperBuilder',  # Interface is now IMapperBuilder
    'MapperRegistry',
    
    # 映射器实现
    'GenericMapper',
    'MapperBuilder',   # Implementation is now directly accessible as MapperBuilder
    
    # 特定映射器
    'POMapper',
    'DTOMapper',
    'VOMapper',
    
    # 注册表
    'MapperRegistryImpl',
    'POMapperRegistry',
    'DTOMapperRegistry',
    'VOMapperRegistry',
    'po_mapper_registry',
    'dto_mapper_registry',
    'vo_mapper_registry',
    
    # 工厂函数
    'create_mapper_builder',
]

def create_mapper_builder() -> MapperBuilder:
    """
    创建映射器构建器
    
    Returns:
        MapperBuilder: 映射器构建器实例
    """
    return MapperBuilder() 