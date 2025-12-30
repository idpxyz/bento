# Outbox 配置外部化指南

## 🎯 概述

Bento Framework 的 Outbox 模块支持完整的配置外部化，允许在不修改代码的情况下调整性能参数和行为。

## 📋 配置参数

### OutboxProjectorConfig

| 参数 | 默认值 | 说明 | 环境变量 |
|------|--------|------|----------|
| **批量处理** | | | |
| `batch_size` | 200 | 每批处理的事件数量 | `BENTO_OUTBOX_BATCH_SIZE` |
| `max_concurrent_projectors` | 5 | 最大并发投影器数量 | `BENTO_OUTBOX_MAX_CONCURRENT_PROJECTORS` |
| **轮询间隔** | | | |
| `sleep_busy` | 0.1 | 有事件时轮询间隔(秒) | `BENTO_OUTBOX_SLEEP_BUSY` |
| `sleep_idle` | 1.0 | 无事件时基础间隔(秒) | `BENTO_OUTBOX_SLEEP_IDLE` |
| `sleep_idle_max` | 5.0 | 无事件时最大间隔(秒) | `BENTO_OUTBOX_SLEEP_IDLE_MAX` |
| `error_retry_delay` | 2.0 | 出错后重试间隔(秒) | `BENTO_OUTBOX_ERROR_RETRY_DELAY` |
| **重试策略** | | | |
| `max_retry_attempts` | 5 | 最大重试次数 | `BENTO_OUTBOX_MAX_RETRY_ATTEMPTS` |
| `backoff_multiplier` | 2 | 退避倍数 | `BENTO_OUTBOX_BACKOFF_MULTIPLIER` |
| `backoff_base_seconds` | 5 | 退避基础秒数 | `BENTO_OUTBOX_BACKOFF_BASE_SECONDS` |
| `backoff_max_exponent` | 5 | 退避最大指数 | `BENTO_OUTBOX_BACKOFF_MAX_EXPONENT` |
| **状态配置** | | | |
| `status_new` | "NEW" | 新事件状态 | `BENTO_OUTBOX_STATUS_NEW` |
| `status_sent` | "SENT" | 已发送状态 | `BENTO_OUTBOX_STATUS_SENT` |
| `status_failed` | "FAILED" | 失败状态 | `BENTO_OUTBOX_STATUS_FAILED` |
| `status_dead` | "DEAD" | 死信状态 | `BENTO_OUTBOX_STATUS_DEAD` |
| **多租户** | | | |
| `default_tenant_id` | "default" | 默认租户ID | `BENTO_OUTBOX_DEFAULT_TENANT_ID` |

### OutboxConfig (存储配置)

| 参数 | 默认值 | 说明 | 环境变量 |
|------|--------|------|----------|
| `table_name` | "outbox" | Outbox 表名 | `BENTO_OUTBOX_STORAGE_TABLE_NAME` |
| `max_topic_length` | 128 | Topic 最大长度 | `BENTO_OUTBOX_STORAGE_MAX_TOPIC_LENGTH` |
| `max_error_message_length` | 500 | 错误消息最大长度 | `BENTO_OUTBOX_STORAGE_MAX_ERROR_MESSAGE_LENGTH` |

## 🛠️ 使用方式

### 1. 环境变量配置（推荐生产环境）

```bash
# 性能调优
export BENTO_OUTBOX_BATCH_SIZE=1000
export BENTO_OUTBOX_SLEEP_BUSY=0.05

# 可靠性配置
export BENTO_OUTBOX_MAX_RETRY_ATTEMPTS=10
export BENTO_OUTBOX_BACKOFF_MULTIPLIER=2

# 多租户
export BENTO_OUTBOX_DEFAULT_TENANT_ID=production
```

```python
# 自动从环境变量加载
from bento.config.outbox import OutboxProjectorConfig
config = OutboxProjectorConfig.from_env()
```

### 2. 代码配置（推荐开发/测试环境）

```python
from bento.config.outbox import OutboxProjectorConfig

# 自定义配置
config = OutboxProjectorConfig(
    batch_size=100,
    max_retry_attempts=3,
    sleep_busy=0.1,
    sleep_idle=2.0,
    backoff_multiplier=3,
    default_tenant_id="development"
)

# 使用配置创建OutboxProjector
from bento.infrastructure.projection.projector import OutboxProjector

projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    tenant_id="my_service",  # 可选，默认使用config中的default_tenant_id
    config=config
)
```

### 3. 配置字典（推荐配置文件）

```python
from bento.config.outbox import OutboxProjectorConfig
import yaml

# 从 YAML 配置文件
with open('config.yaml', 'r') as f:
    config_data = yaml.safe_load(f)

config = OutboxProjectorConfig.from_dict(config_data['outbox'])
```

```yaml
# config.yaml
outbox:
  batch_size: 500
  max_retry_attempts: 8
  sleep_busy: 0.1
  sleep_idle: 1.5
  default_tenant_id: "staging"
```

### 4. 全局配置管理

```python
from bento.config.outbox import (
    get_outbox_projector_config,
    set_outbox_projector_config
)

# 设置全局配置（通常在应用启动时）
custom_config = OutboxProjectorConfig(batch_size=300)
set_outbox_projector_config(custom_config)

# 在其他地方获取全局配置
config = get_outbox_projector_config()
```

## 🎚️ 性能调优指南

### 高吞吐量场景

```python
high_throughput_config = OutboxProjectorConfig(
    batch_size=2000,        # 大批量处理
    sleep_busy=0.01,        # 极快轮询
    sleep_idle=0.5,         # 短空闲等待
    max_retry_attempts=15,  # 更多重试保证投递
)
```

### 低延迟场景

```python
low_latency_config = OutboxProjectorConfig(
    batch_size=50,          # 小批量快速处理
    sleep_busy=0.001,       # 毫秒级轮询
    sleep_idle=0.1,         # 短暂空闲
    error_retry_delay=0.5,  # 快速重试
)
```

### 资源节约场景

```python
resource_saving_config = OutboxProjectorConfig(
    batch_size=100,         # 适中批量
    sleep_busy=0.2,         # 较慢轮询
    sleep_idle=5.0,         # 长空闲等待
    sleep_idle_max=60.0,    # 最大1分钟等待
)
```

## 📊 指数退避策略

配置支持灵活的指数退避策略：

```python
# 退避延迟 = backoff_multiplier^retry_count * backoff_base_seconds
# 最大指数限制为 backoff_max_exponent

config = OutboxProjectorConfig(
    backoff_multiplier=2,      # 2倍递增
    backoff_base_seconds=5,    # 基础5秒
    backoff_max_exponent=6     # 最大2^6=64倍
)

# 重试延迟序列: 5s, 10s, 20s, 40s, 80s, 160s, 320s...
```

## 🚀 部署建议

### 开发环境
```bash
export BENTO_OUTBOX_BATCH_SIZE=50
export BENTO_OUTBOX_SLEEP_BUSY=0.1
export BENTO_OUTBOX_MAX_RETRY_ATTEMPTS=3
```

### 测试环境
```bash
export BENTO_OUTBOX_BATCH_SIZE=100
export BENTO_OUTBOX_SLEEP_BUSY=0.05
export BENTO_OUTBOX_MAX_RETRY_ATTEMPTS=5
```

### 生产环境
```bash
export BENTO_OUTBOX_BATCH_SIZE=1000
export BENTO_OUTBOX_SLEEP_BUSY=0.01
export BENTO_OUTBOX_SLEEP_IDLE=2.0
export BENTO_OUTBOX_SLEEP_IDLE_MAX=30.0
export BENTO_OUTBOX_MAX_RETRY_ATTEMPTS=10
export BENTO_OUTBOX_BACKOFF_MULTIPLIER=2
export BENTO_OUTBOX_DEFAULT_TENANT_ID=production
```

## 🔍 监控和调试

### 配置验证

```python
config = get_outbox_projector_config()

# 输出当前配置
print("当前配置:", config.to_dict())

# 验证关键参数
assert config.batch_size > 0, "批量大小必须大于0"
assert config.max_retry_attempts > 0, "重试次数必须大于0"
```

### 性能监控

关键指标：
- **批量利用率**: `实际批量大小 / 配置批量大小`
- **轮询频率**: `events_per_second / batch_size`
- **重试率**: `failed_events / total_events`
- **退避效率**: `avg_retry_delay`

## ✅ 最佳实践

1. **🏭 生产环境**: 使用环境变量，便于不同部署环境调整
2. **🧪 测试环境**: 使用代码配置，便于自动化测试
3. **📋 配置文件**: 复杂场景使用 YAML/JSON 配置文件
4. **📊 性能监控**: 根据监控数据调整配置参数
5. **🔒 安全考虑**: 敏感配置通过环境变量或密钥管理系统
6. **📖 文档化**: 记录每个环境的配置参数和调优原因

## 🚨 注意事项

- `batch_size` 过大可能导致内存压力
- `sleep_busy` 过小会增加 CPU 使用率
- `max_retry_attempts` 过大可能导致垃圾事件堆积
- 配置变更需要重启 OutboxProjector 才能生效（除非使用热更新功能）

## 🔄 API 更新说明

**v1.1+ API 变更**：`OutboxProjector` 构造函数参数已更新：

```python
# ❌ 旧API（v1.0）
projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    tenant_id="my_tenant",
    batch_size=200,        # 硬编码参数
    max_retries=5         # 硬编码参数
)

# ✅ 新API（v1.1+）
from bento.config.outbox import OutboxProjectorConfig

# 方式1：使用默认配置
projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    tenant_id="my_tenant"
    # 配置从环境变量自动加载
)

# 方式2：使用自定义配置
config = OutboxProjectorConfig(batch_size=200, max_retry_attempts=5)
projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    tenant_id="my_tenant",
    config=config
)
```

新API的优势：
- ✅ 支持环境变量配置
- ✅ 支持配置模板
- ✅ 支持配置验证
- ✅ 支持热更新（可选）
- ✅ 更好的类型安全
