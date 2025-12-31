# i18n Integration in my-shop

my-shop 应用已集成 Bento Framework 的 i18n 支持，提供中英文双语错误消息。

---

## 📁 文件结构

```
my-shop/
├── shared/
│   └── i18n/
│       ├── __init__.py          # 导出 CATALOG 和 MessageRenderer
│       ├── catalog.py           # 翻译字典（中文 + 英文）
│       └── renderer.py          # MessageRenderer 实现
├── runtime/
│   └── config/
│       ├── runtime_config.py    # 注册 i18n renderer
│       └── middleware_config.py # 注册 LocaleMiddleware (from Bento Framework)
```

**注意**: Locale middleware 使用 Bento Framework 提供的 `LocaleMiddleware`，无需自己实现。

---

## 🎯 功能特性

### 1. 自动语言检测

通过 `Accept-Language` 请求头自动检测语言：

```bash
# 中文
curl -H "Accept-Language: zh-CN" http://localhost:8001/api/v1/products/999

# 英文
curl -H "Accept-Language: en-US" http://localhost:8001/api/v1/products/999
```

### 2. 支持的语言

- **zh-CN** (简体中文) - 默认语言
- **en-US** (English)

### 3. 翻译覆盖范围

#### Bento Framework 错误码
- `STATE_CONFLICT` - 状态冲突，当前操作不允许
- `NOT_FOUND` - 资源不存在
- `VALIDATION_FAILED` - 参数校验失败
- `UNAUTHORIZED` - 需要身份认证
- `FORBIDDEN` - 访问被拒绝
- 等等...

#### my-shop 业务错误码

**Catalog Context (商品目录)**
- `CATEGORY_NOT_FOUND` - 分类不存在
- `PRODUCT_NOT_FOUND` - 商品不存在
- `PRODUCT_OUT_OF_STOCK` - 商品库存不足

**Identity Context (用户身份)**
- `USER_NOT_FOUND` - 用户不存在
- `EMAIL_ALREADY_EXISTS` - 邮箱已被使用

**Ordering Context (订单)**
- `ORDER_NOT_FOUND` - 订单不存在
- `INSUFFICIENT_STOCK` - 库存不足

---

## 🔧 使用方式

### 在业务代码中使用

**不需要任何修改！** 业务代码保持纯粹：

```python
# Domain 层 - 无需关心 i18n
from bento.core import DomainException

raise DomainException(reason_code="PRODUCT_NOT_FOUND")
# Framework 自动根据 Accept-Language 返回对应语言的消息
```

### 消息插值

支持动态参数插值：

```python
raise DomainException(
    reason_code="FIELD_REQUIRED",
    details={"field": "email"}
)
# 中文: "字段 email 是必需的"
# 英文: "Field email is required"
```

---

## 📝 添加新的翻译

### 1. 在 `shared/i18n/catalog.py` 中添加

```python
CATALOG = {
    "zh-CN": {
        "YOUR_NEW_CODE": "你的中文消息",
    },
    "en-US": {
        "YOUR_NEW_CODE": "Your English message",
    },
}
```

### 2. 在业务代码中使用

```python
raise DomainException(reason_code="YOUR_NEW_CODE")
```

---

## 🧪 测试示例

### 测试中文响应

```bash
curl -H "Accept-Language: zh-CN" \
     http://localhost:8001/api/v1/products/999

# 响应
{
  "error": {
    "reason_code": "PRODUCT_NOT_FOUND",
    "message": "商品不存在",  # 中文
    "category": "domain"
  }
}
```

### 测试英文响应

```bash
curl -H "Accept-Language: en-US" \
     http://localhost:8001/api/v1/products/999

# 响应
{
  "error": {
    "reason_code": "PRODUCT_NOT_FOUND",
    "message": "Product not found",  # 英文
    "category": "domain"
  }
}
```

### 测试默认行为（无 Accept-Language）

```bash
curl http://localhost:8001/api/v1/products/999

# 响应（使用默认语言：zh-CN）
{
  "error": {
    "reason_code": "PRODUCT_NOT_FOUND",
    "message": "商品不存在",  # 默认中文
    "category": "domain"
  }
}
```

---

## 🎓 技术细节

### 消息优先级

1. **显式传入的 message** (最高优先级)
2. **i18n renderer 渲染的消息** (根据 locale)
3. **contracts 中的默认消息**
4. **reason_code 本身** (最低优先级)

### Locale 检测逻辑

```python
# Bento Framework: bento.runtime.middleware.LocaleMiddleware
# 自动从 Accept-Language 头部检测 locale
# 支持配置 default_locale 和 supported_locales

app.add_middleware(
    LocaleMiddleware,
    default_locale="zh-CN",
    supported_locales=["en-US", "zh-CN"],
)
```

### 中间件顺序

```
1. Security (认证)
2. LocaleMiddleware (i18n) ← Bento Framework 提供
3. Tenant (多租户)
4. CORS
5. Idempotency
6. Rate Limiting
7. Structured Logging
8. Tracing
9. Request ID
```

**LocaleMiddleware 配置**:
```python
from bento.runtime.middleware import LocaleMiddleware

app.add_middleware(
    LocaleMiddleware,
    default_locale="zh-CN",           # 默认语言
    supported_locales=["en-US", "zh-CN"],  # 支持的语言列表
)
```

---

## 🔄 禁用 i18n

如果不需要 i18n 支持，可以：

### 方法 1: 移除 renderer 注册

在 `runtime/config/runtime_config.py` 中注释掉：

```python
# renderer = MessageRenderer(CATALOG, default_locale="zh-CN")
# set_global_message_renderer(renderer)
```

### 方法 2: 移除 locale middleware

在 `runtime/config/middleware_config.py` 中注释掉：

```python
# app.add_middleware(
#     LocaleMiddleware,
#     default_locale="zh-CN",
#     supported_locales=["en-US", "zh-CN"],
# )
```

---

## 📚 相关文档

- [Bento Framework i18n Guide](/workspace/bento/docs/core/I18N_GUIDE.md)
- [Bento Framework i18n Examples](/workspace/bento/examples/i18n/)
- [Exception System](/workspace/bento/docs/core/EXCEPTIONS.md)

---

## ✅ 总结

my-shop 应用的 i18n 集成特点：

- ✅ **零侵入**: 业务代码无需修改
- ✅ **自动检测**: 根据 Accept-Language 自动切换语言
- ✅ **完整覆盖**: 框架错误码 + 业务错误码全部翻译
- ✅ **易于扩展**: 只需在 catalog.py 添加翻译
- ✅ **可选功能**: 可随时启用/禁用
- ✅ **默认中文**: 符合国内用户习惯

**现在所有异常消息都会根据用户的语言偏好自动显示中文或英文！** 🎉
