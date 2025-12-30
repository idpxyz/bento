# my-shop 文件整理总结

**整理日期**: 2024-12-30
**状态**: ✅ 目录结构已创建

---

## 🎯 整理目标

将 my-shop 应用中混乱的文档、测试和脚本文件进行科学整理。

---

## 📊 当前问题

### 根目录混乱（需要整理）
```
my-shop/
├── ARCHITECTURE_*.md (12个)           ← 应该在 docs/architecture/
├── test_*.py (10个)                   ← 应该在 tests/ 或 scripts/
├── demo_*.py (3个)                    ← 应该在 scripts/demo/
├── debug_*.py (2个)                   ← 应该在 scripts/debug/
├── scenario_*.py (1个)                ← 应该在 tests/e2e/
└── *.sh (5个)                         ← 应该在 scripts/test/
```

### docs/ 目录混乱（60+ 个文档）
- 没有分类
- 难以查找
- 缺少索引

---

## 🏗️ 新的目录结构（已创建）

```
my-shop/
├── docs/
│   ├── architecture/        ✅ 已创建 - 架构文档
│   ├── features/            ✅ 已创建 - 功能文档
│   ├── guides/              ✅ 已创建 - 使用指南
│   └── implementation/      ✅ 已创建 - 实施细节
│
├── tests/
│   └── e2e/                 ✅ 已创建 - 端到端测试
│
└── scripts/
    ├── demo/                ✅ 已创建 - 演示脚本
    ├── debug/               ✅ 已创建 - 调试工具
    └── test/                ✅ 已创建 - 测试脚本
```

---

## 📋 建议的整理步骤

### Step 1: 整理架构文档（根目录 → docs/architecture/）

```bash
# 移动架构相关文档
mv ARCHITECTURE_*.md docs/architecture/
mv README_ARCHITECTURE.md docs/architecture/
mv ORDER_AGGREGATE_GUIDE.md docs/architecture/
mv PROJECT_OVERVIEW.md docs/architecture/
```

### Step 2: 整理功能文档（docs/ → docs/features/）

```bash
# 创建功能子目录
mkdir -p docs/features/{observability,idempotency,cache,service-discovery,security}

# 移动 Observability 文档
mv docs/OBSERVABILITY_*.md docs/features/observability/

# 移动 Idempotency 文档
mv docs/IDEMPOTENCY_*.md docs/features/idempotency/

# 移动 Cache 文档
mv docs/CACHE_*.md docs/features/cache/
mv CACHE_*.md docs/features/cache/

# 移动 Service Discovery 文档
mv MY_SHOP_SERVICE_DISCOVERY_INTEGRATION.md docs/features/service-discovery/

# 移动 Security 文档
mv docs/SECURITY_*.md docs/features/security/
mv docs/MULTI_TENANCY_*.md docs/features/security/
```

### Step 3: 整理实施文档（docs/ → docs/implementation/）

```bash
# 移动 Bootstrap 文档
mv docs/BOOTSTRAP_*.md docs/implementation/

# 移动 Middleware 文档
mv docs/MIDDLEWARE_*.md docs/implementation/

# 移动 Database 文档
mv docs/DATABASE_*.md docs/implementation/
```

### Step 4: 整理测试脚本（根目录 → scripts/）

```bash
# 移动测试脚本
mv test_*.sh scripts/test/
mv run_*.sh scripts/test/

# 移动演示脚本
mv demo_*.py scripts/demo/
mv example_*.py scripts/demo/
mv scenario_*.py scripts/demo/

# 移动调试工具
mv debug_*.py scripts/debug/
mv manual_test_*.py scripts/debug/
mv verify_*.sql scripts/debug/
```

### Step 5: 整理测试文件（根目录 → tests/）

```bash
# 移动端到端测试
mv test_*_integration.py tests/e2e/
mv test_outbox_end_to_end.py tests/e2e/

# 移动其他测试到 integration
mv test_*.py tests/integration/ 2>/dev/null || true
```

### Step 6: 清理临时文件

```bash
# 清理编译文件
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete

# 清理测试缓存
rm -rf .pytest_cache htmlcov

# 清理日志文件（可选）
# rm -f server.log *.txt
```

---

## 📚 推荐的文档索引

### docs/README.md（文档导航）

```markdown
# my-shop 文档

## 📖 快速开始
- [README](../README.md) - 项目介绍
- [QUICKSTART](../QUICKSTART.md) - 快速开始

## 🏗️ 架构文档
- [architecture/](architecture/) - 架构设计文档

## ✨ 功能文档
- [features/observability/](features/observability/) - 可观测性
- [features/idempotency/](features/idempotency/) - 幂等性
- [features/cache/](features/cache/) - 缓存
- [features/service-discovery/](features/service-discovery/) - 服务发现
- [features/security/](features/security/) - 安全和多租户

## 🔧 实施文档
- [implementation/](implementation/) - 实施细节

## 📝 指南
- [guides/](guides/) - 使用指南
```

### tests/README.md（测试说明）

```markdown
# my-shop 测试

## 🧪 测试结构

- `unit/` - 单元测试
- `integration/` - 集成测试
- `e2e/` - 端到端测试

## 🚀 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/e2e/
```

## 📜 测试脚本

见 `../scripts/test/` 目录
```

### scripts/README.md（脚本说明）

```markdown
# my-shop 脚本

## 📁 目录结构

- `demo/` - 演示脚本
- `debug/` - 调试工具
- `test/` - 测试脚本

## 🎯 使用方式

### 演示脚本
```bash
python scripts/demo/demo_event_handlers.py
```

### 测试脚本
```bash
bash scripts/test/test_idempotency.sh
```

### 调试工具
```bash
python scripts/debug/debug_tenant.py
```
```

---

## ✅ 整理后的效果

### 根目录清爽
```
my-shop/
├── README.md                    ← 主文档
├── QUICKSTART.md                ← 快速开始
├── main.py                      ← 应用入口
├── pyproject.toml               ← 项目配置
├── docs/                        ← 所有文档
├── tests/                       ← 所有测试
├── scripts/                     ← 所有脚本
├── contexts/                    ← 业务代码
├── runtime/                     ← 运行时配置
└── config/                      ← 应用配置
```

### 文档分类清晰
- 架构文档在 `docs/architecture/`
- 功能文档在 `docs/features/`
- 实施文档在 `docs/implementation/`

### 测试组织规范
- 单元测试在 `tests/unit/`
- 集成测试在 `tests/integration/`
- E2E 测试在 `tests/e2e/`

### 脚本分类明确
- 演示脚本在 `scripts/demo/`
- 调试工具在 `scripts/debug/`
- 测试脚本在 `scripts/test/`

---

## 🎓 最佳实践

### 1. 保持根目录简洁
- 只保留核心文档（README, QUICKSTART）
- 只保留核心配置文件
- 其他文件分类存放

### 2. 文档分类清晰
- 按类型分类（架构/功能/实施/指南）
- 每个目录有 README 索引
- 相关文档放在一起

### 3. 测试分层明确
- 单元测试 - 测试单个组件
- 集成测试 - 测试组件交互
- E2E 测试 - 测试完整流程

### 4. 脚本用途明确
- demo/ - 演示功能
- debug/ - 调试问题
- test/ - 运行测试

---

## 🚀 下一步

1. **执行整理** - 按照上述步骤移动文件
2. **创建索引** - 创建 README.md 文档
3. **验证测试** - 确保测试仍然可以运行
4. **更新引用** - 更新文档中的路径引用

---

**整理完成后，项目将更加专业和易于维护！** 🎉
