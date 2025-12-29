# Middleware 架构组织评审

## 当前状态

### 现有 Middleware 位置

**1. bento.runtime.middleware/** (统一位置)
- ✅ `IdempotencyMiddleware` - 幂等性
- ✅ `RequestIDMiddleware` - 请求追踪
- ✅ `StructuredLoggingMiddleware` - 结构化日志
- ✅ `RateLimitingMiddleware` - 限流

**2. bento.multitenancy/** (独立模块)
- ⚠️ `add_tenant_middleware()` - 多租户识别

**3. bento.security/** (独立模块)
- ⚠️ `SecurityMiddleware` - 安全相关

## 问题分析

### 当前组织的问题

1. **不一致性**
   - 大部分 middleware 在 `runtime.middleware`
   - Multi-tenancy middleware 在 `multitenancy` 模块
   - Security middleware 在 `security` 模块
   - 用户需要从不同位置导入

2. **发现性差**
   - 用户可能不知道 multi-tenancy 和 security 有 middleware
   - 文档分散

3. **导入路径不统一**
   ```python
   # 当前需要从多个地方导入
   from bento.runtime.middleware import RequestIDMiddleware
   from bento.multitenancy import add_tenant_middleware
   from bento.security import SecurityMiddleware
   ```

## 推荐方案：统一到 runtime.middleware

### 方案 A：全部移到 runtime.middleware（推荐）

**目录结构**:
```
bento/runtime/middleware/
├── __init__.py
├── idempotency.py
├── request_id.py
├── logging.py
├── rate_limiting.py
├── tenant.py           # 新增：从 multitenancy 移过来
├── security.py         # 新增：从 security 移过来
├── README.md
└── MIDDLEWARE_DESIGN.md
```

**优势**:
- ✅ 统一的导入路径
- ✅ 更好的发现性
- ✅ 集中的文档
- ✅ 一致的 API 设计

**导入示例**:
```python
from bento.runtime.middleware import (
    RequestIDMiddleware,
    StructuredLoggingMiddleware,
    RateLimitingMiddleware,
    IdempotencyMiddleware,
    TenantMiddleware,      # 统一命名
    SecurityMiddleware,
)
```

**兼容性**:
```python
# bento/multitenancy/__init__.py
# 保持向后兼容
from bento.runtime.middleware.tenant import (
    TenantMiddleware as add_tenant_middleware,
    TenantContext,
)
```

### 方案 B：保持当前结构（不推荐）

**理由**:
- Multi-tenancy 是一个独立的功能模块
- Security 是一个独立的功能模块
- 它们不仅仅是 middleware

**问题**:
- ❌ 导入路径不一致
- ❌ 发现性差
- ❌ 文档分散

### 方案 C：混合方案（折中）

**核心 middleware** → `runtime.middleware`
- RequestID
- Logging
- RateLimiting
- Idempotency

**功能模块 middleware** → 各自模块
- Tenant → `multitenancy.middleware`
- Security → `security.middleware`

**同时在 runtime.middleware 中 re-export**:
```python
# bento/runtime/middleware/__init__.py
from bento.runtime.middleware.idempotency import IdempotencyMiddleware
from bento.runtime.middleware.request_id import RequestIDMiddleware
# ...

# Re-export from other modules for convenience
from bento.multitenancy.middleware import add_tenant_middleware as TenantMiddleware
from bento.security.middleware import SecurityMiddleware

__all__ = [
    "IdempotencyMiddleware",
    "RequestIDMiddleware",
    # ...
    "TenantMiddleware",
    "SecurityMiddleware",
]
```

**优势**:
- ✅ 保持模块独立性
- ✅ 统一的导入路径
- ✅ 向后兼容

## 推荐实施方案

### Phase 1: Re-export（立即实施）

在 `runtime.middleware.__init__.py` 中 re-export multi-tenancy middleware：

```python
# bento/runtime/middleware/__init__.py
"""Bento Runtime Middleware.

This module provides middleware components for FastAPI applications.

Available middleware:
- IdempotencyMiddleware: Request deduplication
- RequestIDMiddleware: Request tracking and tracing
- StructuredLoggingMiddleware: Structured HTTP logging
- RateLimitingMiddleware: API rate limiting
- TenantMiddleware: Multi-tenant context management
"""

from bento.runtime.middleware.idempotency import IdempotencyMiddleware
from bento.runtime.middleware.request_id import RequestIDMiddleware
from bento.runtime.middleware.logging import StructuredLoggingMiddleware
from bento.runtime.middleware.rate_limiting import RateLimitingMiddleware

# Re-export from multitenancy module for convenience
from bento.multitenancy.middleware import add_tenant_middleware as TenantMiddleware

__all__ = [
    "IdempotencyMiddleware",
    "RequestIDMiddleware",
    "StructuredLoggingMiddleware",
    "RateLimitingMiddleware",
    "TenantMiddleware",
]
```

**优势**:
- ✅ 无需移动代码
- ✅ 向后兼容
- ✅ 统一导入路径
- ✅ 立即可用

### Phase 2: 文档更新（立即实施）

更新 `runtime/middleware/README.md` 添加 TenantMiddleware 文档。

### Phase 3: 代码移动（可选，未来）

如果需要更彻底的重构，可以：
1. 创建 `runtime/middleware/tenant.py`
2. 移动代码并保持 API 兼容
3. 在 `multitenancy/middleware.py` 中 re-export

## 决策

### 立即实施：Re-export 方案

**原因**:
1. ✅ 最小改动
2. ✅ 向后兼容
3. ✅ 解决导入不一致问题
4. ✅ 提高发现性

**实施步骤**:
1. 在 `runtime/middleware/__init__.py` 中 re-export `TenantMiddleware`
2. 更新 `runtime/middleware/README.md` 添加使用文档
3. 更新 `MIDDLEWARE_DESIGN.md` 说明 multi-tenancy 支持

## 使用示例（实施后）

```python
# 统一从 runtime.middleware 导入所有 middleware
from bento.runtime.middleware import (
    RequestIDMiddleware,
    StructuredLoggingMiddleware,
    RateLimitingMiddleware,
    IdempotencyMiddleware,
    TenantMiddleware,
)

app = FastAPI()

# 按推荐顺序配置
app.add_middleware(RequestIDMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(TenantMiddleware, resolver=HeaderTenantResolver())
app.add_middleware(RateLimitingMiddleware, requests_per_minute=60)
app.add_middleware(IdempotencyMiddleware)
```

## 结论

**推荐**: 实施 Re-export 方案

- 在 `runtime.middleware` 中 re-export `TenantMiddleware`
- 保持原有代码位置不变
- 提供统一的导入路径
- 更新文档说明

这样既解决了导入不一致的问题，又保持了向后兼容性和模块独立性。
