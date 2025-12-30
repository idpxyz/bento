# DI 模块合并优化

## 📋 问题

**发现**: 项目中存在两个相似的依赖注入文件：
- `shared/infrastructure/dependencies.py` - 提供数据库依赖
- `shared/infrastructure/di.py` - 提供 Handler 依赖注入

**问题**:
- ⚠️ 职责重叠，容易混淆
- ⚠️ `di.py` 只有 3 行实际代码
- ⚠️ 不必要的文件分离

---

## ✅ 解决方案

### 合并策略

将 `di.py` 的功能合并到 `dependencies.py` 中，统一管理所有依赖注入。

### 实施步骤

#### 1. 在 `dependencies.py` 中添加 `handler_dependency`

```python
# shared/infrastructure/dependencies.py

# Create handler_dependency using Bento Framework's factory
handler_dependency = create_handler_dependency(get_uow)

# ==================== Public API ====================
# This module exports:
# - get_db_session: Get database session
# - get_uow: Get Unit of Work
# - handler_dependency: Inject CQRS handlers
```

#### 2. 更新所有导入

**修改前**:
```python
from shared.infrastructure.di import handler_dependency
```

**修改后**:
```python
from shared.infrastructure.dependencies import handler_dependency
```

**影响的文件**:
- `contexts/identity/interfaces/user_api.py`
- `contexts/ordering/interfaces/order_api.py`
- `contexts/catalog/interfaces/product_api.py`
- `contexts/catalog/interfaces/category_api.py`

#### 3. 删除冗余文件

```bash
rm shared/infrastructure/di.py
```

---

## 📊 对比分析

### 修改前

```
shared/infrastructure/
├── dependencies.py  (提供 get_db_session, get_uow)
└── di.py           (提供 handler_dependency)
                    ↑ 只有 3 行代码，职责重叠
```

**问题**:
- 两个文件，职责不清晰
- 开发者需要记住从哪个文件导入什么
- 维护成本高

### 修改后

```
shared/infrastructure/
└── dependencies.py  (提供所有依赖注入)
    ├── get_db_session      # 数据库会话
    ├── get_uow            # Unit of Work
    └── handler_dependency  # CQRS Handler 注入
```

**优势**:
- ✅ 单一文件，职责清晰
- ✅ 统一的导入路径
- ✅ 更易维护

---

## 📝 新的使用方式

### 统一导入

```python
from shared.infrastructure.dependencies import (
    get_db_session,      # 如果需要直接访问数据库
    get_uow,            # 如果需要 UnitOfWork
    handler_dependency,  # 如果需要注入 Handler（推荐）
)
```

### 三种使用模式

#### 1. 直接数据库访问（不推荐）

```python
@router.get("/items")
async def get_items(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Item))
    return result.scalars().all()
```

#### 2. Unit of Work 模式

```python
@router.post("/items")
async def create_item(uow: SQLAlchemyUnitOfWork = Depends(get_uow)):
    async with uow:
        repo = uow.repository(Item)
        item = Item.create(...)
        await repo.save(item)
        await uow.commit()
```

#### 3. CQRS Handler 注入（✅ 推荐）

```python
@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
):
    command = CreateOrderCommand(...)
    return await handler.execute(command)
```

---

## 🎯 优化效果

| 指标 | 修改前 | 修改后 | 改善 |
|------|--------|--------|------|
| **文件数量** | 2 个 | 1 个 | -50% |
| **代码行数** | 分散 | 集中 | 更清晰 |
| **导入路径** | 2 个 | 1 个 | 更统一 |
| **维护成本** | 高 | 低 | 降低 |
| **认知负担** | 需要记住分离 | 单一来源 | 降低 |

---

## 📚 设计原则

### 为什么合并是正确的？

1. **单一职责原则**: `dependencies.py` 负责所有依赖注入
2. **最小惊讶原则**: 开发者只需要记住一个导入路径
3. **DRY 原则**: 避免不必要的文件分离
4. **简单性**: 3 行代码不值得单独一个文件

### 何时应该分离文件？

只有在以下情况下才应该分离：
- ✅ 文件超过 500 行
- ✅ 有明确不同的职责域
- ✅ 需要独立测试
- ✅ 有不同的依赖关系

`di.py` 不满足任何一个条件，因此合并是正确的。

---

## ✅ 验证

### 检查导入

```bash
# 确认没有文件还在使用旧的导入
grep -r "from shared.infrastructure.di import" .
# 应该返回空结果
```

### 运行测试

```bash
# 确保所有测试通过
pytest tests/
```

### 启动应用

```bash
# 确保应用正常启动
python main.py
```

---

## 📖 相关文档

- **依赖注入**: `shared/infrastructure/dependencies.py`
- **数据库优化**: `docs/DATABASE_ENGINE_SOLUTION.md`
- **审查报告**: `docs/BENTO_FRAMEWORK_ALIGNMENT_AUDIT.md`

---

## ✨ 总结

**优化类型**: 代码结构简化

**影响范围**:
- ✅ 删除 1 个冗余文件
- ✅ 更新 4 个导入引用
- ✅ 统一依赖注入入口

**收益**:
- ✅ 代码更清晰
- ✅ 维护更简单
- ✅ 认知负担降低

**状态**: ✅ 已完成

---

**优化人**: Cascade AI
**优化日期**: 2025-12-29
**验证状态**: ✅ 已验证
