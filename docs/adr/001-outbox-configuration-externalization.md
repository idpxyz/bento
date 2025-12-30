# ADR-001: Outbox 配置外部化架构决策

**状态**: 已接受 ✅
**日期**: 2024-11-29
**决策者**: Bento Framework 架构团队

## 背景

Bento Framework 的 Outbox 模块最初使用硬编码常量进行配置，这导致了以下问题：

1. **环境适配困难**: 相同代码无法适配不同环境（开发/测试/生产）
2. **性能调优受限**: 无法根据业务场景调整性能参数
3. **运维复杂**: 配置变更需要修改代码和重新部署
4. **违反 12-Factor**: 配置与代码耦合，不符合现代应用标准

## 决策

我们决定实施完整的配置外部化方案，包括：

### 核心决策
1. **创建统一配置模型**: `OutboxProjectorConfig` 和 `OutboxConfig`
2. **支持多种配置来源**: 环境变量、代码配置、配置文件
3. **保持向后兼容**: 提供合理默认值
4. **类型安全**: 使用 `@dataclass` 和类型注解
5. **全局配置管理**: 单例模式管理配置实例

### 配置参数分类
- **性能调优**: `batch_size`, `sleep_*` 系列
- **重试策略**: `max_retry_attempts`, `backoff_*` 系列
- **状态管理**: `status_*` 系列
- **多租户**: `default_tenant_id`
- **存储**: 字段长度限制等

## 技术实现

### 配置模型设计
```python
@dataclass(frozen=True)
class OutboxProjectorConfig:
    batch_size: int = 200
    max_retry_attempts: int = 5
    # ... 17个可配置参数

    @classmethod
    def from_env(cls, prefix: str = "BENTO_OUTBOX_") -> OutboxProjectorConfig:
        # 环境变量加载逻辑

    @classmethod
    def from_dict(cls, config_dict: dict) -> OutboxProjectorConfig:
        # 配置字典加载逻辑
```

### 依赖注入设计
```python
class OutboxProjector:
    def __init__(
        self,
        config: OutboxProjectorConfig | None = None  # 可选注入
    ):
        self._config = config or get_outbox_projector_config()
```

### 全局配置管理
```python
# 懒加载单例
_outbox_projector_config: OutboxProjectorConfig | None = None

def get_outbox_projector_config() -> OutboxProjectorConfig:
    global _outbox_projector_config
    if _outbox_projector_config is None:
        _outbox_projector_config = OutboxProjectorConfig.from_env()
    return _outbox_projector_config
```

## 配置加载优先级

1. **显式配置** (最高优先级)
   ```python
   config = OutboxProjectorConfig(batch_size=500)
   projector = OutboxProjector(config=config)
   ```

2. **环境变量**
   ```bash
   export BENTO_OUTBOX_BATCH_SIZE=1000
   ```

3. **配置文件** (通过字典加载)
   ```python
   config = OutboxProjectorConfig.from_dict(yaml_data)
   ```

4. **默认值** (最低优先级)
   ```python
   batch_size: int = 200  # 内置默认值
   ```

## 影响的组件

### 已更新组件
- `OutboxProjector`: 使用配置对象替代硬编码常量
- `OutboxRecord`: 重试逻辑使用配置参数
- 所有示例和测试代码

### 新增组件
- `bento.config.outbox`: 配置模型模块
- `examples/outbox_config_usage.py`: 使用示例
- `docs/configuration/outbox.md`: 配置文档

## 优势

### 1. 环境适配能力
- **开发环境**: 小批量、快速失败、详细日志
- **测试环境**: 中等配置、适中重试
- **生产环境**: 大批量、更多重试、优化性能

### 2. 性能调优灵活性
- **高吞吐量**: `batch_size=2000, sleep_busy=0.01`
- **低延迟**: `batch_size=50, sleep_busy=0.001`
- **资源节约**: `sleep_idle_max=60, backoff_multiplier=3`

### 3. 运维便利性
- **热配置**: 环境变量调整无需代码变更
- **监控集成**: `to_dict()` 导出配置供监控
- **故障排查**: 配置参数可见性

### 4. 架构一致性
- **符合 12-Factor App**: 配置与代码分离
- **符合六边形架构**: 配置在正确的层次
- **符合 SOLID 原则**: 依赖倒置，可测试

## 风险与缓解

### 风险
1. **配置复杂性**: 17个参数可能让用户困惑
2. **向后兼容**: 可能破坏现有代码
3. **配置错误**: 错误配置可能影响性能

### 缓解措施
1. **良好默认值**: 所有参数都有经过测试的默认值
2. **完整文档**: 提供详细配置指南和使用示例
3. **类型安全**: 使用类型注解防止配置错误
4. **验证机制**: 后续添加配置参数合理性检查

## 后续计划

### Phase 2: 配置增强
- [ ] 配置热更新支持
- [ ] 预定义配置模板
- [ ] 配置参数校验
- [ ] Prometheus metrics 集成

### Phase 3: 生态完善
- [ ] 配置管理 Web UI
- [ ] 配置版本控制
- [ ] 配置审计日志

## 测量指标

### 成功指标
- ✅ 17个关键参数完全外部化
- ✅ 4种配置加载方式可用
- ✅ 100% 向后兼容
- ✅ 0 个硬编码常量残留

### 性能指标
- 🎯 配置加载时间 < 1ms
- 🎯 内存开销增加 < 1KB
- 🎯 运行时性能影响 < 0.1%

## 参考资料

- [12-Factor App - Config](https://12factor.net/config)
- [Domain-Driven Design - Configuration](https://martinfowler.com/articles/injection.html)
- [Hexagonal Architecture - Adapters](https://alistair.cockburn.us/hexagonal-architecture/)

## 修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2024-11-29 | 初始版本，配置外部化决策 |
