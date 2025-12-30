# Idempotency Architecture Design

## 问题
Idempotency 应该在 Bento Framework 中实现，还是在具体应用中实现？

## 分析

### 当前状态
- **LOMS**: 在应用层实现完整的 idempotency middleware 和基础设施
- **my-shop**: 刚刚添加了简化版的 idempotency middleware

### 业界最佳实践

#### Stripe API
- 使用 `Idempotency-Key` header
- 24小时内重复请求返回缓存结果
- 框架级别支持

#### AWS SDK
- 自动重试机制
- 客户端生成 idempotency token
- 服务端验证

#### Google Cloud
- 请求 ID 机制
- 服务端去重
- 框架级别支持

## 推荐方案：混合架构

### Bento Framework 提供（基础设施层）

```python
# bento/runtime/middleware/idempotency.py
class IdempotencyMiddleware:
    """Framework-level idempotency middleware.

    Provides:
    - Request deduplication
    - Response caching
    - Configurable behavior
    """

    def __init__(
        self,
        header_name: str = "X-Idempotency-Key",
        ttl_seconds: int = 86400,  # 24 hours
        storage: IdempotencyStorage | None = None,
    ):
        ...

# bento/persistence/idempotency/storage.py
class IdempotencyStorage(Protocol):
    """Storage interface for idempotency records."""

    async def get(self, key: str) -> IdempotencyRecord | None:
        ...

    async def set(self, key: str, record: IdempotencyRecord) -> None:
        ...

# bento/persistence/idempotency/models.py
@dataclass
class IdempotencyRecord:
    """Idempotency record model."""

    idempotency_key: str
    request_hash: str
    status: str  # IN_PROGRESS, SUCCEEDED, FAILED
    response_status: int | None
    response_body: str | None
    created_at: datetime
    expires_at: datetime
```

### 应用层配置（my-shop, loms）

```python
# applications/my-shop/runtime/bootstrap_v2.py
from bento.runtime.middleware.idempotency import IdempotencyMiddleware
from bento.persistence.idempotency.storage import DatabaseStorage

def create_app() -> FastAPI:
    app = runtime.create_fastapi_app(...)

    # Optional: Enable idempotency middleware
    if settings.enable_idempotency:
        storage = DatabaseStorage(session_factory)
        app.middleware("http")(
            IdempotencyMiddleware(
                header_name="X-Idempotency-Key",
                ttl_seconds=86400,
                storage=storage,
            )
        )

    return app
```

### 配置文件

```python
# applications/my-shop/config/settings.py
class Settings(BaseSettings):
    # Idempotency settings
    enable_idempotency: bool = True
    idempotency_header: str = "X-Idempotency-Key"
    idempotency_ttl: int = 86400  # 24 hours
```

## 实现路线图

### Phase 1: Framework 基础设施（优先级：高）
- [ ] 创建 `bento.persistence.idempotency` 模块
- [ ] 实现 `IdempotencyRecord` 模型
- [ ] 实现 `IdempotencyStorage` 接口
- [ ] 实现 `DatabaseStorage` 实现

### Phase 2: Framework Middleware（优先级：高）
- [ ] 创建 `bento.runtime.middleware.idempotency` 模块
- [ ] 实现 `IdempotencyMiddleware`
- [ ] 支持配置化
- [ ] 添加测试

### Phase 3: 应用集成（优先级：中）
- [ ] 更新 my-shop 使用框架 middleware
- [ ] 更新 loms 使用框架 middleware
- [ ] 添加配置选项
- [ ] 更新文档

### Phase 4: 高级特性（优先级：低）
- [ ] 支持 Redis 存储
- [ ] 支持自定义存储
- [ ] 支持细粒度控制（装饰器）
- [ ] 性能优化

## 优势

### 对 Framework
1. **标准化**: 统一的 idempotency 实现
2. **可复用**: 所有应用都可使用
3. **可维护**: 集中维护和升级

### 对应用
1. **简单**: 只需配置即可启用
2. **灵活**: 可选择是否启用
3. **可定制**: 可自定义存储和行为

## 迁移策略

### 当前 my-shop 实现
```python
# shared/infrastructure/idempotency_middleware.py
# 保留作为临时方案，直到框架实现完成
```

### 迁移到框架后
```python
# 删除应用层实现
# 使用框架提供的 middleware
from bento.runtime.middleware.idempotency import IdempotencyMiddleware
```

## 结论

**推荐在 Bento Framework 中实现 idempotency 基础设施**，原因：

1. ✅ **通用需求**: 几乎所有生产应用都需要 idempotency
2. ✅ **标准化**: 避免每个应用重复实现
3. ✅ **最佳实践**: 框架级别保证正确性
4. ✅ **可选性**: 应用可选择是否启用
5. ✅ **灵活性**: 支持自定义配置和存储

**实现优先级**: 高（应该在 Bento Framework v1.0 中包含）

## 参考

- [Stripe API Idempotency](https://stripe.com/docs/api/idempotent_requests)
- [AWS SDK Retry Strategy](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
- [Google Cloud Request IDs](https://cloud.google.com/apis/design/design_patterns#request_duplication)
- LOMS implementation: `/workspace/bento/applications/loms/shared/platform/runtime/idempotency_middleware.py`
