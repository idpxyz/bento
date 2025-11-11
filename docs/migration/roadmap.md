# Bento Framework 路线图

本文档描述 Bento Framework 的开发路线图和未来规划。

---

## 🚨 重要更新：Legend 融合升级计划 🔥 NEW!

**状态**：📝 计划制定完成 | **预计时长**：12-16 周（3-4 个月）

我们制定了一个**全新的融合升级计划**，将 Legend 框架的生产力优势和 Bento 的架构优势完美结合！

### 🎯 融合理念

**"灵活性 + 生产力 + 类型安全 = 完美框架"**

提供**渐进式**的开发体验：
- 🚀 **快速开发**：零配置自动化（Legend 风格）- 3 行代码
- 🎯 **精确控制**：显式配置（Bento 风格）- 完全控制
- 🔄 **混合模式**：在同一项目中灵活切换

### 核心目标
- ✅ 保持 Bento 的**架构优势**（严格分层、端口与适配器分离、依赖反转）
- ✅ 引入 Legend 的**生产力优势**（AutoMapper、EnhancedRepository、智能事件收集）
- ✅ 实现 **开发效率提升 60-90%**，同时保持架构清晰

### 融合亮点

| 特性 | Legend | Bento | **融合后** |
|------|--------|-------|----------|
| **Mapper** | 自动映射 | 手动映射 | ✅ **三选一**：Auto/Explicit/Hybrid |
| **Repository** | BaseAdapter | 手动实现 | ✅ **EnhancedRepository** 自动CRUD |
| **事件收集** | 全局上下文 | 聚合根内部 | ✅ **双模式** 智能切换 |
| **Specification** | Builder链式 | 声明式 | ✅ **Fluent Builder** + 类型安全 |
| **Use Case** | CommandHandler | 手动实现 | ✅ **BaseUseCase** 自动管理 |

### 详细计划
请查看：
- 🔥 **[Legend 融合升级计划](./FUSION_UPGRADE_PLAN.md)**（推荐！）
- 📋 [Old 架构迁移计划](./MIGRATION_PLAN.md)（原计划）

### 融合时间线
```
Week 1-3:   F1 - Mapper 系统融合         ⭐⭐⭐⭐⭐ 最高优先级
Week 4-7:   F2 - Repository 增强系统     ⭐⭐⭐⭐⭐ 核心功能
Week 8-9:   F3 - 统一事件收集机制        ⭐⭐⭐⭐   重要改进
Week 10-11: F4 - Fluent Specification    ⭐⭐⭐     便利性
Week 12-13: F5 - BaseUseCase 增强        ⭐⭐⭐     便利性
Week 14-16: F6 - 整合和优化              ⭐⭐⭐⭐   质量保证
```

### 成功指标

| 场景 | 当前代码量 | 融合后 | 减少 |
|------|----------|--------|------|
| 简单 Repository | 50 行 | 3 行 | **94% ↓** |
| 复杂 Repository | 100 行 | 30 行 | **70% ↓** |
| Mapper | 40 行 | 15 行 | **62% ↓** |
| Use Case | 50 行 | 20 行 | **60% ↓** |

**完成后的版本号**：v0.3.0（融合版本）→ v1.0.0（生产就绪）

---

## 📍 当前状态

**当前版本**: v0.1.0a1 (内测阶段)

**核心完成度**:
- ✅ DDD 战术模式（聚合、实体、值对象、领域事件）
- ✅ 六边形架构分层
- ✅ Result 错误处理
- ✅ 基础 Repository 抽象
- ⏳ SQLAlchemy 集成（进行中）
- ⏳ Outbox 模式实现（进行中）

---

## 🎯 版本规划

### v0.1.0 - 核心抽象与基础设施 ✅ 已完成

**发布时间**: 2024 Q4

**目标**: 建立 DDD 核心抽象和基本架构

**核心功能**:
- ✅ Core 层基础组件
  - `Result<T,E>` 错误处理
  - `EntityId` 实体标识
  - `Guard` 前置条件检查
  - `Clock` 时间抽象
- ✅ Domain 层基础类
  - `Entity` 实体基类
  - `ValueObject` 值对象基类
  - `DomainEvent` 领域事件基类
  - `Repository` Protocol 定义
  - `Specification` 规格模式
- ✅ Application 层
  - `UseCase` 用例基类
  - `DTO` 数据传输对象
- ✅ InMemory Repository 实现
- ✅ 基础文档和示例

---

### v0.2.0 - 持久化与事件驱动 🚧 进行中

**预计发布**: 2025 Q1

**目标**: 实现生产级持久化和事件驱动架构

**核心功能**:
- 🚧 SQLAlchemy 集成
  - [x] Base ORM 配置
  - [x] UnitOfWork 实现
  - [ ] Repository 基类
  - [ ] 事务管理优化
- 🚧 Outbox 模式
  - [x] Outbox 表设计
  - [x] OutboxRepository 实现
  - [ ] Outbox Publisher 后台任务
  - [ ] 重试机制和幂等性
- 📋 事件总线抽象
  - [ ] EventBus Protocol 定义
  - [ ] InMemory EventBus 实现
  - [ ] 事件订阅机制
- 📋 持久化测试工具
  - [ ] 数据库 Fixture
  - [ ] 事务隔离测试

**文档**:
- [ ] SQLAlchemy 集成指南
- [ ] Outbox 模式最佳实践
- [ ] 事件驱动架构指南

---

### v0.3.0 - 消息队列与可观测性 📋 计划中

**预计发布**: 2025 Q2

**目标**: 接入生产级消息队列和完善监控

**核心功能**:
- 📋 Pulsar 适配器（优先）
  - [ ] Pulsar EventBus 实现
  - [ ] 消费者/订阅管理
  - [ ] 死信队列处理（DLQ）
  - [ ] 消息序列化/反序列化（JSON/Avro/Protobuf）
  - [ ] Schema Registry 集成
- 📋 Kafka 适配器（可选）
  - [ ] Kafka EventBus 实现
  - [ ] 消费者组管理
- 📋 Metrics 指标
  - [ ] Prometheus 集成
  - [ ] 自定义指标装饰器
  - [ ] UseCase 执行时间统计
  - [ ] Repository 查询统计
- 📋 Tracing 链路追踪
  - [ ] OpenTelemetry 集成
  - [ ] 分布式追踪上下文
- 📋 Logging 日志
  - [ ] 结构化日志
  - [ ] 上下文传递
  - [ ] 敏感数据脱敏

**适配器**:
- [ ] Redis Cache 适配器
- [ ] Redis EventBus 适配器（轻量级场景）

**文档**:
- [ ] Pulsar 集成指南（优先）
- [ ] Kafka 集成指南（可选）
- [ ] 可观测性最佳实践
- [ ] 性能优化指南

---

### v0.4.0 - 安全与多租户 📋 计划中

**预计发布**: 2025 Q3

**目标**: 企业级安全和多租户支持

**核心功能**:
- 📋 认证与授权
  - [ ] JWT 认证集成
  - [ ] RBAC 权限控制
  - [ ] SecurityContext 上下文
  - [ ] 资源级权限
- 📋 多租户支持
  - [ ] TenantContext 租户上下文
  - [ ] 租户隔离策略
  - [ ] 跨租户查询控制
- 📋 审计日志
  - [ ] 操作审计
  - [ ] 数据变更追踪
  - [ ] 合规性报告
- 📋 加密存储
  - [ ] 字段级加密
  - [ ] 密钥管理

**文档**:
- [ ] 安全架构指南
- [ ] 多租户设计模式
- [ ] 合规性检查清单

---

### v0.5.0 - 高级特性与工具 📋 计划中

**预计发布**: 2025 Q4

**目标**: 增强开发体验和高级功能

**核心功能**:
- 📋 Saga 长事务编排
  - [ ] Saga 状态机
  - [ ] 补偿机制
  - [ ] 超时处理
- 📋 CQRS 支持
  - [ ] Command/Query 分离
  - [ ] Read Model 投影
  - [ ] Event Sourcing（可选）
- 📋 工具链
  - [ ] CLI 代码生成器增强
  - [ ] 迁移工具
  - [ ] 健康检查端点
- 📋 性能优化
  - [ ] 查询缓存
  - [ ] 批量操作
  - [ ] 连接池优化

**适配器**:
- [ ] MinIO/S3 Storage 适配器
- [ ] OpenSearch 搜索引擎适配器
- [ ] Email 服务适配器

**文档**:
- [ ] Saga 模式详解
- [ ] CQRS 实战指南
- [ ] 工具使用手册

---

### v1.0.0 - 生产就绪 📋 愿景

**预计发布**: 2026 Q1

**目标**: 稳定的 1.0 版本，适合大规模生产使用

**里程碑**:
- ✅ 完整的功能集
- ✅ 全面的文档
- ✅ 充分的测试覆盖（>90%）
- ✅ 性能基准测试
- ✅ 生产案例研究
- ✅ 社区贡献指南
- ✅ 语义化版本承诺

**质量保证**:
- [ ] 完整的单元测试套件
- [ ] 集成测试覆盖
- [ ] E2E 测试场景
- [ ] 性能回归测试
- [ ] 安全审计

**文档**:
- [ ] 完整的 API 文档
- [ ] 迁移指南（从其他框架）
- [ ] 架构决策记录（ADR）完善
- [ ] 生产部署指南
- [ ] 故障排查手册

---

## 🔮 未来愿景 (v2.0+)

以下是长期规划，具体时间待定：

### 高级功能
- 🌟 GraphQL 原生支持
- 🌟 gRPC 服务生成
- 🌟 WebSocket 实时推送
- 🌟 分布式锁管理
- 🌟 配置中心集成

### 生态系统
- 🌟 官方插件市场
- 🌟 社区贡献模块
- 🌟 与主流框架集成示例（Django, Flask）
- 🌟 云原生部署模板（K8s, Docker Compose）

### 工具和体验
- 🌟 可视化领域建模工具
- 🌟 性能分析面板
- 🌟 自动化文档生成
- 🌟 AI 辅助代码审查

---

## 📊 进度追踪

### 总体进度
- **v0.1.0**: ✅ 100% (已发布)
- **v0.2.0**: 🚧 60% (进行中)
- **v0.3.0**: 📋 0% (计划中)
- **v0.4.0**: 📋 0% (计划中)
- **v0.5.0**: 📋 0% (计划中)

### 当前冲刺 (Sprint 2025-01)

**重点任务**:
1. 🚧 完成 SQLAlchemy Repository 基类
2. 🚧 实现 Outbox Publisher 后台任务
3. 📋 编写 SQLAlchemy 集成测试
4. 📋 完善 Outbox 文档

---

## 🤝 如何参与

我们欢迎社区贡献！以下是参与方式：

### 报告问题
在 GitHub Issues 中报告 bug 或提出功能建议。

### 提交代码
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 改进文档
文档改进同样重要！欢迎提交文档 PR。

### 分享经验
- 编写博客文章
- 在社区分享使用案例
- 回答其他用户的问题

---

## 📝 版本策略

我们遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号 (MAJOR)**: 不兼容的 API 修改
- **次版本号 (MINOR)**: 向下兼容的功能新增
- **修订号 (PATCH)**: 向下兼容的问题修正
- **Alpha/Beta 标识**: 内测/公测版本

---

## 📮 反馈与建议

如果你对路线图有任何建议或想法：

- 📧 邮件：oss@example.com
- 💬 GitHub Discussions
- 🐛 GitHub Issues

---

**最后更新**: 2025-01-04
**下次审查**: 2025-02-01

> 💡 **提示**: 路线图会根据社区反馈和实际需求动态调整。具体功能和时间可能会有变化。
