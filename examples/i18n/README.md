# i18n Examples

This directory contains examples of using Bento Framework's optional i18n support.

## Examples

### 1. Simple i18n Example (`simple_i18n_example.py`)

Basic demonstration of i18n functionality:
- Using exceptions without i18n (default behavior)
- Using exceptions with i18n (English and Chinese)
- Message interpolation with context variables
- Fallback behavior when translations are missing

**Run**:
```bash
uv run python examples/i18n/simple_i18n_example.py
```

### 2. FastAPI i18n Example (`fastapi_i18n_example.py`)

Complete FastAPI application with i18n integration:
- Locale middleware (reads Accept-Language header)
- Application lifespan (register/unregister renderer)
- Exception handler with i18n support
- Multiple test endpoints

**Run**:
```bash
uv run python examples/i18n/fastapi_i18n_example.py
```

**Test**:
```bash
# English (default)
curl http://localhost:8000/test/state-conflict

# Chinese
curl -H "Accept-Language: zh-CN" http://localhost:8000/test/state-conflict

# With interpolation
curl -H "Accept-Language: zh-CN" http://localhost:8000/test/not-found/product-123
```

## Key Concepts

### 1. Optional by Design

i18n is **completely optional**. Applications can:
- Ignore i18n entirely (use default messages)
- Implement i18n for some exceptions
- Implement full i18n support

### 2. Framework Provides Mechanisms

Bento provides:
- `IMessageRenderer` interface
- `LocaleContext` for async-safe locale storage
- Automatic integration with exception system

### 3. Applications Provide Strategies

Applications implement:
- Translation catalogs
- Locale detection logic
- Message rendering logic

## See Also

- [i18n Guide](../../docs/core/I18N_GUIDE.md) - Complete documentation
- [Exception System](../../docs/core/EXCEPTIONS.md) - Exception handling
- [Security Module](../../src/bento/security/README.md) - Similar pattern
