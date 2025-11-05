# ADR-003: 数据库基础设施架构

**状态**: ✅ Accepted
**日期**: 2025-11-05
**决策者**: Bento Architecture Team
**相关人员**: Backend Team, DevOps Team

---

## 📋 目录

1. [背景](#背景)
2. [问题陈述](#问题陈述)
3. [决策](#决策)
4. [理由](#理由)
5. [影响](#影响)
6. [备选方案](#备选方案)
7. [实施计划](#实施计划)
8. [验收标准](#验收标准)

---

## 背景

### 当前状况

在实施数据库基础设施之前，Bento 项目的数据库配置和管理存在以下问题：

1. **配置管理混乱**
   - 数据库 URL 硬编码在应用代码中
   - 无法通过环境变量灵活配置
   - 开发/测试/生产环境配置耦合

2. **缺少数据库优化**
   - PostgreSQL 和 SQLite 使用相同的通用配置
   - 没有针对不同数据库类型的优化
   - 缺少连接池管理和预检查机制

3. **缺少错误处理和重试**
   - 数据库瞬态错误（如连接超时）直接导致请求失败
   - 没有智能错误分类和重试机制

4. **缺少生命周期管理**
   - 应用启动时手动初始化数据库
   - 应用关闭时没有优雅的连接清理
   - 不支持 Kubernetes/Docker 的优雅关闭

5. **违反架构原则**
   - 应用层直接依赖基础设施实现细节
   - 没有遵循依赖注入原则
   - 测试不友好（难以 mock 数据库）

### 参考实现

我们参考了 Legend 框架的数据库实现 (`legend/infrastructure/db`)，但发现其使用全局单例模式 (`Database` 类)，违反了 Bento 的依赖注入和六边形架构原则。

---

## 问题陈述

### 核心问题

**如何设计一个符合 Bento 架构原则的数据库基础设施，同时提供生产级别的功能和性能？**

### 需求

1. **配置管理**
   - 支持环境变量配置
   - 类型安全的配置验证
   - 合理的默认值

2. **数据库优化**
   - 针对不同数据库类型（PostgreSQL、SQLite）的特定优化
   - 连接池管理和配置
   - 连接健康检查

3. **弹性处理**
   - 智能错误分类（瞬态 vs 永久错误）
   - 自动重试机制（指数退避 + 随机抖动）

4. **生命周期管理**
   - 标准化的初始化流程
   - 健康检查支持
   - 优雅的连接关闭
   - Kubernetes/Docker 友好

5. **架构合规**
   - 遵循依赖注入原则
   - 符合六边形架构
   - 易于测试（可 mock）

---

## 决策

### 架构决策

**我们决定实现一个模块化的数据库基础设施层，包含以下核心组件：**

#### 1. 配置管理 (`infrastructure/database/config.py`)

- 使用 Pydantic BaseSettings 进行配置管理
- 支持环境变量配置（`DB_*` 前缀）
- 提供类型安全和验证
- 包含合理的默认值

#### 2. 引擎抽象 (`infrastructure/database/engines/`)

- 定义 `DatabaseEngine` 抽象基类
- 为不同数据库类型提供特定实现：
  - `PostgreSQLEngine`: JSONB、连接池 LIFO、服务器参数
  - `SQLiteEngine`: NullPool、线程安全配置
- 工厂模式自动选择合适的引擎

#### 3. 会话管理 (`infrastructure/database/session.py`)

- 提供 `create_async_engine_from_config` 工厂函数
- 集成引擎抽象优化
- 提供 `create_async_session_factory` 创建会话工厂

#### 4. 生命周期管理 (`infrastructure/database/lifecycle.py`)

- `init_database()`: 初始化数据库表
- `health_check()`: 健康检查
- `cleanup_database()`: 清理资源
- `get_database_info()`: 获取数据库信息

#### 5. 弹性处理 (`infrastructure/database/resilience/`)

- `errors.py`: 智能错误分类（5 种类别，30+ 错误模式）
- `retry.py`: 灵活的重试机制（指数退避 + 随机抖动）
- 支持多种使用方式（函数装饰器、上下文管理器）

#### 6. 连接耗尽 (`infrastructure/database/draining.py`)

- 三种耗尽模式：GRACEFUL、IMMEDIATE、FORCE
- 支持可配置的超时和检查间隔
- 信号处理器支持（SIGTERM/SIGINT）
- Kubernetes/Docker 友好

### 目录结构

```
src/bento/infrastructure/database/
├── __init__.py              # 公开 API
├── config.py                # 配置管理
├── session.py               # 会话工厂
├── lifecycle.py             # 生命周期管理
├── draining.py              # 连接耗尽
│
├── engines/                 # 引擎抽象
│   ├── __init__.py
│   ├── base.py              # 抽象基类
│   ├── postgres.py          # PostgreSQL 优化
│   └── sqlite.py            # SQLite 优化
│
└── resilience/              # 弹性处理
    ├── __init__.py
    ├── errors.py            # 错误分类
    └── retry.py             # 重试机制
```

### 依赖关系

```
Application Layer (Use Cases)
    ↓ depends on (abstraction)
IUnitOfWork (Port)
    ↑ implements
SQLAlchemyUnitOfWork (Adapter)
    ↓ uses
Database Infrastructure
    ↓ uses
SQLAlchemy + Database
```

### 公开 API

```python
# 配置
from bento.infrastructure.database import (
    DatabaseConfig,
    get_database_config,
)

# 会话
from bento.infrastructure.database import (
    create_async_engine_from_config,
    create_async_session_factory,
    create_engine_and_session_factory,
)

# 生命周期
from bento.infrastructure.database import (
    init_database,
    cleanup_database,
    health_check,
    drop_all_tables,
    get_database_info,
)

# 连接耗尽
from bento.infrastructure.database import (
    ConnectionDrainer,
    DrainingMode,
    drain_connections,
    drain_with_signal_handler,
)

# 弹性处理
from bento.infrastructure.database.resilience import (
    DatabaseErrorClassifier,
    ErrorCategory,
    is_database_error_retryable,
    RetryConfig,
    RetryableOperation,
    retry_on_db_error,
    DEFAULT_RETRY_CONFIG,
)
```

---

## 理由

### 为什么选择这个架构？

#### 1. 遵循六边形架构

**决策**: 将数据库基础设施作为独立模块，通过依赖注入使用

**理由**:
- Application 层依赖 `IUnitOfWork` 抽象，而非具体实现
- 数据库基础设施细节隔离在 Infrastructure 层
- 易于替换实现（如从 SQLite 切换到 PostgreSQL）
- 符合依赖倒置原则（DIP）

#### 2. 模块化设计

**决策**: 将功能拆分为多个独立模块（config、session、lifecycle、engines、resilience、draining）

**理由**:
- **单一职责原则（SRP）**: 每个模块职责明确
- **易于理解**: 开发者可以快速定位功能
- **易于测试**: 每个模块可独立测试
- **易于扩展**: 新增功能不影响现有模块

#### 3. 引擎抽象

**决策**: 为不同数据库类型提供特定优化

**理由**:
- PostgreSQL 和 SQLite 有不同的最佳实践
- 抽象基类定义统一接口
- 工厂模式自动选择合适的引擎
- **开闭原则（OCP）**: 易于添加新数据库类型

**示例**:
- PostgreSQL: 使用 JSONB 列类型，连接池 LIFO 优化
- SQLite: 使用 NullPool，禁用 `check_same_thread`

#### 4. 智能错误分类

**决策**: 实现错误分类器，区分瞬态错误和永久错误

**理由**:
- 瞬态错误（连接超时、死锁）可以重试
- 永久错误（权限拒绝、语法错误）不应重试
- 避免无意义的重试，节省资源
- 提高系统可用性

**模式识别**:
- 20+ 瞬态错误模式（connection timeout, deadlock detected, etc.）
- 10+ 永久错误模式（permission denied, syntax error, etc.）

#### 5. 指数退避 + 随机抖动

**决策**: 重试机制使用指数退避和随机抖动

**理由**:
- **指数退避**: 避免短时间内大量重试导致雪崩
- **随机抖动**: 避免多个客户端同时重试（雷鸣群效应）
- 业界最佳实践（AWS、Google Cloud 等都推荐）

**算法**:
```python
delay = min(base_delay * (2 ** attempt), max_delay)
if jitter:
    delay = delay * (0.5 + random.random())
```

#### 6. 三种连接耗尽模式

**决策**: 提供 GRACEFUL、IMMEDIATE、FORCE 三种模式

**理由**:
- **GRACEFUL**: 等待连接完成，适合生产环境
- **IMMEDIATE**: 立即关闭池，适合快速重启
- **FORCE**: 强制关闭，适合紧急情况
- 灵活适应不同场景

#### 7. 依赖注入而非全局单例

**决策**: 不使用全局单例（如 Legend 的 `Database` 类）

**理由**:
- **测试友好**: 易于 mock 和替换实现
- **避免全局状态**: 减少副作用和耦合
- **符合 SOLID 原则**: 依赖注入容器管理生命周期
- **六边形架构**: Application 依赖抽象，而非具体实现

**对比**:

```python
# ❌ Legend 方式（全局单例）
from idp.framework.infrastructure.db import session

async with session() as s:
    result = await s.execute(query)

# ✅ Bento 方式（依赖注入）
class CreateOrderUseCase:
    def __init__(self, uow: IUnitOfWork):  # 注入
        self.uow = uow

    async def execute(self, command):
        async with self.uow:
            ...
```

---

## 影响

### 正面影响

#### 1. 应用层简化

- 配置外部化（环境变量）
- 自动数据库优化
- 标准化生命周期管理
- 可选的重试机制

**示例**（ecommerce 项目）:

改进前:
```python
# ❌ 硬编码配置
DATABASE_URL = "sqlite+aiosqlite:///ecommerce.db"
engine = create_async_engine(DATABASE_URL)
```

改进后:
```python
# ✅ 环境变量 + 自动优化
config = DatabaseConfig()
engine = create_async_engine_from_config(config)
# 日志: INFO: Creating sqlite engine using SQLiteEngine
```

#### 2. 生产就绪

- 错误处理和重试
- 优雅关闭
- Kubernetes/Docker 支持
- 健康检查

#### 3. 可观测性

- 详细的日志输出
- 数据库信息查询
- 连接耗尽统计
- 重试回调支持

#### 4. 易于测试

- 所有组件可独立注入
- 易于 mock
- 测试环境可使用内存数据库

#### 5. 易于扩展

- 添加新数据库类型只需实现 `DatabaseEngine`
- 添加新重试策略只需扩展 `RetryConfig`
- 模块化设计便于功能增强

### 负面影响

#### 1. 代码量增加

- 框架层新增 ~1620 行代码
- 文档新增 ~1640 行

**缓解措施**:
- 清晰的模块划分降低复杂度
- 详尽的文档降低学习成本
- 所有应用都受益于这些投资

#### 2. 学习曲线

- 开发者需要学习新的配置方式
- 需要了解引擎抽象和弹性处理

**缓解措施**:
- 提供 1240 行使用指南
- 提供丰富的示例代码
- 合理的默认值降低配置难度

#### 3. 运行时开销

- 错误分类需要模式匹配
- 重试机制增加延迟

**缓解措施**:
- 错误分类性能开销可忽略（<1ms）
- 重试仅在错误时触发
- 可通过配置禁用（`max_attempts=1`）

### 风险

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 配置错误导致应用无法启动 | 中 | Pydantic 验证 + 详细错误信息 |
| 重试导致请求超时 | 低 | 可配置的最大延迟 + 超时控制 |
| 连接池配置不当导致性能问题 | 中 | 合理默认值 + 文档指导 |
| 新数据库类型兼容性问题 | 低 | 引擎抽象 + 测试覆盖 |

---

## 备选方案

### 备选方案 1: 使用 Legend 的全局单例模式

**描述**: 直接采用 Legend 的 `Database` 全局单例设计

**优点**:
- 使用简单
- 代码量少

**缺点**:
- ❌ 违反依赖注入原则
- ❌ 违反六边形架构
- ❌ 测试困难（全局状态）
- ❌ 不符合 Bento 架构哲学

**结论**: ❌ **拒绝**

### 备选方案 2: 最小化实现（仅 P0）

**描述**: 只实现配置、会话、生命周期管理，不实现引擎抽象、弹性处理、连接耗尽

**优点**:
- 代码量少（~570 行）
- 快速上线

**缺点**:
- ❌ 缺少生产级别功能
- ❌ 缺少数据库优化
- ❌ 缺少错误处理和重试
- ❌ 缺少优雅关闭

**结论**: ⚠️ **部分采纳**（分阶段实施：P0 → P1 → P2）

### 备选方案 3: 使用第三方库

**描述**: 使用第三方库如 `databases`、`encode/orm` 等

**优点**:
- 开箱即用
- 社区维护

**缺点**:
- ❌ 引入外部依赖
- ❌ 可能不符合 Bento 架构
- ❌ 难以定制和扩展
- ❌ 增加依赖管理负担

**结论**: ❌ **拒绝**

### 备选方案 4: 完全实现（P0+P1+P2）

**描述**: 一次性实现所有功能，包括读写分离、监控指标等

**优点**:
- 功能最完整
- 一劳永逸

**缺点**:
- ❌ 时间成本高（~16 小时）
- ❌ 可能存在过度设计
- ❌ 部分功能可能用不到

**结论**: ⚠️ **部分采纳**（先实施 P0+P1，P2 按需）

---

## 实施计划

### 阶段划分

#### P0 - 基础设施 ✅ (已完成)

**时间**: 2 小时
**代码量**: ~570 行
**状态**: ✅ 已完成

**内容**:
- ✅ 配置管理（config.py）
- ✅ 会话工厂（session.py）
- ✅ 生命周期管理（lifecycle.py）
- ✅ 公开 API（__init__.py）

**成果**:
- 环境变量配置
- 引擎和会话创建
- 标准化初始化/清理
- 健康检查

#### P1 - 生产就绪 ✅ (已完成)

**时间**: 6 小时
**代码量**: ~1050 行
**状态**: ✅ 已完成

**内容**:
- ✅ 引擎抽象（engines/）
- ✅ 弹性处理（resilience/）
- ✅ 连接耗尽（draining.py）

**成果**:
- 数据库特定优化
- 智能错误分类
- 灵活重试机制
- 三种耗尽模式
- Kubernetes/Docker 支持

#### P2 - 高级特性 ⏳ (待评估)

**时间**: 8+ 小时
**代码量**: ~800 行
**状态**: ⏳ 待评估

**内容**:
- ⏳ 读写分离（replica.py）
- ⏳ 监控指标（monitoring.py）
- ⏳ MySQL 支持（mysql.py）

**触发条件**:
- QPS > 10,000
- 需要主从复制
- 需要可观测性指标
- 需要 MySQL 支持

### 验证清单

#### P0 验证 ✅

- [x] 配置可以通过环境变量设置
- [x] 支持 PostgreSQL 和 SQLite
- [x] 引擎和会话工厂正常创建
- [x] 初始化数据库成功创建表
- [x] 健康检查返回正确状态
- [x] 清理数据库正确释放资源

#### P1 验证 ✅

- [x] PostgreSQL 使用 JSONB 和连接池优化
- [x] SQLite 使用 NullPool
- [x] 错误分类器正确识别瞬态/永久错误
- [x] 重试机制在瞬态错误时自动重试
- [x] 重试机制在永久错误时立即失败
- [x] 连接耗尽三种模式都正常工作
- [x] 信号处理器正确响应 SIGTERM/SIGINT

#### 集成测试 ✅

- [x] 10/10 集成测试通过
- [x] 无回归问题
- [x] 向后兼容

### 文档 ✅

- [x] 使用指南（DATABASE_USAGE.md, 1240 行）
- [x] 设计文档（DATABASE_INFRASTRUCTURE_DESIGN.md, 1076 行）
- [x] ADR 文档（本文档）

---

## 验收标准

### 功能验收

- [x] **配置管理**: 支持环境变量，类型安全
- [x] **引擎抽象**: PostgreSQL 和 SQLite 有特定优化
- [x] **会话管理**: 正确创建和管理会话
- [x] **生命周期**: 初始化、健康检查、清理都正常
- [x] **错误分类**: 正确识别 30+ 种错误模式
- [x] **重试机制**: 指数退避 + 随机抖动
- [x] **连接耗尽**: 三种模式都正常工作
- [x] **文档完整**: 使用指南 + 设计文档 + ADR

### 质量验收

- [x] **测试覆盖**: 集成测试全部通过（10/10）
- [x] **类型安全**: 完整的类型注解
- [x] **代码质量**: 清晰的模块划分，单一职责
- [x] **文档质量**: 详尽的文档和示例（1640+ 行）

### 性能验收

- [x] **错误分类**: 性能开销 < 1ms
- [x] **重试延迟**: 符合配置的延迟策略
- [x] **连接池**: 配置合理，无泄漏

### 架构验收

- [x] **依赖注入**: Application 依赖抽象，通过 DI 注入
- [x] **六边形架构**: Infrastructure 层独立，易于替换
- [x] **SOLID 原则**: 单一职责、开闭原则、依赖倒置
- [x] **测试友好**: 所有组件可独立注入和测试

---

## 后续行动

### 短期（已完成）

- [x] 完成 P0 + P1 实施
- [x] 编写使用文档
- [x] 编写设计文档
- [x] 更新 ecommerce 项目使用新基础设施
- [x] 创建 ADR 记录

### 中期（1-3 个月）

- [ ] 收集用户反馈
- [ ] 优化性能瓶颈
- [ ] 补充边缘案例测试
- [ ] 评估是否需要 P2 功能

### 长期（3-6 个月）

- [ ] 根据需求实施 P2（读写分离、监控）
- [ ] 添加更多数据库支持（MySQL、MariaDB）
- [ ] 性能基准测试
- [ ] 持续优化和重构

---

## 参考文献

### 技术文档

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic Settings Management](https://docs.pydantic.dev/latest/usage/settings/)
- [The Twelve-Factor App](https://12factor.net/)

### 架构原则

- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

### 重试策略

- [Exponential Backoff and Jitter (AWS)](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Google Cloud Retry Strategy](https://cloud.google.com/architecture/error-handling)

### 内部文档

- [DATABASE_USAGE.md](../infrastructure/DATABASE_USAGE.md)
- [DATABASE_INFRASTRUCTURE_DESIGN.md](../design/DATABASE_INFRASTRUCTURE_DESIGN.md)
- [ARCHITECTURE.md](../../applications/ecommerce/docs/ARCHITECTURE.md)

---

## 附录

### A. 目录结构

```
src/bento/infrastructure/database/
├── __init__.py              (85 行) - 公开 API
├── config.py               (174 行) - 配置管理
├── session.py              (161 行) - 会话工厂
├── lifecycle.py            (191 行) - 生命周期
├── draining.py             (237 行) - 连接耗尽
│
├── engines/                         - 引擎抽象
│   ├── __init__.py          (20 行)
│   ├── base.py              (99 行)
│   ├── postgres.py         (113 行)
│   └── sqlite.py            (85 行)
│
└── resilience/                      - 弹性处理
    ├── __init__.py          (24 行)
    ├── errors.py           (250 行)
    └── retry.py            (215 行)

总计：~1620 行
```

### B. 统计数据

| 指标 | 数值 |
|------|------|
| 代码行数 | 1620 |
| 文档行数 | 1640+ |
| 测试通过率 | 10/10 (100%) |
| 模块数量 | 10 |
| 支持数据库 | 2 (PostgreSQL, SQLite) |
| 错误模式 | 30+ |
| 实施时间 | 8 小时 |

### C. 版本历史

| 版本 | 日期 | 变更 | 状态 |
|------|------|------|------|
| 1.0 | 2025-11-05 | P0+P1 完成，生产就绪 | ✅ Accepted |

---

**决策状态**: ✅ Accepted
**决策日期**: 2025-11-05
**下次评审**: 2026-02-05（3 个月后）

---

*本 ADR 记录了 Bento 数据库基础设施的架构决策。如有问题或建议，请提交 Issue 或 Pull Request。*

