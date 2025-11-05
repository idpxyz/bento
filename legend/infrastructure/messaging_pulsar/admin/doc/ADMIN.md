非常好，以下是**面向专业开发团队或企业技术文档风格**的完整 `ADMIN.md`，用于指导 Pulsar Admin 模块的使用、维护与扩展。文档具备：

- 架构性清晰
- 目录结构完整
- 功能逐级展开
- 使用案例 + 扩展建议
- 面向 CLI 运维团队友好

---

# 🛠️ Pulsar Admin 管理模块说明文档

> 版本：v0.1.0  
> 作者：后端架构组  
> 上次更新时间：2025-04-01

---

## 📌 模块简介

`messaging_admin` 模块是面向 Apache Pulsar 的通用管理工具集合，基于官方 Admin REST API 封装，提供包括：

- Topic 与命名空间管理
- 消费者订阅管理
- 死信队列（DLQ）操作与消息补偿
- 主题运行状态监控（TPS、Backlog、堆积等）
- 命令行运维工具（`pulsar-admin`）

适用于 CI/CD、补偿平台、异步消息运维面板或开发自测工具。

---

## 📁 项目结构

```
messaging_admin/
├── __init__.py
├── admin/
│   ├── client.py              # Pulsar Admin REST API 封装
│   ├── topics.py              # Topic 管理（创建/删除/策略）
│   ├── subscriptions.py       # 消费订阅管理（重置 offset / 删除）
│   ├── dlq_admin.py           # 死信队列操作（list/clear/replay）
│   └── diagnostics.py         # Topic 运行状态获取
└── cli/
    └── __main__.py            # 系统 CLI 工具 pulsar-admin 入口
```

---

## ⚙️ 环境依赖

| 项目 | 最小版本 | 说明 |
|------|----------|------|
| Python | 3.8+ | 支持 `asyncio` 异步执行 |
| httpx | 0.24+ | 异步 HTTP 客户端 |
| pulsar-client | 官方 Python 包 | 用于 replay 消息 |

### 环境变量建议：

```
PULSAR_ADMIN_URL=http://localhost:8080
PULSAR_AUTH_TOKEN=xxx  # 可选
```

---

## 🔧 功能模块详解

### 1️⃣ `client.py`：基础 HTTP 封装

封装 Pulsar Admin REST API 的基础请求逻辑：

```python
client = PulsarAdminClient(admin_url="http://localhost:8080")
await client.get("/admin/v2/brokers/health")
```

支持自动带 token、支持全局重试处理。

---

### 2️⃣ `topics.py`：主题管理

```python
from messaging_admin.admin.topics import Topics

topics = Topics(client)
await topics.list_topics("public", "default")
await topics.create_topic("public", "default", "user.registered", partitions=3)
await topics.set_retention("public", "default", "user.registered", 128, 60)
```

| 方法 | 描述 |
|------|------|
| `list_topics()` | 获取某命名空间所有 Topic 名称 |
| `create_topic()` | 创建持久化 Topic，支持分区数 |
| `delete_topic()` | 删除 Topic，支持 `force=true` |
| `set_retention()` | 设置保留大小（MB）与时间（分钟） |
| `get_retention()` | 获取当前策略 |

---

### 3️⃣ `subscriptions.py`：订阅管理

```python
from messaging_admin.admin.subscriptions import Subscriptions

subs = Subscriptions(client)
await subs.list_subscriptions("public", "default", "user.registered")
await subs.reset_cursor_to_latest("public", "default", "user.registered", "default-sub")
```

| 方法 | 功能说明 |
|------|----------|
| `list_subscriptions()` | 获取所有订阅者名称 |
| `delete_subscription()` | 删除某订阅名（可强制） |
| `reset_cursor_to_time()` | 指定时间戳重置 offset |
| `reset_cursor_to_latest()` | 快速跳过 backlog 到当前位点 |
| `get_subscription_stats()` | 获取 backlog/消费速率等状态 |

---

### 4️⃣ `dlq_admin.py`：DLQ 操作（Dead Letter Queue）

```python
from messaging_admin.admin.dlq_admin import DLQAdmin

dlq = DLQAdmin(client)
await dlq.list_dlq_topics("public", "default")
await dlq.replay_dlq("public", "default", "user.registered.dlq", max_messages=5)
```

| 方法 | 功能说明 |
|------|----------|
| `list_dlq_topics()` | 命名空间下所有 `.dlq` Topic |
| `get_dlq_stats()` | backlog、未 ack 计数、消息速率 |
| `clear_dlq()` | 删除 `.dlq` Topic |
| `replay_dlq()` | 将 DLQ 中失败消息重放至原始 Topic |

---

### 5️⃣ `diagnostics.py`：Topic 运行监控

```python
from messaging_admin.admin.diagnostics import Diagnostics

diag = Diagnostics(client)
stats = await diag.get_topic_stats("public", "default", "user.registered")
backlog = await diag.get_backlog_size("public", "default", "user.registered")
```

| 方法 | 说明 |
|------|------|
| `get_topic_stats()` | 包含 subscriptions、msgRate、backlog、delay |
| `get_partitioned_topic_metadata()` | 是否分区 Topic，多少分区 |
| `get_backlog_size()` | 所有订阅 backlog 总和 |

---

## 💻 CLI 工具：`pulsar-admin`

安装后支持：

```bash
$ pulsar-admin --help
```

### 安装方式

1. 项目根目录创建 `setup.cfg`：

```ini
[options.entry_points]
console_scripts =
    pulsar-admin = messaging_admin.cli.__main__:main
```

2. 本地开发安装：

```bash
pip install -e .
```

### 常用命令示例

```bash
# 查看 backlog 数量
pulsar-admin backlog user.registered

# 重放 DLQ 消息
pulsar-admin dlq-replay user.registered.dlq --max 10

# 清空 DLQ
pulsar-admin dlq-clear user.registered.dlq

# 重置订阅消费位点
pulsar-admin reset-sub user.registered default-sub
```

---

## 🧪 测试建议

| 场景 | 建议 |
|------|------|
| 单元测试 | 使用 `pytest-asyncio`，mock httpx.Client |
| 接口稳定性 | 对关键 Topic 创建/删除接口加 retry 模拟 |
| CLI 测试 | 使用 `subprocess.run()` 模拟命令调用验证输出 |

---

## 📈 扩展建议

| 方向 | 说明 |
|------|------|
| 支持 schema 管理 | 注册 Avro/Protobuf schema 接口 |
| 多租户 / 命名空间策略 | 调整命名规范 + 自动配置 quota |
| Prometheus Exporter | 把 backlog/tps 输出为 HTTP 指标接口 |
| Web UI 面板 | 封装 FastAPI + Vue/React 管理平台 |
| 集成认证 | 添加支持 JWT/OAuth token 头配置 |

---

## 🧭 运维建议

| 项目 | 建议策略 |
|------|-----------|
| Topic 命名 | `{bounded_context}.{event}.{version}` |
| `.dlq` Topic 监控 | backlog > 100 自动告警 |
| 订阅清理策略 | 消费 inactive 超过 30 天可自动删除 |
| replay 策略 | 使用 `replay_dlq()` + metrics 标记防止重复发送 |

---

## 📞 联系方式与维护者

| 角色 | 姓名 | 联系方式 |
|------|------|-----------|
| 技术负责人 | 张架构 | zhang.arch@yourcorp.com |
| DevOps 工程师 | 陈运维 | chen.ops@yourcorp.com |
| 消息平台支持 | messaging-team | slack://#pulsar-support |

---

如需打包压缩模板、添加 Makefile/CI 自动化、生成文档网站，可联系维护者协助完成。

如需 Web 管控台支持、补偿任务调度模块、Kafka 兼容方案等，也可在此基础上扩展。需要我导出 Markdown → PDF 文档或项目模板压缩包吗？