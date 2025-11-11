# Legend 融合升级 - 执行检查清单

> ✅ 使用本清单跟踪每个阶段的完成情况

**更新日期**：2025-11-06
**当前阶段**：准备启动

---

## 🎯 总体进度

- [ ] **Phase F1**: Mapper 系统融合（Week 1-3）
- [ ] **Phase F2**: Repository 增强系统（Week 4-7）
- [ ] **Phase F3**: 统一事件收集机制（Week 8-9）
- [ ] **Phase F4**: Fluent Specification Builder（Week 10-11）
- [ ] **Phase F5**: BaseUseCase 增强（Week 12-13）
- [ ] **Phase F6**: 整合和优化（Week 14-16）

**总体完成度**：0%

---

## 📅 Week 1: Mapper 基础（最高优先级）

### Day 1-2: MapperStrategy 基类

#### 任务列表

- [ ] **环境准备**
  - [ ] 创建 `fusion/week1-mapper-foundation` 分支
  - [ ] 创建目录结构
    ```bash
    src/bento/infrastructure/mapper/
    tests/unit/infrastructure/mapper/
    tests/integration/infrastructure/mapper/
    examples/mapper/
    docs/infrastructure/
    ```

- [ ] **基类实现**
  - [ ] 创建 `src/bento/infrastructure/mapper/base.py`
  - [ ] 实现 `MapperStrategy` 抽象类
    - [ ] `to_po()` 方法
    - [ ] `to_domain()` 方法
    - [ ] `to_po_list()` 批量方法
    - [ ] `to_domain_list()` 批量方法
  - [ ] 完整的 docstring 和类型注解

- [ ] **单元测试**
  - [ ] 创建 `tests/unit/infrastructure/mapper/test_base.py`
  - [ ] `test_to_po()` - Domain → PO
  - [ ] `test_to_domain()` - PO → Domain
  - [ ] `test_to_po_list()` - 批量转换
  - [ ] `test_to_domain_list()` - 批量转换
  - [ ] 所有测试通过 ✅

- [ ] **质量检查**
  - [ ] mypy 类型检查通过
  - [ ] 代码格式化（black/ruff）
  - [ ] Git commit

**验收**：✅ 基类完成，4个测试通过，类型检查通过

---

### Day 3-4: AutoMapper 实现

#### 任务列表

- [ ] **核心实现**
  - [ ] 创建 `src/bento/infrastructure/mapper/auto.py`
  - [ ] 实现 `AutoMapper` 类
    - [ ] 构造函数（domain_class, po_class, field_mapping, exclude_fields）
    - [ ] `to_po()` - 自动字段提取和映射
    - [ ] `to_domain()` - 反向自动映射
    - [ ] 支持 dataclass 和普通类
  - [ ] 完整的 docstring 和示例

- [ ] **单元测试**
  - [ ] 创建 `tests/unit/infrastructure/mapper/test_auto.py`
  - [ ] `test_auto_map_dataclass()` - dataclass 映射
  - [ ] `test_auto_map_normal_class()` - 普通类映射
  - [ ] `test_field_mapping()` - 字段名映射
  - [ ] `test_exclude_fields()` - 字段排除
  - [ ] `test_nested_objects()` - 嵌套对象（可选）
  - [ ] `test_to_po_with_none()` - None 值处理
  - [ ] `test_reverse_mapping()` - 反向映射
  - [ ] `test_batch_conversion()` - 批量转换
  - [ ] ... 共 20+ 测试
  - [ ] 测试覆盖率 > 85% ✅

- [ ] **示例代码**
  - [ ] 创建 `examples/mapper/auto_mapper_demo.py`
  - [ ] 简单 User 示例
  - [ ] 带字段映射的 Product 示例
  - [ ] 字段排除的 Customer 示例

- [ ] **质量检查**
  - [ ] 所有测试通过
  - [ ] mypy 类型检查通过
  - [ ] 示例可运行
  - [ ] Git commit

**验收**：✅ AutoMapper 完成，20+ 测试通过，示例可运行

---

### Day 5: 文档和 Code Review

#### 任务列表

- [ ] **集成测试**
  - [ ] 创建 `tests/integration/infrastructure/mapper/test_auto_integration.py`
  - [ ] 与现有 Domain 对象集成测试
  - [ ] 与现有 PO 对象集成测试

- [ ] **文档编写**
  - [ ] 创建 `docs/infrastructure/MAPPER_GUIDE.md`
    - [ ] Mapper 系统概述
    - [ ] MapperStrategy 接口说明
    - [ ] AutoMapper 使用指南
    - [ ] 示例代码
    - [ ] 最佳实践
    - [ ] 常见问题（FAQ）

- [ ] **Code Review**
  - [ ] 代码质量检查
  - [ ] 性能考虑
  - [ ] 边界情况处理
  - [ ] 错误处理
  - [ ] 文档完整性

- [ ] **更新包导出**
  - [ ] 更新 `src/bento/infrastructure/mapper/__init__.py`
  - [ ] 添加到主 `__init__.py`

**验收**：✅ 文档完成，代码审查通过，准备合并

---

## 🎯 Week 1 Milestone 验收

### 必须完成 ✅

- [ ] `MapperStrategy` 基类完整实现
- [ ] `AutoMapper` 完整实现
- [ ] 25+ 单元测试通过
- [ ] 测试覆盖率 > 85%
- [ ] 类型检查 100% 通过
- [ ] 基础文档完成
- [ ] 示例可运行

### 可选完成 ⭐

- [ ] `ExplicitMapper` 基类（简单占位）
- [ ] 性能基准测试
- [ ] 与 ecommerce 应用集成测试

### Week 1 Demo 准备

准备演示以下功能：

```python
# Demo 1: 零配置使用
from bento.infrastructure.mapper import AutoMapper

mapper = AutoMapper(User, UserPO)
po = mapper.to_po(user)  # ✅ 自动映射

# Demo 2: 字段映射
mapper = AutoMapper(
    Product, ProductPO,
    field_mapping={'product_id': 'id'},
    exclude_fields={'internal_notes'}
)
po = mapper.to_po(product)  # ✅ 自动映射 + 字段转换

# Demo 3: 批量转换
pos = mapper.to_po_list(products)  # ✅ 批量转换
```

---

## 📅 Week 2-3: HybridMapper 和迁移

### Week 2: HybridMapper 实现

- [ ] **HybridMapper 核心**
  - [ ] 创建 `src/bento/infrastructure/mapper/hybrid.py`
  - [ ] 实现混合映射逻辑
  - [ ] 30+ 单元测试

- [ ] **示例和文档**
  - [ ] `examples/mapper/hybrid_mapper_demo.py`
  - [ ] 更新 MAPPER_GUIDE.md

### Week 3: 现有代码迁移

- [ ] **迁移 OrderMapper**
  - [ ] 从 ExplicitMapper 改为 HybridMapper
  - [ ] 对比代码量（应减少 50-70%）
  - [ ] 测试验证

- [ ] **性能测试**
  - [ ] 基准测试
  - [ ] 对比报告

---

## 📊 进度跟踪

### 完成度统计

| 阶段 | 计划任务 | 已完成 | 完成率 |
|------|---------|--------|--------|
| Week 1 - Day 1-2 | 15 | 0 | 0% |
| Week 1 - Day 3-4 | 18 | 0 | 0% |
| Week 1 - Day 5 | 12 | 0 | 0% |
| **Week 1 总计** | **45** | **0** | **0%** |

### 时间追踪

| 日期 | 实际工时 | 任务 | 备注 |
|------|---------|------|------|
| 2025-11-06 | - | 计划制定 | ✅ 完成 |
| 2025-11-07 | - | - | - |
| 2025-11-08 | - | - | - |

---

## 🚀 下一步行动

### 立即执行（今天）

1. **创建分支**
   ```bash
   cd /workspace/bento
   git checkout -b fusion/week1-mapper-foundation
   ```

2. **创建目录结构**
   ```bash
   mkdir -p src/bento/infrastructure/mapper
   mkdir -p tests/unit/infrastructure/mapper
   mkdir -p examples/mapper
   ```

3. **开始编码**
   - 创建 `base.py`
   - 实现 `MapperStrategy`
   - 编写第一个测试

### 本周目标

- ✅ 完成 Week 1 所有任务
- 📝 每日更新本检查清单
- 🎉 周五 Demo 演示

---

## 📝 会议和同步

### 每日站会

- **时间**：每天早上 9:00
- **内容**：
  - 昨天完成了什么
  - 今天计划做什么
  - 有什么阻碍

### 周五 Review

- **时间**：周五下午 4:00
- **内容**：
  - Week 1 完成情况
  - Demo 演示
  - 下周计划

---

## 💡 提示和注意事项

### 开发建议

1. **TDD 驱动**：先写测试，再写实现
2. **小步提交**：每完成一个功能就提交
3. **持续验证**：随时运行测试和类型检查
4. **文档同步**：代码和文档同步更新

### 常见陷阱

⚠️ **避免过度设计**：先实现核心功能，再优化
⚠️ **类型注解**：确保所有公开 API 都有类型注解
⚠️ **测试覆盖**：不要遗漏边界情况
⚠️ **性能考虑**：对大列表的批量操作要注意性能

---

## 🎯 成功标准

Week 1 成功完成的标志：

- ✅ 所有测试通过（绿灯）
- ✅ 类型检查通过（mypy strict mode）
- ✅ 代码覆盖率 > 85%
- ✅ 文档清晰完整
- ✅ 示例可以运行
- ✅ Code Review 无严重问题
- ✅ 团队成员理解并认可设计

**准备好了吗？Let's Go! 🚀**

---

**最后更新**：2025-11-06
**下次更新**：每日更新

