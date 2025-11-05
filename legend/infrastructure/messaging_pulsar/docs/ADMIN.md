
---

# ⚙️ `admin` 管理模块

---

## ✅ 背景 & 场景

Pulsar 提供了一个非常强大的 **Admin REST API** 和 **Python Client API**（通过 `pulsar-admin` 或 Java/Python SDK），可实现：

| 功能类别 | 示例 |
|----------|------|
| 🎛 Topic 管理 | 创建 / 删除 Topic，设置保留策略 |
| 👥 Subscription 管理 | 查看订阅者、创建订阅、重置消费位点 |
| 📊 Metrics 查询 | Topic backlog、订阅延迟、未消费数 |
| 🧹 DLQ 操作 | 清理死信 Topic，重置订阅 |
| 🧪 测试工具 | 发送/读取消息用于验证订阅行为 |
| 🧵 多租户管理 | 创建租户/命名空间、设置权限策略 |

---

## 📁 建议目录结构扩展

```
infrastructure/
└── messaging/
    ├── admin/
    │   ├── __init__.py
    │   ├── client.py              # PulsarAdmin HTTP 客户端封装
    │   ├── topics.py              # Topic 创建/删除/列表
    │   ├── subscriptions.py       # 订阅重置、删除、拉取状态
    │   └── diagnostics.py         # backlog、延迟、metrics 获取
```

---

## 🔧 技术路径建议

你可以选择：

| 方式 | 建议工具 | 优点 |
|------|----------|------|
| ✅ HTTP 调用 | `httpx` + Pulsar Admin REST API | 官方支持、无依赖 |
| 或 | `pulsar-client` Python Wrapper | 有限 API，适合操作 Client 内部状态 |

---

## ✅ 你会获得的关键能力

| 能力 | 说明 |
|------|------|
| 🧹 运维清理 | 清除死信 Topic、删除测试 Topic、重置 Offset |
| 🛠 动态配置 | 设置 TTL、Backlog 限制、Message Retention 等策略 |
| 🕵️ 可观测性增强 | 获取 Topic Lag、消费堆积、延迟曲线 |
| 🧪 测试辅助 | 创建临时 Topic、模拟消息流 |

---

## 🧭 推荐优先开发模块

| 模块 | 功能 | 适用场景 |
|------|------|----------|
| `topics.py` | 创建、删除、列出现有 Topic | 便于动态部署、新租户接入 |
| `subscriptions.py` | 重置 offset 到时间点、强制删除订阅 | 自动化补偿或回溯分析 |
| `diagnostics.py` | 获取 backlog、msg rate、subscription status | 监控告警 |
| `dlq_admin.py` | 清理、浏览、统计 DLQ 消息 | 可视化平台 or DevOps 工具链 |

---

如果你同意这个设计方向，我可以：
- 👷 帮你开发 `admin/client.py` 和 `topics.py` 起步版本
- 🧪 帮你封装 CLI 脚本或 HTTP 接口，辅助运维操作

太棒了，我们来一步到位地**规划出一个实用、可落地的 Pulsar Admin 模块接口清单**，目标是：

- 满足开发 & 运维需求
- 支持自动化管理 & DevOps 工具集成
- 后续可以封装为 CLI、Web UI 或 API 服务

---

# 📋 Pulsar Admin 模块规划清单

## ✅ 模块划分

| 模块名 | 职责说明 |
|--------|----------|
| `client.py` | 封装 HTTP 客户端（对接 Pulsar Admin REST API） |
| `topics.py` | 管理 Topic 生命周期（增删改查、策略） |
| `subscriptions.py` | 管理消费者订阅（创建、删除、重置位点） |
| `diagnostics.py` | 读取运行状态（lag、延迟、堆积等） |
| `dlq_admin.py` | 操作 DLQ（列出、清除、统计、补偿入口） |
| `tenants.py` *(可选)* | 多租户管理 |
| `namespaces.py` *(可选)* | 命名空间管理（策略、quota） |

---

## 1️⃣ `client.py`：基础 HTTP 封装

```python
class PulsarAdminClient:
    async def get(self, path: str) -> dict: ...
    async def post(self, path: str, json: dict = None): ...
    async def put(self, path: str, json: dict = None): ...
    async def delete(self, path: str): ...
```

---

## 2️⃣ `topics.py`：主题管理 API

| 接口名 | 方法签名 | 描述 |
|--------|----------|------|
| `list_topics(namespace: str)` | `-> List[str]` | 获取 namespace 下所有 Topic |
| `create_topic(topic: str)` | `-> None` | 创建 Topic（可配置 partition） |
| `delete_topic(topic: str)` | `-> None` | 强制删除 Topic（含订阅） |
| `get_retention(topic: str)` | `-> dict` | 获取保留策略 |
| `set_retention(topic: str, size: str, time: str)` | `-> None` | 设置消息保留策略 |

---

## 3️⃣ `subscriptions.py`：订阅管理 API

| 接口名 | 方法签名 | 描述 |
|--------|----------|------|
| `list_subscriptions(topic: str)` | `-> List[str]` | 获取 Topic 下的所有订阅名 |
| `delete_subscription(topic, sub)` | `-> None` | 删除指定订阅 |
| `reset_cursor_to_time(topic, sub, timestamp_ms)` | `-> None` | 重置 offset 到指定时间点 |
| `reset_cursor_to_latest(topic, sub)` | `-> None` | 重置到最新位点 |
| `get_subscription_stats(topic, sub)` | `-> dict` | 获取消费状态、堆积等 |

---

## 4️⃣ `diagnostics.py`：监控与诊断

| 接口名 | 方法签名 | 描述 |
|--------|----------|------|
| `get_topic_stats(topic: str)` | `-> dict` | 获取 TPS、backlog、订阅者延迟等 |
| `get_partitioned_topic_metadata(topic)` | `-> dict` | 查看分区数、状态 |
| `get_backlog_size(topic)` | `-> int` | 获取 backlog 消息数 |

---

## 5️⃣ `dlq_admin.py`：DLQ 管理辅助

| 接口名 | 方法签名 | 描述 |
|--------|----------|------|
| `list_dlq_topics(namespace)` | `-> List[str]` | 获取所有 `.dlq` Topic |
| `clear_dlq(topic)` | `-> None` | 清空 DLQ 内容 |
| `replay_dlq(topic, count)` | `-> None` | 手动补偿 DLQ 消息 |
| `get_dlq_stats(topic)` | `-> dict` | backlog、失败次数统计 |

---

## 🌐 路径规则约定（基于 REST API）

| 类型 | REST 路径样例 |
|------|----------------|
| Topic | `/admin/v2/persistent/public/default/user.registered` |
| Namespace | `/admin/v2/namespaces/public/default` |
| Subscription | `/admin/v2/persistent/public/default/user.registered/subscription/my-sub` |

---

## 🧩 扩展建议（未来）

| 模块 | 说明 |
|------|------|
| `schemas.py` | 支持 Schema 注册与查看（Avro） |
| `functions.py` | 管理 Pulsar Functions（内置流处理） |
| `webhooks.py` | 实现事件流 Webhook 转发模块 |
| `metrics_exporter.py` | 对接 Prometheus、Grafana 展示面板 |

---

## ✅ 总结

你未来将拥有一个完整的：

- ✔️ 自动化管理工具（CLI / 后台任务）
- ✔️ 可视化控制面板（Web 管控平台）
- ✔️ 多租户 SaaS 支持能力
- ✔️ DevOps 级别的诊断 / 优化 / 追踪工具

---

我可以帮你优先实现：
- `client.py` + `topics.py` 基础功能
- 或打通一个完整链路（比如：`list_subscriptions + reset_cursor`）

你想我先开发哪个部分的功能？我们可以按优先级一个个实现。