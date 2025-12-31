# i18n Support in Bento Framework

**Status**: Optional mechanism (not required)

Bento Framework provides **optional** i18n (internationalization) mechanisms following the principle of **"Framework provides mechanisms, applications provide strategies"**.

---

## 🎯 Design Philosophy

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer                                       │
│  - Chooses i18n strategy (gettext, fluent, custom)     │
│  - Implements IMessageRenderer/ILocaleResolver          │
│  - Provides translation catalogs                        │
│  - Registers with Framework (optional)                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Bento Framework (THIS MODULE)                          │
│                                                          │
│  ✅ Provides:                                            │
│     - Interfaces (IMessageRenderer, ILocaleResolver)    │
│     - Context (LocaleContext)                           │
│     - Integration (exception system)                    │
│                                                          │
│  ❌ Does NOT provide:                                    │
│     - Translation catalogs                              │
│     - Locale detection strategies                       │
│     - i18n library dependencies                         │
│     - Forced i18n usage                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📐 Core Interfaces

### IMessageRenderer

```python
from bento.core import IMessageRenderer

class IMessageRenderer(Protocol):
    """Message renderer interface (Optional)."""

    def render(
        self,
        reason_code: str,
        fallback: str,
        locale: str | None = None,
        **context: Any,
    ) -> str:
        """Render a message for the given reason code.

        Args:
            reason_code: The reason code to translate
            fallback: Default message if translation not found
            locale: Optional locale code (e.g., "en-US", "zh-CN")
            **context: Optional context variables for interpolation

        Returns:
            Translated message or fallback
        """
        ...
```

### ILocaleResolver

```python
from bento.core import ILocaleResolver

class ILocaleResolver(Protocol):
    """Locale resolver interface (Optional)."""

    def resolve(self, request: Any) -> str:
        """Resolve locale from request.

        Args:
            request: Request object (framework-agnostic)

        Returns:
            Locale code (e.g., "en-US", "zh-CN")
        """
        ...
```

### LocaleContext

```python
from bento.core import LocaleContext

# Set current locale (usually in middleware)
LocaleContext.set("zh-CN")

# Get current locale
locale = LocaleContext.get()  # "zh-CN"

# Clear
LocaleContext.clear()
```

---

## 🚀 Usage Examples

### Example 1: Simple Application (No i18n)

```python
# No i18n needed - just use default messages
from bento.core import DomainException

raise DomainException(
    reason_code="STATE_CONFLICT",
    message="Current state does not allow this operation"
)
```

### Example 2: Application with i18n

#### Step 1: Implement IMessageRenderer

```python
# myapp/i18n/renderer.py
from bento.core import IMessageRenderer

class MessageRenderer:
    """Application's message renderer."""

    def __init__(self, catalog: dict, default_locale: str = "en-US"):
        self._catalog = catalog
        self._default = default_locale

    def render(
        self,
        reason_code: str,
        fallback: str,
        locale: str | None = None,
        **context
    ) -> str:
        loc = locale or self._default
        msg = self._catalog.get(loc, {}).get(reason_code, fallback)

        # Support interpolation
        if context:
            msg = msg.format(**context)

        return msg
```

#### Step 2: Define Translation Catalog

```python
# myapp/i18n/catalog.py
CATALOG = {
    "zh-CN": {
        "STATE_CONFLICT": "当前状态不允许此操作",
        "NOT_FOUND": "资源不存在",
        "VALIDATION_FAILED": "参数校验失败: {field}",
    },
    "en-US": {
        "STATE_CONFLICT": "Current state does not allow this operation",
        "NOT_FOUND": "Resource not found",
        "VALIDATION_FAILED": "Validation failed: {field}",
    },
}
```

#### Step 3: Register at Application Startup

```python
# myapp/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from bento.core import set_global_message_renderer
from myapp.i18n import MessageRenderer, CATALOG

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register i18n renderer (optional)
    renderer = MessageRenderer(CATALOG, default_locale="zh-CN")
    set_global_message_renderer(renderer)

    yield

    # Cleanup
    set_global_message_renderer(None)

app = FastAPI(lifespan=lifespan)
```

#### Step 4: Use in Business Code

```python
# Domain layer - no i18n code needed!
from bento.core import DomainException

# Framework automatically uses renderer if registered
raise DomainException(
    reason_code="STATE_CONFLICT",
    current_state="DRAFT"
)
# Message will be: "当前状态不允许此操作" (if locale is zh-CN)

# With interpolation
raise DomainException(
    reason_code="VALIDATION_FAILED",
    field="email"
)
# Message will be: "参数校验失败: email"
```

### Example 3: Locale Middleware

```python
# myapp/middleware/locale.py
from fastapi import Request
from bento.core import LocaleContext

async def locale_middleware(request: Request, call_next):
    """Set locale from request header."""
    # Resolve locale from Accept-Language header
    locale = request.headers.get("Accept-Language", "en-US")
    LocaleContext.set(locale)

    try:
        response = await call_next(request)
        return response
    finally:
        LocaleContext.clear()

# Register middleware
app.middleware("http")(locale_middleware)
```

---

## 🎓 Integration with Exception System

The exception system automatically uses the registered `IMessageRenderer`:

```python
# exceptions.py (framework code)
def __post_init__(self):
    # ... resolve from contracts ...

    # Try to render message with i18n (optional)
    if not self.message and _global_message_renderer is not None:
        try:
            from bento.core.i18n import LocaleContext

            locale = LocaleContext.get()
            fallback = rc.message if rc else self.reason_code
            self.message = _global_message_renderer.render(
                self.reason_code, fallback, locale, **self.details
            )
        except Exception:
            # Silently fall back if i18n rendering fails
            pass
```

**Flow**:
1. Exception raised with `reason_code`
2. Framework checks if `IMessageRenderer` is registered
3. If yes, calls `renderer.render(reason_code, fallback, locale)`
4. If no, uses default message from contracts
5. If rendering fails, falls back gracefully

---

## 📊 Comparison with Other Approaches

| Approach | Framework Complexity | App Flexibility | Bento Philosophy |
|----------|---------------------|-----------------|------------------|
| **Framework provides i18n** | ❌ High | ❌ Low | ❌ No |
| **Framework provides mechanism** | ✅ Low | ✅ High | ✅ Yes |
| **No i18n support** | ✅ Lowest | ⚠️ Medium | ✅ Yes |

---

## 🎯 Best Practices

### 1. Keep Domain Layer i18n-Free

```python
# ✅ Good - Domain layer uses reason codes
raise DomainException(reason_code="STATE_CONFLICT")

# ❌ Bad - Domain layer depends on i18n
from myapp.i18n import t
raise DomainException(message=t("STATE_CONFLICT"))
```

### 2. Use Reason Codes as Keys

```python
# ✅ Good - Consistent with contracts
CATALOG = {
    "zh-CN": {
        "STATE_CONFLICT": "状态冲突",
        "NOT_FOUND": "未找到",
    }
}

# ❌ Bad - Custom keys
CATALOG = {
    "zh-CN": {
        "error.state.conflict": "状态冲突",
    }
}
```

### 3. Provide Fallbacks

```python
# ✅ Good - Always provide fallback
def render(self, reason_code: str, fallback: str, locale: str | None = None) -> str:
    msg = self._catalog.get(locale, {}).get(reason_code)
    return msg or fallback  # Always return something

# ❌ Bad - May return None
def render(self, reason_code: str, fallback: str, locale: str | None = None) -> str:
    return self._catalog.get(locale, {}).get(reason_code)
```

### 4. Handle Interpolation

```python
# ✅ Good - Support context variables
CATALOG = {
    "zh-CN": {
        "VALIDATION_FAILED": "字段 {field} 验证失败",
    }
}

raise DomainException(
    reason_code="VALIDATION_FAILED",
    field="email"  # Will be interpolated
)
```

---

## 🔧 Advanced: Custom Locale Resolver

```python
from bento.core import ILocaleResolver

class HeaderLocaleResolver:
    """Resolve locale from Accept-Language header."""

    def __init__(self, default: str = "en-US"):
        self._default = default

    def resolve(self, request) -> str:
        # Parse Accept-Language header
        accept_lang = request.headers.get("Accept-Language", "")

        # Simple parsing (production should use proper parser)
        if "zh" in accept_lang.lower():
            return "zh-CN"
        elif "en" in accept_lang.lower():
            return "en-US"

        return self._default

class TenantLocaleResolver:
    """Resolve locale from tenant settings."""

    async def resolve(self, request) -> str:
        from bento.multitenancy import TenantContext

        tenant_id = TenantContext.get()
        if not tenant_id:
            return "en-US"

        # Fetch tenant settings from database
        tenant = await get_tenant(tenant_id)
        return tenant.locale or "en-US"
```

---

## ✅ Summary

**Bento Framework i18n Support**:
- ✅ Provides **optional mechanisms** (interfaces, context)
- ✅ Applications **choose** whether to use i18n
- ✅ Applications **implement** translation strategies
- ✅ Zero dependencies on i18n libraries
- ✅ Graceful fallback if not configured
- ✅ Follows "mechanism not policy" principle

**When to Use**:
- ✅ Multi-language SaaS applications
- ✅ Global enterprise systems
- ✅ Customer-facing applications

**When NOT to Use**:
- ❌ Internal tools (single language)
- ❌ API-only services
- ❌ Simple CRUD applications

---

## 📚 See Also

- [Exception System](./EXCEPTIONS.md)
- [Contracts Guide](../contracts/README.md)
- [Security Context](../security/README.md) (similar pattern)
- [Multi-tenancy](../multitenancy/README.md) (locale per tenant)
