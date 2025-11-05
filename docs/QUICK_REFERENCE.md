# Bento Framework - 迁移快速参考

> 📌 本文档提供迁移计划的快速查阅和执行清单

---

## 📅 当前状态

| 项目 | 状态 | 更新时间 |
|------|------|---------|
| **迁移计划** | 📝 已制定 | 2025-01-04 |
| **当前阶段** | Phase 0 | - |
| **预计完成** | v1.0.0 | 2025 Q2-Q3 |
| **总工作量** | 14-20 周 | - |

---

## 🎯 7 个迁移阶段（Phase）

### ✅ Phase 0: 准备阶段（1 周）
- [ ] 架构文档
- [ ] 开发环境
- [ ] 目录结构
- [ ] 测试框架

### ⏳ Phase 1: 端口层定义（2-3 周）
- [ ] Domain Ports（Repository, Specification, EventPublisher）
- [ ] Application Ports（UoW, Cache, MessageBus, Mapper）
- [ ] 文档和验证

### ⏳ Phase 2: 持久化层迁移（4-6 周）⭐ 核心
- [ ] Specification 实现
- [ ] **Interceptor 系统**（最重要）
- [ ] SQLAlchemy Repository
- [ ] UnitOfWork 完整实现
- [ ] Outbox 整合

### ⏳ Phase 3: Mapper 系统（2-3 周）
- [ ] Mapper Core
- [ ] Registry & Builder
- [ ] DTO/PO/VO Base

### ⏳ Phase 4: Cache 系统（1-2 周）
- [ ] Cache Manager
- [ ] Backends（Memory, Redis）
- [ ] Policies（LRU, LFU, Adaptive）

### ⏳ Phase 5: Messaging 系统（2-3 周）
- [ ] MessageBus Core
- [ ] Kafka/Pulsar 适配器
- [ ] Codec 系统

### ⏳ Phase 6: 其他基础设施（2-3 周）
- [ ] Config 系统
- [ ] Logger 系统
- [ ] Observability
- [ ] Identity & Storage（可选）

### ⏳ Phase 7: 完善和优化（2-3 周）
- [ ] 文档完善
- [ ] 示例项目
- [ ] 性能优化
- [ ] 发布准备

---

## 📂 核心迁移源文件映射

### Persistence（持久化）
| Old 源文件 | 迁移目标 | 优先级 |
|-----------|---------|-------|
| `old/persistence/specification/` | `src/adapters/persistence/specification/` | ⭐⭐⭐⭐⭐ |
| `old/persistence/sqlalchemy/interceptor/` | `src/adapters/persistence/interceptor/` | ⭐⭐⭐⭐⭐ |
| `old/persistence/sqlalchemy/repository/base.py` | `src/adapters/persistence/sqlalchemy/repository.py` | ⭐⭐⭐⭐⭐ |
| `old/persistence/sqlalchemy/uow.py` | `src/adapters/persistence/sqlalchemy/uow.py` | ⭐⭐⭐⭐⭐ |

### Mapper（映射）
| Old 源文件 | 迁移目标 | 优先级 |
|-----------|---------|-------|
| `old/mapper/core/` | `src/adapters/mapper/core/` | ⭐⭐⭐⭐ |
| `old/mapper/registry/` | `src/adapters/mapper/registry/` | ⭐⭐⭐ |

### Cache（缓存）
| Old 源文件 | 迁移目标 | 优先级 |
|-----------|---------|-------|
| `old/cache/core/` | `src/adapters/cache/core/` | ⭐⭐⭐⭐ |
| `old/cache/backends/` | `src/adapters/cache/backends/` | ⭐⭐⭐⭐ |
| `old/cache/policies/` | `src/adapters/cache/policies/` | ⭐⭐⭐ |

### Messaging（消息）
| Old 源文件 | 迁移目标 | 优先级 |
|-----------|---------|-------|
| `old/messaging_pulsar/` | `src/adapters/messaging/pulsar/` | ⭐⭐⭐⭐⭐ |
| `old/messaging_pulsar/codec/` | `src/adapters/messaging/codec/` | ⭐⭐⭐⭐ |
| `old/messaging-kafka/` | `src/adapters/messaging/kafka/` | ⭐⭐⭐ (可选) |

---

## 🔑 关键决策点

### 1. Port 定义原则
```python
# ✅ 正确：使用 Protocol
from typing import Protocol

class Repository(Protocol):
    async def save(self, entity: Entity) -> None: ...

# ❌ 错误：使用抽象类
from abc import ABC, abstractmethod

class Repository(ABC):  # ❌ 不要在 Port 中使用 ABC
    @abstractmethod
    async def save(self, entity: Entity) -> None: ...
```

### 2. 依赖方向
```python
# ✅ 正确：内层不依赖外层
# src/domain/entity.py
from bento.domain.ports.repository import Repository  # Protocol

class User(Entity):
    ...

# ❌ 错误：内层依赖外层
# src/domain/entity.py
from bento.adapters.persistence.sqlalchemy.repository import SqlRepository  # ❌
```

### 3. import-linter 验证
```bash
# 每次修改后都要验证
uv run import-linter

# 预期结果：
# ✅ Hexagonal layering: PASSED
# ✅ Domain ports are protocols: PASSED
# ✅ Application ports are protocols: PASSED
# ✅ No adapters into domain or application: PASSED
```

---

## 🧪 测试策略

### 单元测试
```python
# 测试端口实现（Adapter）
# tests/unit/adapters/persistence/test_repository.py

async def test_repository_save():
    repo = SqlAlchemyRepository(session, UserPO, interceptor_chain)
    user = User.create(...)
    await repo.save(user)
    # 断言...
```

### 集成测试
```python
# 测试完整流程
# tests/integration/test_user_flow.py

async def test_create_user_flow():
    async with uow:
        user = User.create(...)
        await repo.save(user)
        await uow.commit()
    
    # 验证数据库
    # 验证事件发布
```

### 性能测试
```python
# 测试性能基准
# tests/performance/benchmark_repository.py

def test_repository_performance():
    # 1000 次插入应该 < 1 秒
    start = time.time()
    for i in range(1000):
        await repo.save(entity)
    assert time.time() - start < 1.0
```

---

## 📋 每日执行清单

### 开发前
- [ ] 拉取最新代码
- [ ] 查看当前 Phase 任务
- [ ] 确认要迁移的模块

### 开发中
- [ ] 先定义 Port（如果还没有）
- [ ] 实现 Adapter
- [ ] 编写单元测试（> 80% 覆盖率）
- [ ] 运行 import-linter 验证
- [ ] 运行 mypy 验证

### 开发后
- [ ] 编写/更新文档
- [ ] 提交代码（附带清晰的 commit message）
- [ ] 更新进度（在 MIGRATION_PLAN.md 中打勾）

---

## 🚨 常见问题

### Q1: 如何判断一个组件应该是 Port 还是 Adapter？
**A**: 
- **Port**：领域/应用需要的抽象契约 → 定义为 `Protocol`
- **Adapter**：Port 的具体实现 → 实现 Protocol

### Q2: 遇到循环依赖怎么办？
**A**: 
1. 检查是否违反了分层原则
2. 使用 `TYPE_CHECKING` 延迟导入
3. 将共享类型移到更内层

### Q3: import-linter 检查失败怎么办？
**A**: 
1. 查看错误信息，找到违反规则的导入
2. 调整导入关系，确保依赖方向正确
3. 如果规则不合理，讨论后调整 `pyproject.toml` 规则

### Q4: 迁移时发现 old 代码有问题怎么办？
**A**: 
1. 记录问题
2. 在迁移时修复（改进，不是照搬）
3. 更新文档说明改进点

---

## 📊 进度跟踪

### Phase 完成度
| Phase | 进度 | 预计完成 | 实际完成 |
|-------|------|---------|---------|
| Phase 0 | ✅ 100% | Week 1 | - |
| Phase 1 | ⏳ 0% | Week 2-4 | - |
| Phase 2 | ⏳ 0% | Week 5-10 | - |
| Phase 3 | ⏳ 0% | Week 11-13 | - |
| Phase 4 | ⏳ 0% | Week 14-15 | - |
| Phase 5 | ⏳ 0% | Week 16-18 | - |
| Phase 6 | ⏳ 0% | Week 19-21 | - |
| Phase 7 | ⏳ 0% | Week 22-24 | - |

### 核心模块完成度
| 模块 | 单元测试 | 集成测试 | 文档 | 状态 |
|------|---------|---------|------|------|
| Specification | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |
| Interceptor | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |
| Repository | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |
| UoW | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |
| Mapper | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |
| Cache | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |
| Messaging | ⏳ 0% | ⏳ 0% | ⏳ 0% | 未开始 |

---

## 🔗 相关文档

| 文档 | 说明 |
|------|------|
| [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) | 完整迁移计划（详细） |
| [TARGET_STRUCTURE.md](./architecture/TARGET_STRUCTURE.md) | 目标目录结构 |
| [roadmap.md](./roadmap.md) | 项目路线图 |

---

## 💡 每周同步会议 Agenda

### 1. 进度回顾（15 分钟）
- 上周完成的任务
- 遇到的问题和解决方案
- 延迟的原因

### 2. 本周计划（10 分钟）
- 本周要完成的任务
- 预计的挑战
- 需要的支持

### 3. 技术讨论（20 分钟）
- 架构决策
- 设计问题
- 代码评审

### 4. 风险评估（10 分钟）
- 识别风险
- 制定应对计划

### 5. 下周规划（5 分钟）

---

**最后更新**：2025-01-04

**维护者**：请在每周会议后更新本文档

