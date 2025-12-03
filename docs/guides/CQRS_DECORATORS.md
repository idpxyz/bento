# CQRS 装饰器使用指南

## 📋 概述

Bento Framework 提供了 `@command_handler` 和 `@query_handler` 装饰器，用于简化 CQRS Handler 的注册和使用。

## 🎯 装饰器功能

### 1. `@command_handler` - Command Handler 装饰器

**用途**：标记和注册 Command Handler（写操作）

**功能**：
- ✅ 自动注册到全局注册表
- ✅ 添加元数据标记（`handler_type = "command"`）
- ✅ 验证类继承自 `CommandHandler`
- ✅ 支持依赖注入框架集成

### 2. `@query_handler` - Query Handler 装饰器

**用途**：标记和注册 Query Handler（读操作）

**功能**：
- ✅ 自动注册到全局注册表
- ✅ 添加元数据标记（`handler_type = "query"`）
- ✅ 验证类继承自 `QueryHandler`
- ✅ 支持依赖注入框架集成

---

## 🚀 基础使用

### Before（无装饰器）

```python
# ❌ 需要手动管理依赖注入

# 1. Handler 定义
class CreateProductHandler(CommandHandler[CreateProductCommand, str]):
    async def handle(self, command):
        ...

# 2. FastAPI 路由（需要手动创建 DI 函数）
async def get_create_product_handler(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> CreateProductHandler:
    """手动 DI 函数"""
    return CreateProductHandler(uow)

@router.post("/products")
async def create_product(
    request: CreateProductRequest,
    handler: Annotated[CreateProductHandler, Depends(get_create_product_handler)],
):
    command = CreateProductCommand(...)
    return await handler.execute(command)
```

**问题**：
- ❌ 每个 Handler 都要写一个 DI 函数
- ❌ 样板代码太多
- ❌ 难以统一管理

---

### After（使用装饰器）

```python
# ✅ 装饰器自动注册，代码简洁

# 1. Handler 定义（添加装饰器）
from bento.application import command_handler, CommandHandler

@command_handler
class CreateProductHandler(CommandHandler[CreateProductCommand, str]):
    """自动注册的 Command Handler"""
    
    async def handle(self, command):
        product = Product.create(command.name, command.price)
        repo = self.uow.repository(Product)
        await repo.save(product)
        return str(product.id)

# 2. FastAPI 路由（简化 DI）
from shared.dependencies import get_handler  # 统一的 Handler 工厂

@router.post("/products")
async def create_product(
    request: CreateProductRequest,
    handler: Annotated[CreateProductHandler, Depends(get_handler)],
):
    command = CreateProductCommand(...)
    return await handler.execute(command)
```

**优势**：
- ✅ 无需手动 DI 函数
- ✅ 自动注册到全局表
- ✅ 代码简洁易维护

---

## 📐 完整示例

### 示例 1：Command Handler（写操作）

```python
from dataclasses import dataclass
from bento.application import command_handler, CommandHandler
from bento.application.ports.uow import UnitOfWork
from bento.core.ids import ID

# 1. 定义 Command
@dataclass
class CreateProductCommand:
    name: str
    sku: str
    price: float
    category_id: str

# 2. 定义 Handler（使用装饰器）
@command_handler
class CreateProductHandler(CommandHandler[CreateProductCommand, str]):
    """创建产品 Handler"""
    
    async def validate(self, command: CreateProductCommand) -> None:
        """验证命令"""
        if not command.name or not command.name.strip():
            raise ValidationError("Product name cannot be empty")
        
        if command.price <= 0:
            raise ValidationError("Price must be positive")
    
    async def handle(self, command: CreateProductCommand) -> str:
        """执行业务逻辑"""
        # 创建聚合根
        product = Product(
            id=ID.generate(),
            name=command.name.strip(),
            sku=command.sku.strip(),
            price=command.price,
            category_id=ID(command.category_id),
        )
        
        # 保存（事务自动管理）
        repo = self.uow.repository(Product)
        await repo.save(product)
        
        return str(product.id)

# 3. FastAPI 路由
@router.post("/products", response_model=ProductResponse)
async def create_product(
    request: CreateProductRequest,
    handler: Annotated[CreateProductHandler, Depends(get_handler)],
) -> dict:
    """创建产品"""
    command = CreateProductCommand(
        name=request.name,
        sku=request.sku,
        price=request.price,
        category_id=request.category_id,
    )
    
    product_id = await handler.execute(command)
    return {"id": product_id}
```

---

### 示例 2：Query Handler（读操作）

```python
from dataclasses import dataclass
from bento.application import query_handler, QueryHandler
from bento.application.ports.uow import UnitOfWork
from bento.core.ids import ID

# 1. 定义 Query
@dataclass
class GetProductQuery:
    product_id: str

# 2. 定义 Response DTO
@dataclass
class ProductDTO:
    id: str
    name: str
    sku: str
    price: float
    category_id: str
    
    @classmethod
    def from_domain(cls, product: Product) -> "ProductDTO":
        """从领域对象转换"""
        return cls(
            id=str(product.id),
            name=product.name,
            sku=product.sku,
            price=product.price,
            category_id=str(product.category_id),
        )

# 3. 定义 Handler（使用装饰器）
@query_handler
class GetProductHandler(QueryHandler[GetProductQuery, ProductDTO]):
    """获取产品 Handler"""
    
    async def handle(self, query: GetProductQuery) -> ProductDTO:
        """执行查询"""
        repo = self.uow.repository(Product)
        product = await repo.get(ID(query.product_id))
        
        if not product:
            raise EntityNotFoundError(f"Product {query.product_id} not found")
        
        return ProductDTO.from_domain(product)

# 4. FastAPI 路由
@router.get("/products/{product_id}", response_model=ProductDTO)
async def get_product(
    product_id: str,
    handler: Annotated[GetProductHandler, Depends(get_handler)],
) -> ProductDTO:
    """获取产品详情"""
    query = GetProductQuery(product_id=product_id)
    return await handler.execute(query)
```

---

## 🛠️ 统一的 Handler 工厂（DI 集成）

创建一个通用的依赖注入工厂：

```python
# shared/dependencies.py

from typing import Annotated, Any, Type, TypeVar
from fastapi import Depends
from bento.application.ports.uow import UnitOfWork
from bento.persistence.uow import SQLAlchemyUnitOfWork
from shared.infrastructure.database import get_session

THandler = TypeVar("THandler")

async def get_uow(
    session = Depends(get_session)
) -> UnitOfWork:
    """获取 UnitOfWork"""
    return SQLAlchemyUnitOfWork(session)

def get_handler(
    handler_cls: Type[THandler],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> THandler:
    """通用的 Handler 工厂
    
    自动注入 UoW 到任何 Handler。
    
    用法：
        handler: Annotated[CreateProductHandler, Depends(get_handler)]
    """
    return handler_cls(uow)
```

---

## 📊 装饰器高级功能

### 1. 查询已注册的 Handlers

```python
from bento.application.decorators import get_registered_handlers

# 获取所有已注册的 Handler
handlers = get_registered_handlers()

print(handlers["commands"])  # 所有 Command Handlers
# {'CreateProductHandler': <class 'CreateProductHandler'>, ...}

print(handlers["queries"])   # 所有 Query Handlers
# {'GetProductHandler': <class 'GetProductHandler'>, ...}
```

### 2. 检查类是否为 Handler

```python
from bento.application.decorators import is_handler, get_handler_type

# 检查是否为 Handler
print(is_handler(CreateProductHandler))  # True
print(is_handler(SomeOtherClass))        # False

# 获取 Handler 类型
print(get_handler_type(CreateProductHandler))  # "command"
print(get_handler_type(GetProductHandler))     # "query"
```

### 3. 自定义 Handler 工厂

```python
from bento.application.decorators import create_handler_factory

# 创建专门的工厂函数
get_create_product_handler = create_handler_factory(CreateProductHandler)

# 在路由中使用
@router.post("/products")
async def create_product(
    handler: Annotated[CreateProductHandler, Depends(get_create_product_handler)],
):
    ...
```

---

## ⚠️ 注意事项

### 1. Handler 必须继承基类

```python
# ❌ 错误：没有继承 CommandHandler
@command_handler
class BadHandler:
    pass
# TypeError: BadHandler must inherit from CommandHandler

# ✅ 正确
@command_handler
class GoodHandler(CommandHandler[...]):
    pass
```

### 2. 装饰器顺序（如果有多个）

```python
# ✅ 正确：@command_handler 应该在最外层
@command_handler
@some_other_decorator
class CreateProductHandler(CommandHandler[...]):
    pass
```

### 3. Query Handler 不应有副作用

```python
# ❌ 错误：Query 不应修改状态
@query_handler
class BadQueryHandler(QueryHandler[...]):
    async def handle(self, query):
        product = await repo.get(query.id)
        product.view_count += 1  # ❌ 不应该修改！
        await repo.save(product)  # ❌ 不应该保存！
        return ProductDTO.from_domain(product)

# ✅ 正确：Query 只读取
@query_handler
class GoodQueryHandler(QueryHandler[...]):
    async def handle(self, query):
        product = await repo.get(query.id)
        return ProductDTO.from_domain(product)  # ✅ 只返回数据
```

---

## 🎯 最佳实践

### 1. 命名规范

```python
# Commands: {Action}{Entity}Handler
@command_handler
class CreateProductHandler(CommandHandler[...]): ...

@command_handler
class UpdateProductHandler(CommandHandler[...]): ...

@command_handler
class DeleteProductHandler(CommandHandler[...]): ...

# Queries: {Action}{Entity}Handler
@query_handler
class GetProductHandler(QueryHandler[...]): ...

@query_handler
class ListProductsHandler(QueryHandler[...]): ...

@query_handler
class SearchProductsHandler(QueryHandler[...]): ...
```

### 2. 一个文件一个 Handler

```
application/
├── commands/
│   ├── create_product.py     # CreateProductHandler
│   ├── update_product.py     # UpdateProductHandler
│   └── delete_product.py     # DeleteProductHandler
└── queries/
    ├── get_product.py        # GetProductHandler
    └── list_products.py      # ListProductsHandler
```

### 3. 统一导出

```python
# application/commands/__init__.py
from .create_product import CreateProductCommand, CreateProductHandler
from .update_product import UpdateProductCommand, UpdateProductHandler
from .delete_product import DeleteProductCommand, DeleteProductHandler

__all__ = [
    "CreateProductCommand",
    "CreateProductHandler",
    "UpdateProductCommand",
    "UpdateProductHandler",
    "DeleteProductCommand",
    "DeleteProductHandler",
]
```

---

## 🚀 完整项目结构示例

```
contexts/catalog/
├── application/
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── create_product.py
│   │   │   @command_handler
│   │   │   class CreateProductHandler(CommandHandler): ...
│   │   ├── update_product.py
│   │   └── delete_product.py
│   │
│   └── queries/
│       ├── __init__.py
│       ├── get_product.py
│       │   @query_handler
│       │   class GetProductHandler(QueryHandler): ...
│       └── list_products.py
│
├── domain/
│   └── product.py
│
└── interfaces/
    └── product_api.py  # FastAPI routes
```

---

## 📝 总结

**装饰器支持的优势**：

1. ✅ **代码简洁** - 减少样板代码
2. ✅ **自动注册** - 无需手动管理 Handler 列表
3. ✅ **统一 DI** - 一个工厂函数处理所有 Handler
4. ✅ **类型安全** - 保持完整的类型提示
5. ✅ **易于测试** - Handler 仍然是普通的 Python 类
6. ✅ **向后兼容** - 不使用装饰器也可以正常工作

**核心理念**：
- Command Handler = 写操作 + 事务 + 事件
- Query Handler = 读操作 + 无副作用 + DTO
- 装饰器 = 注册 + 元数据 + DI 集成

---

## 🔗 相关文档

- [CommandHandler API Reference](../api/command_handler.md)
- [QueryHandler API Reference](../api/query_handler.md)
- [CQRS Architecture Guide](../architecture/CQRS.md)
- [Dependency Injection Guide](../guides/DEPENDENCY_INJECTION.md)
