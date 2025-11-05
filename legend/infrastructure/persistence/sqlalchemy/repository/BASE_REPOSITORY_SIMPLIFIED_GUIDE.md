# BaseRepository 简化指南

## 🎯 简化目标

通过重构BaseRepository，我们实现了以下目标：

1. **消除重复代码** - 统一查询入口，减少方法冗余
2. **简化实现** - 所有查询方法都委托给核心方法
3. **提高可维护性** - 清晰的职责分离和代码结构

## 📊 简化前后对比

### 简化前的问题

```python
# 重复的计数逻辑
async def exists_by_spec(self, spec: Specification[T]) -> bool:
    spec = copy.deepcopy(spec)
    spec.page = None
    spec.fields = []
    spec.sorts = []
    spec.includes = []
    spec.group_by = []
    spec.having = []
    spec.statistics = [Statistic(field="id", function=StatisticalFunction.COUNT)]
    
    results = await self.query_by_spec(spec)
    if not results:
        return False
    
    count_value = results[0]
    if isinstance(count_value, (int, float)):
        return count_value > 0
    elif hasattr(count_value, 'count'):
        return count_value.count > 0
    else:
        try:
            return int(count_value) > 0
        except (TypeError, ValueError):
            return False

async def exists_by_json(self, json_spec: Dict[str, Any]) -> bool:
    # 重复的计数逻辑...
    json_spec = copy.deepcopy(json_spec)
    json_spec["page"] = None
    json_spec["fields"] = []
    # ... 更多重复代码

async def count_by_spec(self, spec: Specification[T]) -> int:
    # 类似的重复逻辑...
    count_spec = copy.deepcopy(spec)
    count_spec.page = None
    # ... 更多重复代码
```

### 简化后的实现

```python
# 统一的查询入口
async def query_by_spec(self, spec: Specification[T]) -> List[T]:
    """使用规范查询实体 - 统一的查询入口"""
    # 核心查询逻辑，只实现一次
    pass

# 便捷方法委托给核心方法
async def find_one_by_spec(self, spec: Specification[T]) -> Optional[T]:
    spec.page = Page(offset=0, limit=1)
    results = await self.query_by_spec(spec)
    return results[0] if results else None

async def count_by_spec(self, spec: Specification[T]) -> int:
    count_spec = self._build_count_spec(spec)
    results = await self.query_by_spec(count_spec)
    return self._extract_count(results)

async def exists_by_spec(self, spec: Specification[T]) -> bool:
    return await self.count_by_spec(spec) > 0

# JSON方法委托给Specification方法
async def find_one_by_json(self, json_spec: Dict[str, Any]) -> Optional[T]:
    spec = self._build_spec_from_json(json_spec)
    return await self.find_one_by_spec(spec)

async def count_by_json(self, json_spec: Dict[str, Any]) -> int:
    spec = self._build_spec_from_json(json_spec)
    return await self.count_by_spec(spec)

async def exists_by_json(self, json_spec: Dict[str, Any]) -> bool:
    spec = self._build_spec_from_json(json_spec)
    return await self.exists_by_spec(spec)
```

## 🏗️ 新的架构设计

### 核心设计原则

1. **统一的查询入口** - `query_by_spec` 是唯一的查询实现
2. **委托模式** - 所有其他方法都委托给核心方法
3. **辅助方法** - 提取公共逻辑到辅助方法

### 方法层次结构

```
BaseRepository
├── 核心CRUD操作
│   ├── create()
│   ├── get_by_id()
│   ├── update()
│   └── delete()
├── 核心查询方法
│   └── query_by_spec()  ← 统一的查询入口
├── 便捷查询方法（委托给核心方法）
│   ├── find_one_by_spec()
│   ├── find_all_by_spec()
│   ├── count_by_spec()
│   └── exists_by_spec()
├── JSON规范查询方法（委托给便捷方法）
│   ├── query_by_json()
│   ├── find_one_by_json()
│   ├── find_all_by_json()
│   ├── count_by_json()
│   └── exists_by_json()
├── 分页查询方法
│   ├── find_page_by_spec()
│   └── find_page_by_json()
├── 批量操作
│   ├── batch_create()
│   ├── batch_update()
│   └── batch_delete()
└── 辅助方法
    ├── exists()
    ├── _build_count_spec()
    └── _extract_count()
```

## 💡 使用示例

### 1. 基础查询

```python
# 使用Specification查询
spec = (SpecificationBuilder()
    .filter("is_active", True)
    .filter("tenant_id", "tenant_001")
    .build())

# 查询所有
entities = await repository.query_by_spec(spec)

# 查询单个
entity = await repository.find_one_by_spec(spec)

# 统计数量
count = await repository.count_by_spec(spec)

# 检查存在性
exists = await repository.exists_by_spec(spec)
```

### 2. JSON规范查询

```python
# JSON规范
json_spec = {
    "filters": [
        {"field": "is_active", "operator": "equals", "value": True},
        {"field": "tenant_id", "operator": "equals", "value": "tenant_001"}
    ],
    "sorts": [{"field": "created_at", "direction": "desc"}]
}

# 委托给Specification方法
entities = await repository.query_by_json(json_spec)
entity = await repository.find_one_by_json(json_spec)
count = await repository.count_by_json(json_spec)
exists = await repository.exists_by_json(json_spec)
```

### 3. 分页查询

```python
# 分页参数
page_params = PageParams(page=1, page_size=20)

# 使用Specification分页
result = await repository.find_page_by_spec(spec, page_params)

# 使用JSON规范分页
result = await repository.find_page_by_json(json_spec, page_params)
```

## 🔧 辅助方法

### 1. 构建计数规范

```python
def _build_count_spec(self, spec: Specification[T]) -> Specification[T]:
    """构建计数查询规范"""
    count_spec = copy.deepcopy(spec)
    count_spec.page = None
    count_spec.fields = []
    count_spec.sorts = []
    count_spec.includes = []
    count_spec.group_by = []
    count_spec.having = []
    count_spec.statistics = [
        Statistic(field="id", function=StatisticalFunction.COUNT)
    ]
    return count_spec
```

### 2. 提取计数值

```python
def _extract_count(self, results: List[Any]) -> int:
    """从查询结果中提取计数值"""
    if not results:
        return 0
    
    count_value = results[0]
    if isinstance(count_value, (int, float)):
        return int(count_value)
    elif hasattr(count_value, 'count'):
        return count_value.count
    else:
        try:
            return int(count_value)
        except (TypeError, ValueError):
            return 0
```

## 📈 优化效果

### 1. 代码行数减少

- **简化前**: ~700行代码
- **简化后**: ~500行代码
- **减少**: ~30% 的代码量

### 2. 重复代码消除

- **简化前**: 6个方法包含重复的计数逻辑
- **简化后**: 1个核心方法 + 2个辅助方法
- **减少**: ~80% 的重复代码

### 3. 维护性提升

- **单一职责**: 每个方法职责明确
- **委托模式**: 清晰的调用链
- **辅助方法**: 公共逻辑复用

### 4. 测试简化

```python
# 只需要测试核心方法
async def test_query_by_spec():
    # 测试核心查询逻辑
    
async def test_delegation_methods():
    # 测试委托方法（简单测试）
    
async def test_helper_methods():
    # 测试辅助方法
```

## 🚀 最佳实践

### 1. 优先使用Specification

```python
# ✅ 推荐：使用SpecificationBuilder
spec = (SpecificationBuilder()
    .filter("status", "active")
    .add_sort("created_at", direction=SortDirection.DESC)
    .build())
result = await repository.query_by_spec(spec)

# ❌ 避免：直接使用JSON规范
json_spec = {
    "filters": [{"field": "status", "operator": "equals", "value": "active"}],
    "sorts": [{"field": "created_at", "direction": "desc"}]
}
result = await repository.query_by_json(json_spec)
```

### 2. 创建领域特定的Specification

```python
class WarehouseSpecifications:
    """仓库领域查询规范"""
    
    @staticmethod
    def active_warehouses(tenant_id: Optional[str] = None) -> Specification[Warehouse]:
        builder = SpecificationBuilder().filter("is_operational", True)
        if tenant_id:
            builder.filter("tenant_id", tenant_id)
        return builder.build()
    
    @staticmethod
    def by_tenant_and_code(tenant_id: str, code: str) -> Specification[Warehouse]:
        return (SpecificationBuilder()
            .filter("tenant_id", tenant_id)
            .filter("code", code)
            .build())
```

### 3. 在QueryService中使用

```python
class WarehouseQueryService:
    async def find_active_warehouses(self, tenant_id: Optional[str] = None) -> List[WarehouseDTO]:
        spec = WarehouseSpecifications.active_warehouses(tenant_id)
        entities = await self.repository.query_by_spec(spec)
        return [self.entity_to_dto(entity) for entity in entities]
    
    async def find_by_tenant_and_code(self, tenant_id: str, code: str) -> Optional[WarehouseDTO]:
        spec = WarehouseSpecifications.by_tenant_and_code(tenant_id, code)
        entity = await self.repository.find_one_by_spec(spec)
        return self.entity_to_dto(entity) if entity else None
```

## 🎉 总结

通过这次简化，我们实现了：

1. **代码质量提升** - 消除重复，提高可维护性
2. **架构更清晰** - 统一的查询入口，清晰的委托链
3. **使用更简单** - 减少学习成本，提高开发效率
4. **扩展性更好** - 新增查询方法更容易

这个简化版本保持了所有原有功能，同时大大提高了代码质量和可维护性。 