# 配置外部化文档指南

## 📚 文档结构

### 核心文档
- [`outbox.md`](./outbox.md) - **Outbox 配置完整指南**
  - 所有配置参数详细说明
  - 不同使用方式（环境变量、代码配置、配置文件）
  - 性能调优建议
  - API 迁移指南

### 架构决策记录
- [`../adr/001-outbox-configuration-externalization.md`](../adr/001-outbox-configuration-externalization.md) - **配置外部化 ADR**
  - 设计决策背景和原因
  - 技术实现方案
  - 风险评估和缓解措施

## 🎯 使用指南

### 快速开始
1. **基础使用**：参考 [`outbox.md`](./outbox.md) 的"使用方式"部分
2. **完整示例**：查看 [`../../examples/outbox_projector_usage.py`](../../examples/outbox_projector_usage.py)
3. **高级功能**：查看 [`../../examples/advanced_config_features.py`](../../examples/advanced_config_features.py)

### 不同场景
- **开发环境**：使用默认配置或 `development` 模板
- **测试环境**：使用 `testing` 模板
- **生产环境**：通过环境变量配置，使用 `production` 模板
- **性能调优**：根据业务需求选择 `high_throughput`、`low_latency` 等模板

## 🔄 API 迁移

如果您使用的是旧版本的 OutboxProjector API，请参考 [`outbox.md`](./outbox.md) 底部的"API 更新说明"部分。

### 迁移检查清单
- [ ] 移除构造函数中的硬编码参数（如 `batch_size`、`max_retries`）
- [ ] 添加 `config` 参数或使用环境变量配置
- [ ] 更新导入：添加 `from bento.config.outbox import OutboxProjectorConfig`
- [ ] 测试新配置是否正常工作

## 📋 示例文件指南

| 示例文件 | 用途 | 复杂度 |
|----------|------|--------|
| `outbox_projector_usage.py` | OutboxProjector 完整使用指南 | ⭐⭐⭐ |
| `advanced_config_features.py` | 高级配置功能演示 | ⭐⭐⭐⭐ |
| `outbox_usage.py` | Outbox 智能路由示例 | ⭐⭐ |
| `outbox_usage_example.py` | 基础 Outbox 模式使用 | ⭐ |

## 🛠️ 配置开发工具

### 配置验证
```python
from bento.config import validate_config
result = validate_config(your_config)
print(result.get_detailed_report())
```

### 配置模板
```python
from bento.config import ConfigTemplates
config = ConfigTemplates.get_template("production")
```

### 配置热更新
```python
from bento.config import get_hot_reloader
reloader = get_hot_reloader()
reloader.register_callback(your_callback)
```

## 🔍 故障排查

### 常见问题
1. **配置参数不生效**
   - 检查环境变量名称是否正确（前缀 `BENTO_OUTBOX_`）
   - 确认配置对象是否正确传递给 OutboxProjector

2. **性能问题**
   - 使用配置验证工具检查参数合理性
   - 参考性能调优部分的建议

3. **API 迁移问题**
   - 检查是否有残留的硬编码参数
   - 确认导入路径是否正确

### 调试技巧
- 使用 `config.to_dict()` 查看当前配置
- 启用详细日志查看配置加载过程
- 使用配置验证工具检查参数合理性
