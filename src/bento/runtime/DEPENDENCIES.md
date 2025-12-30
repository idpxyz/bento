# Bento Runtime 依赖说明

## 必需依赖

以下依赖是运行 Bento Runtime 所必需的：

```toml
[dependencies]
python = "^3.11"
fastapi = "^0.104.0"
sqlalchemy = "^2.0.0"
pydantic = "^2.0.0"
```

---

## 可选依赖

### 1. OpenTelemetry (可观测性)

如果你需要使用 `with_otel_tracing()` 或 `with_otel_metrics()`，需要安装 OpenTelemetry 相关包。

#### 基础包

```bash
pip install opentelemetry-api opentelemetry-sdk
```

或使用 uv:

```bash
uv pip install opentelemetry-api opentelemetry-sdk
```

#### Jaeger 导出器

```bash
pip install opentelemetry-exporter-jaeger
```

#### OTLP 导出器

```bash
pip install opentelemetry-exporter-otlp
```

#### Prometheus 导出器

```bash
pip install opentelemetry-exporter-prometheus
```

#### 完整安装

```bash
pip install \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-exporter-jaeger \
  opentelemetry-exporter-otlp \
  opentelemetry-exporter-prometheus
```

#### 使用示例

```python
from bento.runtime import RuntimeBuilder

runtime = (
    RuntimeBuilder()
    .with_otel_tracing(
        service_name="my-shop",
        trace_exporter="jaeger",
        jaeger_host="localhost",
        jaeger_port=6831,
    )
    .with_otel_metrics(
        metrics_exporter="prometheus",
        prometheus_port=8000,
    )
    .build_runtime()
)
```

#### 不安装 OpenTelemetry 的影响

如果不安装 OpenTelemetry 包：
- ✅ Bento Runtime 可以正常运行
- ⚠️ 调用 `with_otel_tracing()` 或 `with_otel_metrics()` 会输出警告
- ✅ 不会抛出错误，继续正常运行

---

### 2. PostgreSQL 驱动 (数据库)

如果使用 PostgreSQL 数据库，需要安装异步驱动：

```bash
pip install asyncpg
```

#### 使用示例

```python
runtime = (
    RuntimeBuilder()
    .with_database(url="postgresql+asyncpg://user:pass@localhost/db")
    .build_runtime()
)
```

---

### 3. MySQL 驱动 (数据库)

如果使用 MySQL 数据库，需要安装异步驱动：

```bash
pip install aiomysql
```

#### 使用示例

```python
runtime = (
    RuntimeBuilder()
    .with_database(url="mysql+aiomysql://user:pass@localhost/db")
    .build_runtime()
)
```

---

### 4. SQLite (默认)

SQLite 是 Python 内置的，不需要额外安装。

```python
runtime = (
    RuntimeBuilder()
    .with_database(url="sqlite+aiosqlite:///./test.db")
    .build_runtime()
)
```

---

## 开发依赖

### 测试

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Linting

```bash
pip install ruff mypy
```

### 文档

```bash
pip install mkdocs mkdocs-material
```

---

## pyproject.toml 示例

```toml
[project]
name = "my-bento-app"
version = "1.0.0"
dependencies = [
    "bento-framework",
    "fastapi",
    "uvicorn",
]

[project.optional-dependencies]
observability = [
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-exporter-jaeger",
    "opentelemetry-exporter-otlp",
    "opentelemetry-exporter-prometheus",
]
postgres = [
    "asyncpg",
]
mysql = [
    "aiomysql",
]
dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "ruff",
    "mypy",
]
```

### 安装示例

```bash
# 基础安装
pip install my-bento-app

# 带可观测性
pip install my-bento-app[observability]

# 带 PostgreSQL
pip install my-bento-app[postgres]

# 完整安装
pip install my-bento-app[observability,postgres,dev]
```

---

## 依赖检查

你可以在运行时检查可选依赖是否已安装：

```python
import importlib.util

# 检查 OpenTelemetry
has_otel = importlib.util.find_spec("opentelemetry") is not None
print(f"OpenTelemetry available: {has_otel}")

# 检查 asyncpg
has_asyncpg = importlib.util.find_spec("asyncpg") is not None
print(f"AsyncPG available: {has_asyncpg}")
```

---

## 版本兼容性

| 包 | 最低版本 | 推荐版本 | 说明 |
|---|---------|---------|------|
| Python | 3.11 | 3.11+ | 必需 |
| FastAPI | 0.104.0 | 0.104+ | 必需 |
| SQLAlchemy | 2.0.0 | 2.0+ | 必需 |
| Pydantic | 2.0.0 | 2.0+ | 必需 |
| OpenTelemetry | 1.20.0 | 最新 | 可选 |
| AsyncPG | 0.29.0 | 最新 | 可选 |
| AIOMySQL | 0.2.0 | 最新 | 可选 |

---

## 故障排除

### OpenTelemetry 导入错误

**问题**:
```
ImportWarning: OpenTelemetry not installed.
Install with: pip install opentelemetry-api opentelemetry-sdk
```

**解决**:
```bash
pip install opentelemetry-api opentelemetry-sdk
```

### 数据库驱动错误

**问题**:
```
ImportError: No module named 'asyncpg'
```

**解决**:
```bash
pip install asyncpg  # PostgreSQL
# 或
pip install aiomysql  # MySQL
```

### 类型检查错误

**问题**:
```
Type "None" is not assignable to declared type
```

**解决**: 这些是静态类型检查警告，不影响运行时。可以忽略或安装 mypy 修复。

---

## 更多信息

- [Bento Runtime README](./README.md)
- [架构文档](./ARCHITECTURE.md)
- [迁移指南](./MIGRATION.md)
