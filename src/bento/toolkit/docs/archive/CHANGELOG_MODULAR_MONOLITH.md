# Bento Framework - Modular Monolith 统一架构变更日志

## 🎯 重大变更（2025-11-17）

### 架构统一

**Bento Framework 现已统一采用 Modular Monolith（模块化单体）架构。**

---

## 🔄 主要变更

### 1. 移除传统分层架构

**之前**：
```bash
# 可以选择架构
bento init my-app --architecture layered
bento init my-app --architecture modular-monolith
```

**现在**：
```bash
# 统一为 Modular Monolith，无需选择
bento init my-app
```

### 2. context 参数变为必填

**之前**：
```bash
# context 是可选的
bento gen module Product --fields "name:str,price:float"
```

**现在**：
```bash
# context 是必填的
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float"
```

### 3. 统一的目录结构

**所有项目都按上下文组织**：

```
my-app/
├── contexts/              # 边界上下文（必须）
│   ├── catalog/
│   ├── ordering/
│   └── shared/
└── tests/
    ├── catalog/
    └── ordering/
```

---

## 📝 CLI 变更

### 初始化命令

```bash
# 旧命令
bento init my-app --architecture modular-monolith

# 新命令（简化）
bento init my-app
```

### 生成命令

```bash
# 旧命令（context 可选）
bento gen module Product --fields "name:str,price:float"

# 新命令（context 必填）
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float"
```

---

## 🗂️ 文件变更

### 新增文件

- `src/bento/toolkit/UNIFIED_ARCHITECTURE.md` - 架构统一规范
- `src/bento/toolkit/MODULAR_MONOLITH_GUIDE.md` - 完整架构指南
- `CHANGELOG_MODULAR_MONOLITH.md` - 本变更日志

### 更新文件

- `src/bento/toolkit/CLI_USAGE_GUIDE.md` - 完全重写，移除 layered 架构
- `src/bento/toolkit/PROJECT_INIT_GUIDE.md` - 完全重写，统一为 Modular Monolith
- `src/bento/toolkit/cli.py` - 移除架构选择，context 必填

### 备份文件

- `CLI_USAGE_GUIDE.md.old` - 旧版本备份
- `PROJECT_INIT_GUIDE.md.old` - 旧版本备份

---

## 🎯 设计理念

### 为什么统一为 Modular Monolith？

1. **边界清晰** - 强制按边界上下文组织，避免混乱依赖
2. **团队协作** - 支持多团队并行开发不同上下文
3. **可演化性** - 易于重构和拆分为微服务
4. **符合 DDD** - 完整支持战略设计和战术设计
5. **简化选择** - 移除架构选择的复杂性，降低学习成本

### 核心原则

- **上下文优先** - 始终按边界上下文组织代码
- **显式依赖** - 使用接口定义上下文间依赖
- **事件驱动** - 跨上下文通过事件通信
- **独立演化** - 每个上下文可独立修改
- **测试隔离** - 按上下文组织和运行测试

---

## 📊 影响范围

### 对现有项目

**如果你的项目使用旧版 CLI 生成**：

1. **传统分层架构项目**：
   - 仍可正常运行
   - 建议逐步迁移到 Modular Monolith
   - 参考迁移指南（待补充）

2. **Modular Monolith 项目**：
   - 无影响，继续使用
   - 升级 CLI 后体验更好（context 必填保证质量）

### 对新项目

**所有新项目**：
- 自动使用 Modular Monolith 架构
- 必须指定 context 参数
- 强制最佳实践

---

## 🚀 升级指南

### 步骤 1: 更新 Bento CLI

```bash
cd /workspace/bento
git pull
```

### 步骤 2: 测试新 CLI

```bash
# 创建测试项目
bento init test-project

cd test-project

# 生成模块
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float"
```

### 步骤 3: 迁移现有项目（可选）

如果你有使用旧版 layered 架构的项目：

```bash
# 1. 识别边界上下文
# 2. 创建 contexts/ 目录
# 3. 移动相关代码到对应上下文
# 4. 重构跨上下文依赖
```

详细迁移指南请参考 `MIGRATION_GUIDE.md`（待补充）。

---

## 📚 更新的文档

### 必读文档

1. **[UNIFIED_ARCHITECTURE.md](./src/bento/toolkit/UNIFIED_ARCHITECTURE.md)**
   - 架构决策说明
   - CLI 使用指南
   - 最佳实践

2. **[MODULAR_MONOLITH_GUIDE.md](./src/bento/toolkit/MODULAR_MONOLITH_GUIDE.md)**
   - 完整架构指南
   - 上下文设计
   - 通信模式

3. **[CLI_USAGE_GUIDE.md](./src/bento/toolkit/CLI_USAGE_GUIDE.md)**
   - CLI 命令详解
   - 示例和最佳实践

4. **[PROJECT_INIT_GUIDE.md](./src/bento/toolkit/PROJECT_INIT_GUIDE.md)**
   - 项目初始化流程
   - 完整开发工作流

---

## 🎓 示例项目

### 新增示例

- `applications/ecommerce-modular/` - 完整电商示例（3个上下文）
- `applications/test-unified/` - 测试项目（3个上下文）

### 结构示例

```
ecommerce-modular/
├── contexts/
│   ├── catalog/        # Product, Category
│   ├── ordering/       # Order, OrderItem
│   ├── identity/       # User, Role
│   └── shared/
└── tests/
    ├── catalog/
    ├── ordering/
    └── identity/
```

---

## ⚠️ 破坏性变更

### 1. 移除 --architecture 参数

```bash
# ❌ 不再支持
bento init my-app --architecture layered
bento init my-app --architecture modular-monolith

# ✅ 现在只需要
bento init my-app
```

### 2. context 参数变为必填

```bash
# ❌ 会报错
bento gen module Product --fields "name:str,price:float"

# ✅ 必须指定 context
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float"
```

### 3. 目录结构变更

**之前（layered）**：
```
domain/
application/
infrastructure/
```

**现在（unified）**：
```
contexts/<context>/domain/
contexts/<context>/application/
contexts/<context>/infrastructure/
```

---

## 🔮 未来计划

### 短期（Q4 2025）

- [ ] 添加上下文映射工具
- [ ] 生成集成事件模板
- [ ] 自动生成 API 路由
- [ ] 完善迁移指南

### 中期（Q1 2026）

- [ ] 支持上下文依赖分析
- [ ] 可视化上下文关系
- [ ] 自动生成架构文档
- [ ] 性能优化工具

### 长期（Q2 2026+）

- [ ] 微服务拆分工具
- [ ] 事件溯源支持
- [ ] CQRS 模式增强
- [ ] 多语言代码生成

---

## 💬 反馈

如有任何问题或建议，请：

1. 提交 Issue
2. 发起 Discussion
3. 提交 Pull Request

---

## 🙏 致谢

感谢所有贡献者对 Bento Framework 的支持！

---

**Bento Framework - 专注 DDD，构建可演化的应用！** 🍱

---

**更新时间**: 2025-11-17
**版本**: 2.0.0
**状态**: 已发布 ✅
