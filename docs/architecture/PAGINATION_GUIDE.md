# 分页查询指南

## 概述

Bento Framework 提供了三种分页查询方式，满足不同场景的需求。

## 三种分页方式

### 方式 1：`paginate()` - 便捷方法（推荐用于简单场景）✨

**最简单的分页方式**，不需要了解 `PageParams` 和 `Page` 的细节。

```python
from bento.persistence.specification import EntitySpecificationBuilder

# 在 UseCase 中
async def handle(self, query: ListProductsQuery) -> ListProductsResult:
    product_repo = self.uow.repository(Product)

    # 简单分页 - 只需要 page 和 size
    page = await product_repo.paginate(page=query.page, size=query.page_size)

    # 带条件的分页
    spec = EntitySpecificationBuilder().where("status", "active").build()
    page = await product_repo.paginate(spec, page=query.page, size=query.page_size)

    return ListProductsResult(
        items=page.items,
        total=page.total,
        page=page.page,
        total_pages=page.total_pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )
```

**优点**：
- ✅ 最简洁，不需要创建 `PageParams` 对象
- ✅ 适合简单的分页场景
- ✅ 默认值：page=1, size=20

**适用场景**：
- 简单的列表页分页
- 不需要复杂的分页控制
- 快速原型开发

---

### 方式 2：`find_page()` - 完整控制（推荐用于复杂场景）

**完整的分页方法**，使用 `PageParams` 对象，提供更多控制。

```python
from bento.persistence.specification import EntitySpecificationBuilder, PageParams

async def handle(self, query: ListProductsQuery) -> ListProductsResult:
    product_repo = self.uow.repository(Product)

    # 创建分页参数
    page_params = PageParams(page=query.page, size=query.page_size)

    # 构建查询条件
    spec = (
        EntitySpecificationBuilder()
        .where("category_id", query.category_id)
        .where("is_active", True)
        .order_by("created_at", "desc")
        .build()
    )

    # 分页查询
    page = await product_repo.find_page(spec, page_params)

    return ListProductsResult(
        items=page.items,
        total=page.total,
        page=page.page,
        total_pages=page.total_pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )
```

**优点**：
- ✅ 明确的语义：这是分页查询
- ✅ 返回完整的 `Page` 对象
- ✅ 适合需要完整分页信息的场景
- ✅ `PageParams` 可以复用

**适用场景**：
- 需要完整分页元数据的场景
- 复杂的查询条件
- 需要在多处使用相同的分页参数

---

### 方式 3：Builder 的 `paginate()` - 链式调用

**在 Specification Builder 中直接设置分页**。

```python
from bento.persistence.specification import EntitySpecificationBuilder

async def handle(self, query: ListProductsQuery) -> ListProductsResult:
    product_repo = self.uow.repository(Product)

    # 在 builder 中设置分页
    spec = (
        EntitySpecificationBuilder()
        .where("status", "active")
        .order_by("created_at", "desc")
        .paginate(page=query.page, size=query.page_size)  # 链式调用
        .build()
    )

    # 使用 list() 方法（内部会应用分页）
    products = await product_repo.list(spec)

    # 注意：这种方式返回 list[AR]，不是 Page 对象
    # 需要手动查询总数
    total = await product_repo.count(spec)

    return ListProductsResult(
        items=products,
        total=total,
        # 需要手动计算其他元数据
    )
```

**优点**：
- ✅ 链式调用，代码流畅
- ✅ 分页参数与查询条件一起定义

**缺点**：
- ❌ 返回 `list[AR]`，不是 `Page` 对象
- ❌ 需要手动查询总数和计算元数据

**适用场景**：
- 只需要数据列表，不需要分页元数据
- 与其他查询条件一起定义

---

## 对比总结

| 方式 | 代码量 | 返回类型 | 元数据 | 适用场景 |
|------|--------|---------|--------|----------|
| **`paginate()`** ✨ | 最少 | `Page[AR]` | ✅ 完整 | 简单分页 |
| **`find_page()`** | 中等 | `Page[AR]` | ✅ 完整 | 复杂场景 |
| **Builder.paginate()** | 中等 | `list[AR]` | ❌ 需手动 | 只要数据 |

---

## Page 对象详解

```python
class Page[T]:
    items: list[T]        # 当前页的数据
    total: int            # 总记录数
    page: int             # 当前页码（从1开始）
    size: int             # 每页大小
    total_pages: int      # 总页数（自动计算）
    has_next: bool        # 是否有下一页（自动计算）
    has_prev: bool        # 是否有上一页（自动计算）
```

**自动计算的元数据**：
- `total_pages = (total + size - 1) // size`
- `has_next = page < total_pages`
- `has_prev = page > 1`

---

## PageParams 详解

```python
@dataclass(frozen=True)
class PageParams:
    page: int = 1         # 页码，从1开始
    size: int = 10        # 每页大小

    @property
    def offset(self) -> int:
        """计算偏移量：(page - 1) * size"""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """限制数量（等于 size）"""
        return self.size
```

**验证规则**：
- `page >= 1`
- `size >= 1`

---

## 完整示例

### Query DTO

```python
from dataclasses import dataclass

@dataclass
class ListProductsQuery:
    """列出产品查询"""
    category_id: str | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 20
```

### Result DTO

```python
@dataclass
class ListProductsResult:
    """列出产品结果"""
    items: list[Product]
    total: int
    page: int
    total_pages: int
    has_next: bool
    has_prev: bool
```

### UseCase 实现

```python
from bento.application.usecase import BaseUseCase
from bento.persistence.specification import EntitySpecificationBuilder

class ListProductsUseCase(BaseUseCase[ListProductsQuery, ListProductsResult]):
    """列出产品用例"""

    async def handle(self, query: ListProductsQuery) -> ListProductsResult:
        product_repo = self.uow.repository(Product)

        # 构建查询条件
        builder = EntitySpecificationBuilder()

        if query.category_id:
            builder = builder.where("category_id", query.category_id)

        if query.status:
            builder = builder.where("status", query.status)

        spec = builder.order_by("created_at", "desc").build()

        # 方式 1：使用 paginate()（推荐）✨
        page = await product_repo.paginate(spec, page=query.page, size=query.page_size)

        # 方式 2：使用 find_page()
        # from bento.persistence.specification import PageParams
        # page_params = PageParams(page=query.page, size=query.page_size)
        # page = await product_repo.find_page(spec, page_params)

        return ListProductsResult(
            items=page.items,
            total=page.total,
            page=page.page,
            total_pages=page.total_pages,
            has_next=page.has_next,
            has_prev=page.has_prev,
        )
```

### API 端点

```python
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/products")
async def list_products(
    category_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    use_case: ListProductsUseCase = Depends(get_list_products_use_case),
):
    """列出产品（分页）"""
    query = ListProductsQuery(
        category_id=category_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    result = await use_case.execute(query)

    return {
        "items": [product_to_dict(p) for p in result.items],
        "pagination": {
            "total": result.total,
            "page": result.page,
            "page_size": page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_prev": result.has_prev,
        }
    }
```

---

## 最佳实践

### 1. 选择合适的方式

- **简单场景**：使用 `paginate()` ✨
- **复杂场景**：使用 `find_page()`
- **只要数据**：使用 Builder 的 `paginate()`

### 2. 设置合理的默认值

```python
@dataclass
class ListQuery:
    page: int = 1           # 默认第一页
    page_size: int = 20     # 默认每页20条
```

### 3. 限制最大页面大小

```python
async def handle(self, query: ListQuery) -> ListResult:
    # 限制最大页面大小
    page_size = min(query.page_size, 100)  # 最多100条

    page = await repo.paginate(page=query.page, size=page_size)
    ...
```

### 4. 返回完整的分页元数据

```python
# ✅ 好的做法：返回完整元数据
return {
    "items": [...],
    "pagination": {
        "total": page.total,
        "page": page.page,
        "page_size": page.size,
        "total_pages": page.total_pages,
        "has_next": page.has_next,
        "has_prev": page.has_prev,
    }
}

# ❌ 不好的做法：只返回数据
return {"items": [...]}
```

### 5. 处理空结果

```python
page = await repo.paginate(spec, page=query.page, size=query.page_size)

if not page.items:
    # 返回空结果，但仍包含分页元数据
    return ListResult(
        items=[],
        total=0,
        page=1,
        total_pages=0,
        has_next=False,
        has_prev=False,
    )
```

---

## 总结

Bento Framework 提供了灵活的分页支持：

1. **`paginate()`** - 最简单，适合大多数场景 ✨
2. **`find_page()`** - 完整控制，适合复杂场景
3. **Builder.paginate()** - 链式调用，适合只要数据的场景

**推荐**：优先使用 `paginate()` 方法，它提供了最佳的开发体验！🎉
