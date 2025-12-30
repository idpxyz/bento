# 安全中间件集成方案设计

## 🎯 目标

设计一个最佳的安全中间件集成方案，满足以下要求：
1. 保持职责清晰
2. 遵循"提供机制，不提供策略"原则
3. 提供统一的集成入口
4. 易于应用层使用
5. 易于未来扩展

---

## 📐 方案对比

### 方案 1: 直接从 bento.security 导入（当前）

**优点**:
- ✅ 职责清晰
- ✅ 最小化

**缺点**:
- ❌ 没有统一的集成入口
- ❌ 应用层需要了解 bento.security 的细节
- ❌ 难以扩展到其他集成

**使用方式**:
```python
from bento.security import add_security_middleware

app = FastAPI()
add_security_middleware(app, authenticator=MyAuthenticator())
```

---

### 方案 2: 在 bento.runtime.middleware 中导出（不推荐）

**优点**:
- ✅ 统一导出

**缺点**:
- ❌ 混淆职责（middleware vs integrations）
- ❌ 违反"提供机制，不提供策略"原则
- ❌ 基础设施中间件和安全中间件混在一起

**使用方式**:
```python
from bento.runtime.middleware import add_security_middleware

app = FastAPI()
add_security_middleware(app, authenticator=MyAuthenticator())
```

---

### 方案 3: 在 bento.runtime.integrations 中创建 security 模块（推荐）✅

**优点**:
- ✅ 职责清晰（integrations = 集成助手）
- ✅ 统一导出（所有 runtime 集成都在这里）
- ✅ 遵循架构原则
- ✅ 易于扩展（未来可添加更多集成）
- ✅ 应用层使用简洁

**缺点**:
- ⚠️ 需要创建新模块

**使用方式**:
```python
from bento.runtime.integrations import setup_security

app = FastAPI()
setup_security(app, authenticator=MyAuthenticator())
```

---

## ✅ 最佳方案：方案 3

### 架构设计

```
bento/
├── security/                          ← 安全机制（提供接口和工具）
│   ├── ports.py                       (IAuthenticator, IAuthorizer, ITenantResolver)
│   ├── context.py                     (SecurityContext)
│   ├── models.py                      (CurrentUser)
│   ├── middleware.py                  (add_security_middleware)
│   ├── decorators.py                  (@require_auth, @require_permission)
│   ├── depends.py                     (get_current_user)
│   └── __init__.py
│
└── runtime/
    ├── middleware/                    ← 基础设施中间件
    │   ├── idempotency.py
    │   ├── request_id.py
    │   ├── logging.py
    │   ├── rate_limiting.py
    │   └── __init__.py
    │
    └── integrations/                  ← 集成助手（统一入口）
        ├── fastapi_openapi.py         (setup_bento_openapi)
        ├── security.py                (setup_security) ✨ 新增
        └── __init__.py                (统一导出)
```

### 关键设计原则

#### 1. 职责分离

| 模块 | 职责 | 内容 |
|------|------|------|
| `bento.security` | 安全机制 | 接口、上下文、装饰器、工具 |
| `bento.runtime.middleware` | 基础设施中间件 | 请求去重、追踪、日志、速率限制 |
| `bento.runtime.integrations` | 集成助手 | 便捷的设置函数 |

#### 2. 遵循原则

- ✅ **提供机制，不提供策略** - `bento.security` 提供机制，应用提供策略
- ✅ **单一职责** - 每个模块职责清晰
- ✅ **统一入口** - 所有 runtime 集成都通过 `bento.runtime.integrations`
- ✅ **易于扩展** - 未来可添加更多集成

#### 3. 导入路径清晰

```python
# 基础设施中间件（来自 runtime）
from bento.runtime.middleware import IdempotencyMiddleware

# 集成助手（来自 runtime.integrations）
from bento.runtime.integrations import setup_security, setup_bento_openapi

# 安全机制（来自 security）
from bento.security import SecurityContext, IAuthenticator
```

---

## 📋 实现步骤

### 步骤 1: 创建 `bento.runtime.integrations.security` 模块

**文件**: `/workspace/bento/src/bento/runtime/integrations/security.py`

```python
"""Security integration for Bento Runtime.

This module provides convenient setup functions for integrating
security features into FastAPI applications.

Example:
    ```python
    from bento.runtime.integrations import setup_security

    app = FastAPI()
    setup_security(app, authenticator=MyAuthenticator())
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from bento.security import add_security_middleware
from bento.security.ports import IAuthenticator


def setup_security(
    app: "FastAPI",
    authenticator: IAuthenticator,
    require_auth: bool = False,
    exclude_paths: list[str] | None = None,
) -> None:
    """Setup security for Bento application.

    This is a convenience wrapper around bento.security's
    add_security_middleware function, providing a unified
    integration point in bento.runtime.

    Args:
        app: FastAPI application
        authenticator: IAuthenticator implementation
        require_auth: If True, require authentication for all requests
        exclude_paths: Paths to exclude from authentication

    Example:
        ```python
        from bento.runtime.integrations import setup_security
        from my_app.auth import JWTAuthenticator

        app = FastAPI()
        setup_security(
            app,
            authenticator=JWTAuthenticator(jwks_url="..."),
            require_auth=True,
            exclude_paths=["/health", "/docs"],
        )
        ```
    """
    add_security_middleware(
        app,
        authenticator=authenticator,
        require_auth=require_auth,
        exclude_paths=exclude_paths,
    )
```

### 步骤 2: 更新 `bento.runtime.integrations.__init__.py`

```python
"""Bento Runtime Integrations.

This module provides integration helpers for various frameworks
and features in Bento applications.

Available integrations:
- setup_bento_openapi: FastAPI OpenAPI customization
- setup_security: Security middleware setup
"""

from bento.runtime.integrations.fastapi_openapi import setup_bento_openapi
from bento.runtime.integrations.security import setup_security

__all__ = [
    "setup_bento_openapi",
    "setup_security",
]
```

### 步骤 3: 更新应用层 bootstrap

**文件**: `/workspace/bento/applications/my-shop/runtime/bootstrap_v2.py`

```python
from bento.runtime.integrations import setup_bento_openapi, setup_security
from bento.runtime.middleware import IdempotencyMiddleware
from my_shop.auth import MyAuthenticator

def create_app():
    app = FastAPI()

    # 1. 基础设施中间件
    app.add_middleware(IdempotencyMiddleware, ...)

    # 2. 安全集成
    setup_security(app, authenticator=MyAuthenticator())

    # 3. OpenAPI 集成
    setup_bento_openapi(app)

    return app
```

---

## 🎯 优势总结

### 1. 架构清晰 ✅

```
应用层
  ↓
bento.runtime.integrations (统一入口)
  ├─→ setup_security() → bento.security
  └─→ setup_bento_openapi() → bento.runtime.integrations.fastapi_openapi

bento.security (安全机制)
  ├─ IAuthenticator (接口)
  ├─ SecurityContext (上下文)
  └─ add_security_middleware() (工具)
```

### 2. 职责清晰 ✅

| 层级 | 职责 |
|------|------|
| `bento.security` | 提供安全机制 |
| `bento.runtime.integrations` | 提供集成助手 |
| `bento.runtime.middleware` | 提供基础设施中间件 |
| 应用层 | 选择和配置实现 |

### 3. 易于使用 ✅

```python
# 一行代码集成安全
from bento.runtime.integrations import setup_security
setup_security(app, authenticator=MyAuthenticator())
```

### 4. 易于扩展 ✅

```python
# 未来可以添加更多集成
from bento.runtime.integrations import (
    setup_security,
    setup_bento_openapi,
    setup_caching,        # 未来
    setup_monitoring,     # 未来
    setup_tracing,        # 未来
)
```

### 5. 遵循原则 ✅

- ✅ 提供机制，不提供策略
- ✅ 单一职责原则
- ✅ 开闭原则（易于扩展）
- ✅ 依赖倒置原则（依赖接口）

---

## 📊 方案评分

| 评分维度 | 方案 1 | 方案 2 | 方案 3 |
|---------|--------|--------|--------|
| 职责清晰 | ✅ 100% | ❌ 30% | ✅ 100% |
| 统一入口 | ❌ 0% | ✅ 100% | ✅ 100% |
| 遵循原则 | ✅ 100% | ❌ 40% | ✅ 100% |
| 易于扩展 | ⚠️ 50% | ⚠️ 50% | ✅ 100% |
| 应用层体验 | ⚠️ 70% | ✅ 90% | ✅ 95% |
| **总体评分** | **⭐⭐⭐** | **⭐⭐** | **⭐⭐⭐⭐⭐** |

---

## ✅ 最终建议

**采用方案 3：在 `bento.runtime.integrations` 中创建 `security.py` 模块**

这是最佳方案，因为：

1. ✅ **完全符合架构原则** - 职责清晰，遵循 DDD 和 SOLID 原则
2. ✅ **提供统一入口** - 所有 runtime 集成都在一个地方
3. ✅ **易于应用层使用** - 简洁的 API
4. ✅ **易于未来扩展** - 可以添加更多集成
5. ✅ **保持 bento.security 纯粹** - 不污染安全模块

---

## 🚀 下一步

1. 创建 `bento.runtime.integrations.security.py`
2. 更新 `bento.runtime.integrations.__init__.py`
3. 更新应用层 bootstrap 代码
4. 添加文档和示例
5. 验证和测试

