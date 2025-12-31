# LocaleMiddleware - i18n Locale Detection

**Bento Framework Middleware**

Automatic locale detection and context management for internationalization (i18n) support.

---

## 🎯 Purpose

LocaleMiddleware automatically detects user's preferred locale from request headers and sets `LocaleContext` for use by i18n message renderers.

---

## 📦 Installation

Already included in Bento Framework:

```python
from bento.runtime.middleware import LocaleMiddleware
```

---

## 🚀 Basic Usage

### Minimal Setup

```python
from fastapi import FastAPI
from bento.runtime.middleware import LocaleMiddleware

app = FastAPI()

app.add_middleware(
    LocaleMiddleware,
    default_locale="en-US",
    supported_locales=["en-US", "zh-CN"],
)
```

### With i18n Integration

```python
from bento.core import set_global_message_renderer
from bento.runtime.middleware import LocaleMiddleware
from myapp.i18n import MessageRenderer, CATALOG

# 1. Register i18n renderer
renderer = MessageRenderer(CATALOG, default_locale="zh-CN")
set_global_message_renderer(renderer)

# 2. Add locale middleware
app.add_middleware(
    LocaleMiddleware,
    default_locale="zh-CN",
    supported_locales=["en-US", "zh-CN", "ja-JP"],
)
```

---

## ⚙️ Configuration

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_locale` | `str` | `"en-US"` | Default locale code |
| `supported_locales` | `list[str]` | `["en-US", "zh-CN"]` | List of supported locale codes |
| `header_name` | `str` | `"Accept-Language"` | HTTP header name for locale detection |

### Example

```python
app.add_middleware(
    LocaleMiddleware,
    default_locale="zh-CN",           # Chinese as default
    supported_locales=[
        "en-US",                      # English (US)
        "zh-CN",                      # Chinese (Simplified)
        "zh-TW",                      # Chinese (Traditional)
        "ja-JP",                      # Japanese
        "ko-KR",                      # Korean
    ],
    header_name="Accept-Language",    # Standard HTTP header
)
```

---

## 🔍 Locale Detection Logic

### Detection Strategy

1. **Read Accept-Language header** from request
2. **Match against supported locales** (case-insensitive)
3. **Fall back to default locale** if no match

### Matching Rules

```python
# Full locale match: "zh-CN" matches "zh-CN"
Accept-Language: zh-CN
→ Detected: zh-CN

# Language code match: "zh" matches "zh-CN"
Accept-Language: zh
→ Detected: zh-CN

# Multiple locales: first match wins
Accept-Language: ja, zh-CN;q=0.9, en-US;q=0.8
→ Detected: ja-JP (if supported)

# No match: use default
Accept-Language: fr-FR
→ Detected: en-US (default)
```

---

## 💡 Usage in Business Code

### Automatic Integration

No code changes needed! LocaleContext is automatically set:

```python
from bento.core import DomainException

# Exception message will be in user's preferred locale
raise DomainException(reason_code="PRODUCT_NOT_FOUND")
```

### Manual Locale Access

```python
from bento.core import LocaleContext

# Get current locale
locale = LocaleContext.get()  # "zh-CN"

# Use in custom logic
if locale == "zh-CN":
    # Chinese-specific logic
    ...
```

---

## 🧪 Testing

### Test Different Locales

```bash
# Chinese
curl -H "Accept-Language: zh-CN" http://localhost:8000/api/products

# English
curl -H "Accept-Language: en-US" http://localhost:8000/api/products

# Japanese (if supported)
curl -H "Accept-Language: ja-JP" http://localhost:8000/api/products

# Default (no header)
curl http://localhost:8000/api/products
```

### Test in Python

```python
from fastapi.testclient import TestClient

client = TestClient(app)

# Test Chinese
response = client.get("/api/products", headers={"Accept-Language": "zh-CN"})

# Test English
response = client.get("/api/products", headers={"Accept-Language": "en-US"})
```

---

## 🎓 Best Practices

### 1. Place Early in Middleware Stack

```python
# ✅ Good - Early in stack
app.add_middleware(LocaleMiddleware, ...)
app.add_middleware(TenantMiddleware, ...)
app.add_middleware(CORSMiddleware, ...)

# ❌ Bad - Too late
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(TenantMiddleware, ...)
app.add_middleware(LocaleMiddleware, ...)  # Too late!
```

### 2. Match Supported Locales to Translations

```python
# ✅ Good - Only list locales you have translations for
app.add_middleware(
    LocaleMiddleware,
    supported_locales=["en-US", "zh-CN"],  # Have translations
)

# ❌ Bad - Listing unsupported locales
app.add_middleware(
    LocaleMiddleware,
    supported_locales=["en-US", "zh-CN", "fr-FR"],  # No French translations!
)
```

### 3. Choose Appropriate Default

```python
# For global audience
default_locale="en-US"

# For Chinese market
default_locale="zh-CN"

# For Japanese market
default_locale="ja-JP"
```

---

## 🔧 Advanced Usage

### Custom Locale Detection

For more complex locale detection (e.g., from user preferences, cookies, URL), extend the middleware:

```python
from bento.runtime.middleware import LocaleMiddleware

class CustomLocaleMiddleware(LocaleMiddleware):
    def _detect_locale(self, accept_language: str | None) -> str:
        # 1. Check URL parameter
        if "locale" in request.query_params:
            return request.query_params["locale"]

        # 2. Check cookie
        if "user_locale" in request.cookies:
            return request.cookies["user_locale"]

        # 3. Fall back to Accept-Language
        return super()._detect_locale(accept_language)
```

---

## 📊 Comparison with Other Middleware

| Middleware | Purpose | Context | Auto Cleanup |
|------------|---------|---------|--------------|
| **LocaleMiddleware** | i18n locale | `LocaleContext` | ✅ Yes |
| **TenantMiddleware** | Multi-tenancy | `TenantContext` | ✅ Yes |
| **RequestIDMiddleware** | Request tracking | Headers | N/A |
| **IdempotencyMiddleware** | Deduplication | Database | N/A |

---

## 🐛 Troubleshooting

### Locale Not Detected

**Problem**: Locale always defaults to `en-US`

**Solution**: Check Accept-Language header format
```bash
# ✅ Correct
Accept-Language: zh-CN

# ❌ Incorrect
Accept-Language: chinese
```

### Translations Not Working

**Problem**: Still seeing English messages with `zh-CN` locale

**Solution**: Ensure i18n renderer is registered
```python
from bento.core import set_global_message_renderer

renderer = MessageRenderer(CATALOG)
set_global_message_renderer(renderer)  # Must be called!
```

---

## 📚 Related Documentation

- [i18n Guide](/workspace/bento/docs/core/I18N_GUIDE.md)
- [LocaleContext API](/workspace/bento/src/bento/core/i18n.py)
- [Middleware Architecture](/workspace/bento/src/bento/runtime/middleware/README.md)

---

## ✅ Summary

LocaleMiddleware provides:
- ✅ Automatic locale detection from Accept-Language
- ✅ Configurable default and supported locales
- ✅ Async-safe context management
- ✅ Zero-configuration integration with i18n system
- ✅ Production-ready and tested

**Use LocaleMiddleware for hassle-free i18n support in your Bento applications!**
