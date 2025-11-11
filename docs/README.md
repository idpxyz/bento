# Bento Framework 文档中心

欢迎来到 Bento Framework 文档中心！本文档提供了完整的架构说明、迁移计划和使用指南。

---

## 🔥 最新动态（2025-11-06）

### Legend 融合升级计划

**重大升级**：将 Legend 框架的生产力优势融合到 Bento 中！

**核心亮点**：
- 🚀 **开发效率提升 60-90%**：简单场景 3 行代码搞定
- 🎯 **三种开发模式**：自动化/手动/混合，自由选择
- ✅ **保持架构优势**：严格的六边形架构不变

**快速链接**：
- 📋 [完整融合计划](./migration/FUSION_UPGRADE_PLAN.md) - 16周详细计划
- ⚡ [快速开始指南](./migration/FUSION_QUICK_START.md) - 第一周行动指南
- ✅ [执行检查清单](./migration/FUSION_CHECKLIST.md) - 任务追踪

---

## 📚 文档导航

### 🎯 快速开始

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [**FUSION_QUICK_START.md**](./migration/FUSION_QUICK_START.md) | **融合升级快速开始** 🔥 | 所有人 ⭐⭐⭐⭐⭐ |
| [**QUICK_REFERENCE.md**](./migration/QUICK_REFERENCE.md) | 快速参考和每日清单 | 所有人 ⭐ |
| [**roadmap.md**](./migration/roadmap.md) | 项目路线图 | 项目管理者 |

### 🏗️ 架构文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [**architecture/TARGET_STRUCTURE.md**](./architecture/TARGET_STRUCTURE.md) | 迁移后的目标目录结构 | 开发者 ⭐⭐⭐⭐⭐ |
| architecture/HEXAGONAL.md | 六边形架构详解 | 架构师 |
| architecture/LAYERS.md | 分层规范 | 开发者 |
| architecture/PORTS_AND_ADAPTERS.md | 端口与适配器规范 | 开发者 |

### 📋 迁移计划

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [**MIGRATION_PLAN.md**](./MIGRATION_PLAN.md) | 完整迁移计划（14-20 周） | 所有人 ⭐⭐⭐⭐⭐ |

### 🔌 端口文档（Port）

| 文档 | 说明 | 状态 |
|------|------|------|
| ports/REPOSITORY.md | Repository Port 说明 | ⏳ 待创建 |
| ports/SPECIFICATION.md | Specification Port 说明 | ⏳ 待创建 |
| ports/UOW.md | UnitOfWork Port 说明 | ⏳ 待创建 |
| ports/CACHE.md | Cache Port 说明 | ⏳ 待创建 |
| ports/MESSAGE_BUS.md | MessageBus Port 说明 | ⏳ 待创建 |
| ports/MAPPER.md | Mapper Port 说明 | ⏳ 待创建 |

### 🔧 适配器文档（Adapter）

| 文档 | 说明 | 状态 |
|------|------|------|
| adapters/INTERCEPTOR.md | 拦截器系统详解 | ⏳ 待创建 |
| adapters/SPECIFICATION.md | Specification 实现详解 | ⏳ 待创建 |
| adapters/MAPPER.md | Mapper 系统详解 | ⏳ 待创建 |
| adapters/CACHE.md | Cache 系统详解 | ⏳ 待创建 |
| adapters/MESSAGING.md | Messaging 系统详解 | ⏳ 待创建 |

### 📖 使用指南

| 文档 | 说明 | 状态 |
|------|------|------|
| guides/GETTING_STARTED.md | 快速上手指南 | ⏳ 待创建 |
| guides/REPOSITORY.md | Repository 使用指南 | ⏳ 待创建 |
| guides/SPECIFICATION.md | Specification 使用指南 | ⏳ 待创建 |
| guides/INTERCEPTOR.md | Interceptor 使用指南 | ⏳ 待创建 |
| guides/MAPPER.md | Mapper 使用指南 | ⏳ 待创建 |
| [application/MAPPER_USAGE.md](./application/MAPPER_USAGE.md) | AutoMapper 使用指南 | ✅ 已完成 |

### 🎨 Mermaid 图表

| 图表 | 说明 | 状态 |
|------|------|------|
| [diagrams/hexagonal-architecture.md](./diagrams/hexagonal-architecture.md) | 六边形架构总览 | ✅ 已完成 |
| [diagrams/layered-dependencies.md](./diagrams/layered-dependencies.md) | DDD 分层依赖关系 | ✅ 已完成 |
| [diagrams/component-overview.md](./diagrams/component-overview.md) | 组件关系图 | ✅ 已完成 |
| [diagrams/event-driven-flow.md](./diagrams/event-driven-flow.md) | 事件驱动处理流程 | ✅ 已完成 |
| [diagrams/aggregate-lifecycle.md](./diagrams/aggregate-lifecycle.md) | 聚合生命周期 | ✅ 已完成 |
| [diagrams/usecase-execution-sequence.md](./diagrams/usecase-execution-sequence.md) | 用例执行序列图 | ✅ 已完成 |
| [diagrams/outbox-pattern-flow.md](./diagrams/outbox-pattern-flow.md) | Outbox 模式工作流程 | ✅ 已完成 |
| [diagrams/domain-model-example.md](./diagrams/domain-model-example.md) | 领域模型示例 | ✅ 已完成 |

---

## 🚀 推荐阅读顺序

### 对于新加入的开发者

1. **了解项目**
   - 先阅读主 [README.md](../README.md)
   - 查看 [roadmap.md](./roadmap.md) 了解项目方向

2. **理解架构**
   - ⭐⭐⭐⭐⭐ [architecture/TARGET_STRUCTURE.md](./architecture/TARGET_STRUCTURE.md) - 必读！
   - [diagrams/hexagonal-architecture.md](./diagrams/hexagonal-architecture.md)
   - [diagrams/layered-dependencies.md](./diagrams/layered-dependencies.md)

3. **参与迁移**
   - ⭐⭐⭐⭐⭐ [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) - 必读！
   - ⭐⭐⭐⭐⭐ [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 每日参考！

4. **日常开发**
   - 参考 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 每日执行清单
   - 查阅相关的端口和适配器文档

### 对于架构师/技术负责人

1. **架构决策**
   - [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) - 完整迁移计划
   - [architecture/TARGET_STRUCTURE.md](./architecture/TARGET_STRUCTURE.md) - 目标架构
   - architecture/ADR/ - 架构决策记录（未来创建）

2. **进度跟踪**
   - [roadmap.md](./roadmap.md) - 路线图
   - [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 进度跟踪表

3. **风险管理**
   - [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) - 风险评估章节

---

## 📊 迁移计划概览

### 时间线（14-20 周）

```mermaid
gantt
    title Bento Framework 迁移时间线
    dateFormat  YYYY-MM-DD

    section 准备
    Phase 0: 准备阶段           :p0, 2025-01-06, 1w

    section 核心
    Phase 1: 端口层定义         :p1, after p0, 3w
    Phase 2: 持久化层迁移       :crit, p2, after p1, 6w

    section 扩展
    Phase 3: Mapper 系统        :p3, after p2, 3w
    Phase 4: Cache 系统         :p4, after p3, 2w
    Phase 5: Messaging 系统     :p5, after p4, 3w
    Phase 6: 其他基础设施       :p6, after p5, 3w

    section 完善
    Phase 7: 完善和优化         :p7, after p6, 3w
```

### 核心价值排序

1. ⭐⭐⭐⭐⭐ **Interceptor 系统**（Phase 2）- 最高价值
2. ⭐⭐⭐⭐⭐ **Specification 模式**（Phase 2）- 最高价值
3. ⭐⭐⭐⭐⭐ **BaseRepository**（Phase 2）- 最高价值
4. ⭐⭐⭐⭐⭐ **UnitOfWork 完整实现**（Phase 2）- 最高价值
5. ⭐⭐⭐⭐ **Mapper 系统**（Phase 3）
6. ⭐⭐⭐⭐ **Cache 系统**（Phase 4）
7. ⭐⭐⭐ **Messaging 系统**（Phase 5）

---

## 🎯 关键指标

### 架构合规性
- ✅ import-linter 检查：100% 通过
- ✅ mypy strict mode：100% 通过
- ✅ 分层依赖方向：100% 正确

### 测试覆盖率
- 🎯 单元测试：> 80%
- 🎯 集成测试：核心场景全覆盖
- 🎯 性能测试：性能 ≥ old 实现的 90%

### 文档完整性
- 🎯 架构文档：100% 完成
- 🎯 端口文档：100% 完成
- 🎯 适配器文档：100% 完成
- 🎯 使用指南：100% 完成

---

## 🔧 开发工具

### 代码质量检查

```bash
# import-linter 检查（分层依赖）
uv run import-linter

# mypy 类型检查
uv run mypy src/

# ruff 代码规范
uv run ruff check src/

# pytest 测试
uv run pytest tests/
```

### 文档预览

```bash
# Mermaid 图表预览
# 使用 VS Code 插件：Markdown Preview Mermaid Support
# 或访问：https://mermaid.live/
```

---

## 📞 获取帮助

### 技术问题
- 查阅相关文档
- 查看示例代码（`examples/` 目录）
- 参考 old 实现（`old/` 目录）

### 架构问题
- 阅读架构文档（`docs/architecture/`）
- 查看 Mermaid 图表（`docs/diagrams/`）
- 参考 ADR（架构决策记录）

### 进度问题
- 查看 [roadmap.md](./roadmap.md)
- 参考 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 进度表

---

## 📝 文档贡献

### 如何添加新文档

1. **确定文档类型**
   - 架构文档 → `docs/architecture/`
   - 端口文档 → `docs/ports/`
   - 适配器文档 → `docs/adapters/`
   - 使用指南 → `docs/guides/`
   - 图表 → `docs/diagrams/`

2. **使用 Markdown 格式**
   - 遵循现有文档的格式
   - 使用清晰的标题层次
   - 添加代码示例

3. **更新索引**
   - 在本文档（README.md）中添加链接
   - 在相关文档中添加交叉引用

4. **提交 PR**
   - 清晰的 commit message
   - 附带说明和截图（如果需要）

---

## 🏆 里程碑

### v0.1.0a1（当前）
- ✅ DDD 核心抽象
- ✅ 六边形架构基础
- ✅ 基础文档和图表

### v1.0.0（目标）
- 🎯 完成 old 架构迁移
- 🎯 拦截器系统
- 🎯 Specification 模式
- 🎯 Mapper 系统
- 🎯 完整的适配器实现
- 🎯 完善的文档和示例
- 🎯 生产环境就绪

---

**最后更新**：2025-01-04

**维护者**：请在添加新文档时更新本索引

