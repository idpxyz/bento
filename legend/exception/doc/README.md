架构理念、目录结构、异常定义与响应、Sentry & TraceId 支持、配置项说明等。

---

# 🧱 异常处理系统（基于 FastAPI + DDD 分层架构）

本模块提供一套**统一的异常处理系统**，支持：

- ✅ DDD 异常分类（Domain / Application / Infrastructure / Interface）
- ✅ 错误码结构化定义（ErrorCode）
- ✅ Trace ID 链路追踪支持
- ✅ Sentry 异常上报（支持分层采样率）
- ✅ API 响应格式统一
- ✅ 日志输出、异常链追踪（`__cause__`）
- ✅ 是否暴露 message 可配置控制
- ✅ 异步后台任务异常处理支持

---

## 📦 模块目录结构

```
src/idp/framework/exception/
├── __init__.py                    # 模块导出
├── base.py                        # IDPBaseException：统一基类
├── classified.py                  # Domain/Application/Infra/Interface 异常实现
├── metadata.py                    # 异常枚举 + ErrorCode 定义 + ExceptionContext
├── handler.py                     # FastAPI 异常处理器
├── support.py                     # 异步后台任务异常处理支持
├── sentry/                        # Sentry 集成
│   ├── __init__.py
│   └── reporter.py                # SentryReporter 异常上报实现
├── code/                          # 模块化错误码定义
│   ├── __init__.py
│   ├── common.py                  # 通用错误码
│   ├── user.py                    # 用户相关错误码
│   └── ...                        # 其他领域错误码
└── demo/                          # 使用示例
    ├── basic.py                   # 基础用法示例
    ├── async_demo.py              # 异步处理示例
    └── ...
```

---

## 🧱 异常定义方式

### ✅ 错误码结构

```python
from http import HTTPStatus
from idp.framework.exception.metadata import ErrorCode

USER_ALREADY_EXISTS = ErrorCode("100101", "用户已存在", HTTPStatus.CONFLICT)
```

### ✅ 抛出异常（直接使用分类异常）

```python
from idp.framework.exception.classified import DomainException
from idp.framework.exception.code.user import UserErrorCode

# 简洁明了的异常创建
raise DomainException(
    code=UserErrorCode.USER_ALREADY_EXISTS, 
    details={"email": "user@example.com"}
)

# 支持异常链
try:
    # 数据库操作
    db.execute_query()
except Exception as e:
    raise InfrastructureException(
        code=CommonErrorCode.DATABASE_ERROR,
        details={"operation": "find_user"},
        cause=e  # 捕获原始异常作为cause
    )
```

---

## 🔁 响应结构（标准格式）

```json
{
  "code": "100101",
  "message": "用户已存在",
  "category": "DOMAIN",
  "severity": "ERROR",
  "details": {
    "email": "user@example.com"
  },
  "trace_id": "abc-123"
}
```

> 可配置：是否对外暴露 `message`（如生产环境隐藏）

---

## 🧪 异常链（底层异常支持）

```python
try:
    repo.find_user()
except Exception as e:
    raise InfrastructureException(
        code=CommonErrorCode.DATABASE_ERROR, 
        cause=e
    )
```

日志/Sentry 会显示 `Caused by: <底层异常>`，但对外响应结构不变。

---

## 🔄 异步任务异常处理

框架提供了全面的异步任务异常处理支持：

```python
from idp.framework.exception.support import background_task_context, background_task_handler

# 方法1：使用异步上下文管理器
async def process_data():
    async with background_task_context("process_data", error_code=CommonErrorCode.TASK_FAILED):
        # 任务代码...异常会被自动处理并上报
        data = await fetch_data()
        await process_data(data)

# 方法2：使用装饰器
@background_task_handler(error_code=CommonErrorCode.TASK_FAILED)
async def scheduled_task():
    # 任务代码...
    await complex_operation()
```

---

## 🛰️ Trace ID 注入

通过中间件为每个请求注入 `request.state.trace_id`，响应中统一返回。

```python
from idp.framework.exception.demo.request_context import TraceIDMiddleware

app = FastAPI()
app.add_middleware(TraceIDMiddleware)
```

---

## 🚨 Sentry 上报机制

- ✅ 可开关：通过 `.env` 中 `EXCEPTION_SENTRY_ENABLED`
- ✅ 上报异常分类、错误码、trace_id、details
- ✅ 支持采样率控制（不同类型可配置）

```python
# 异常处理器中自动上报
await sentry_reporter.report_exception(
    exc=exc,
    category=category,
    request=request,
    trace_id=trace_id,
    tags={"error_code": exc.context.code}
)
```

---

## 🔁 分类型采样率配置（config.py）

| 异常类型 | 采样率变量 | 示例值 |
|----------|------------|--------|
| DOMAIN | `EXCEPTION_SAMPLE_RATE_DOMAIN` | 1.0 |
| APPLICATION | `EXCEPTION_SAMPLE_RATE_APPLICATION` | 1.0 |
| INFRASTRUCTURE | `EXCEPTION_SAMPLE_RATE_INFRASTRUCTURE` | 0.1 |
| INTERFACE | `EXCEPTION_SAMPLE_RATE_INTERFACE` | 0.5 |

---

## ⚙️ 配置项（支持 .env）

```ini
EXCEPTION_SENTRY_ENABLED=true
EXCEPTION_SAMPLE_RATE_DOMAIN=1.0
EXCEPTION_SAMPLE_RATE_INFRASTRUCTURE=0.1
EXCEPTION_ENVIRONMENT=production
EXCEPTION_PROJECT=idp-framework
EXCEPTION_EXPOSE_MESSAGE=false
EXCEPTION_INCLUDE_CAUSE=true
EXCEPTION_DEBUG_MODE=false
```

---

## ✅ FastAPI 集成方式

```python
from fastapi import FastAPI
from idp.framework.exception.handler import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

---

## 📚 Swagger 文档集成

```python
from idp.framework.exception.swagger import common_error_response

@app.get(
    "/users/{user_id}",
    responses=common_error_response  # 添加通用错误响应文档
)
async def get_user(user_id: str):
    # ...
```

---

## 📚 扩展建议

- ✅ 支持多语言错误消息（如 error_code -> message 映射）
- ✅ 自动生成错误码文档（CLI 工具）
- ✅ 接入全链路追踪（OpenTelemetry / Skywalking）

---

示例代码可以查看 `demo/` 目录：
- `basic.py` - 基础异常处理示例
- `async_demo.py` - 异步任务异常处理示例
- `simplified_demo.py` - 简化异常处理示例