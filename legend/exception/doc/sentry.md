太好了！将 Sentry 上报功能封装成一个类 `SentryReporter`，可以带来以下好处：

| 优势 | 说明 |
|------|------|
| ✅ 面向接口编程 | 更适合依赖注入（如在服务类中注入 `reporter`） |
| ✅ 支持 mock 测试 | 在单元测试中替代真实上报逻辑 |
| ✅ 可扩展 | 统一 trace_id、tags、环境参数配置 |
| ✅ 可集中配置 sentry_sdk 初始化参数 |

---

## ✅ 实现方案：`SentryReporter`

📁 `app/core/sentry_logger.py` 更新为：

```python
import sentry_sdk
from typing import Optional, Dict, Any
from fastapi import Request
from app.exceptions.metadata import ErrorCode, ExceptionCategory


class SentryReporter:
    def __init__(self, enabled: bool = True, default_level: str = "error"):
        self.enabled = enabled
        self.level = default_level

    def report_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        tags: Optional[Dict[str, str]] = None,
        extras: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        level: Optional[str] = None,
    ):
        if not self.enabled:
            return

        with sentry_sdk.push_scope() as scope:
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)

            if extras:
                for key, value in extras.items():
                    scope.set_extra(key, value)

            if request:
                scope.set_tag("path", request.url.path)
                scope.set_tag("method", request.method)
                trace_id = trace_id or getattr(request.state, "trace_id", None)

            if trace_id:
                scope.set_tag("trace_id", trace_id)

            scope.level = level or self.level
            sentry_sdk.capture_exception(exc)

    def report_from_error_code(
        self,
        error_code: ErrorCode,
        category: ExceptionCategory,
        request: Optional[Request] = None,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        exception: Optional[Exception] = None,
    ):
        exc = exception or Exception(error_code.message)
        self.report_exception(
            exc=exc,
            request=request,
            tags={
                "error_code": error_code.code,
                "category": category.value,
            },
            extras=extra,
            trace_id=trace_id,
        )
```

---

## ✅ 使用方式

### 1️⃣ 全局实例初始化（可放在 `core/__init__.py`）

```python
from app.core.sentry_logger import SentryReporter

sentry_reporter = SentryReporter(enabled=True)
```

---

### 2️⃣ 在处理器中使用

```python
from app.core.sentry_logger import sentry_reporter

@app.exception_handler(AppBaseException)
async def handle_app_exception(request: Request, exc: AppBaseException):
    trace_id = getattr(request.state, "trace_id", None)
    if not exc.context.trace_id:
        exc.context.trace_id = trace_id

    sentry_reporter.report_exception(
        exc,
        request=request,
        trace_id=trace_id,
        tags={"error_code": exc.context.code, "category": exc.context.category.value},
        extras={"details": exc.context.details}
    )

    return JSONResponse(
        status_code=exc.http_status,
        content=exc.context.model_dump()
    )
```

---

### 3️⃣ 在业务服务或基础设施中使用

```python
from app.core.sentry_logger import sentry_reporter
from app.exceptions.error_codes.common import REDIS_ERROR
from app.exceptions.metadata import ExceptionCategory

sentry_reporter.report_from_error_code(
    error_code=REDIS_ERROR,
    category=ExceptionCategory.INFRASTRUCTURE,
    extra={"operation": "redis.get('key')"},
    trace_id="abc-123"
)
```

---

## ✅ 可扩展性建议

- 可加 `environment`, `user_id`, `project_name` 等配置字段
- 可在 `SentryReporter` 统一做节流采样（如 5% 上报）
- 可做 Mock 类用于 `pytest` 测试替代 sentry_sdk

---

需要我帮你生成一份测试这个 `SentryReporter` 的 mock 单元测试类吗？比如 `MockSentryReporter`？


# 调整后的方案：

太棒了！以下是根据你的需求和我建议扩展后的完整版本，包含：

- ✅ `SentryReporter` 支持 `environment`、`project_name`、`user_id`
- ✅ 自动采样率（如节流上报）
- ✅ Mock 类 `MockSentryReporter`，用于测试替代
- ✅ 工厂函数 `get_sentry_reporter()`，方便依赖注入或替换

---

## ✅ 📄 文件：`app/core/sentry_logger.py`

```python
import sentry_sdk
from typing import Optional, Dict, Any
from fastapi import Request
from app.exceptions.metadata import ErrorCode, ExceptionCategory
import random


class SentryReporter:
    def __init__(
        self,
        enabled: bool = True,
        environment: str = "dev",
        project: str = "idp-gatekeeper",
        default_level: str = "error",
        sample_rate: float = 1.0,
    ):
        self.enabled = enabled
        self.environment = environment
        self.project = project
        self.level = default_level
        self.sample_rate = sample_rate

    def should_sample(self) -> bool:
        return random.random() <= self.sample_rate

    def report_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        tags: Optional[Dict[str, str]] = None,
        extras: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        level: Optional[str] = None,
    ):
        if not self.enabled or not self.should_sample():
            return

        with sentry_sdk.push_scope() as scope:
            # 默认 Tags
            scope.set_tag("environment", self.environment)
            scope.set_tag("project", self.project)

            # 用户标识
            if user_id:
                scope.user = {"id": user_id}

            # 动态 Tags
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)

            # Extras
            if extras:
                for key, value in extras.items():
                    scope.set_extra(key, value)

            # 请求相关
            if request:
                scope.set_tag("path", request.url.path)
                scope.set_tag("method", request.method)
                trace_id = trace_id or getattr(request.state, "trace_id", None)

            # Trace ID
            if trace_id:
                scope.set_tag("trace_id", trace_id)

            scope.level = level or self.level
            sentry_sdk.capture_exception(exc)

    def report_from_error_code(
        self,
        error_code: ErrorCode,
        category: ExceptionCategory,
        request: Optional[Request] = None,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        user_id: Optional[str] = None,
    ):
        exc = exception or Exception(error_code.message)
        self.report_exception(
            exc=exc,
            request=request,
            trace_id=trace_id,
            user_id=user_id,
            tags={
                "error_code": error_code.code,
                "category": category.value,
            },
            extras=extra,
        )


class MockSentryReporter(SentryReporter):
    """用于测试时替代 Sentry 上报，记录调用参数"""

    def __init__(self):
        super().__init__(enabled=False)
        self.captured = []

    def report_exception(self, *args, **kwargs):
        self.captured.append({"args": args, "kwargs": kwargs})

    def report_from_error_code(self, *args, **kwargs):
        self.captured.append({"args": args, "kwargs": kwargs})


# 工厂方法
def get_sentry_reporter(env: str = "dev") -> SentryReporter:
    return SentryReporter(environment=env)
```

---

## ✅ 使用方式一：在全局初始化

```python
from app.core.sentry_logger import get_sentry_reporter

sentry_reporter = get_sentry_reporter(env="production")
```

---

## ✅ 使用方式二：在 handler 中集成

```python
from app.core.sentry_logger import sentry_reporter

@app.exception_handler(AppBaseException)
async def handle_app_exception(request: Request, exc: AppBaseException):
    trace_id = getattr(request.state, "trace_id", None)

    sentry_reporter.report_exception(
        exc=exc,
        request=request,
        trace_id=trace_id,
        tags={"error_code": exc.context.code, "category": exc.context.category.value},
        extras={"details": exc.context.details},
    )

    return JSONResponse(
        status_code=exc.http_status,
        content=exc.context.model_dump()
    )
```

---

## ✅ 在测试中使用 Mock 替代

```python
from app.core.sentry_logger import MockSentryReporter

def test_redis_failure():
    mock = MockSentryReporter()
    try:
        raise Exception("mock error")
    except Exception as e:
        mock.report_exception(exc=e, trace_id="mock-trace")
        assert len(mock.captured) == 1
```

---

需要我也给你生成一个单元测试文件结构（比如 `tests/test_sentry_logger.py`）来测试这套上报逻辑吗？