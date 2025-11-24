# Bento CLI - 领域驱动设计脚手架生成器

快速生成符合 DDD 和 Modular Monolith 架构的应用。

## 🚀 5 分钟快速开始

```bash
# 1. 初始化项目
bento init my-shop

cd my-shop

# 2. 生成模块（必须指定上下文）
bento gen module Product \
  --context catalog \
  --fields "name:str,price:float,stock:int"

# 3. 安装依赖（包含测试工具）
uv pip install -e ".[dev]"

# 4. 运行测试
uv run pytest -v

# 5. 启动应用
cp .env.example .env
uvicorn main:app --reload

# 6. 访问 http://localhost:8000/docs
```

---

## 📖 核心概念

### Modular Monolith 架构

所有项目都按**边界上下文**组织：

```
my-shop/
├── contexts/              # 边界上下文（按业务能力划分）
│   ├── catalog/          # 产品目录上下文
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── ordering/         # 订单上下文
│   │   └── ...
│   └── shared/           # 共享内核
└── tests/                # 按上下文组织测试
    ├── catalog/
    └── ordering/
```

### 上下文（Context）

按**业务能力**划分，而不是技术层：

**✅ 好的上下文**：
- `catalog` - 产品目录管理
- `ordering` - 订单处理
- `identity` - 用户身份
- `inventory` - 库存管理
- `payment` - 支付处理

**❌ 不好的上下文**：
- `crud`, `api`, `database` - 技术术语

---

## 📝 命令

### 初始化项目

```bash
bento init <project_name> [--description "描述"]
```

### 生成模块（推荐）

```bash
bento gen module <Name> \
  --context <context> \
  --fields "field1:type,field2:type"
```

**参数**：
- `<Name>` - 模块名（如 Product, Order）
- `--context` - **必填**，上下文名（如 catalog, ordering）
- `--fields` - 字段定义，支持 `str`, `int`, `float`, `bool`

**每个模块生成 9 个文件**：
- 聚合根 + 领域事件
- 仓储接口 + 映射器接口 + 持久化对象
- 用例
- 3 个测试文件

### 单独生成组件

```bash
bento gen aggregate <Name> --context <context>
bento gen usecase <Name> --context <context>
bento gen event <Name> --context <context>
```

---

## 🎯 完整示例

### 电商应用

```bash
# 初始化
bento init ecommerce

cd ecommerce

# 产品目录上下文
bento gen module Product --context catalog \
  --fields "name:str,price:float,stock:int"

bento gen module Category --context catalog \
  --fields "name:str,parent_id:str"

# 订单上下文
bento gen module Order --context ordering \
  --fields "customer_id:str,total:float,status:str"

# 用户上下文
bento gen module User --context identity \
  --fields "username:str,email:str,is_active:bool"

# 配置和运行
cp .env.example .env
uv pip install -e .
uvicorn main:app --reload
```

---

## 🔧 开发流程

1. **实现领域逻辑** - 编辑 `contexts/<context>/domain/<name>.py`
2. **实现用例** - 编辑 `contexts/<context>/application/usecases/`
3. **编写测试** - 完善 `tests/<context>/` 中的测试
4. **运行测试** - `uv run pytest -v`
5. **实现仓储** - 根据生成的接口实现具体仓储
6. **检查覆盖率** - `uv run pytest --cov`

---

## 📊 生成代码特性

### ✅ 符合架构契约
- 使用 Protocol 接口（依赖反转）
- 不直接依赖 bento.infrastructure/persistence
- 框架集成示例在注释中

### ✅ 测试驱动开发
- 自动生成单元测试
- 自动生成集成测试
- 包含测试骨架和 fixtures

### ✅ 最佳实践
- DDD 分层清晰
- CQRS 模式
- 事件驱动架构
- 详细代码注释

---

## ❓ 常见问题

**Q: 忘记写 --context 怎么办？**
A: 会报错提示，context 是必填参数。

**Q: 如何在现有项目中使用？**
A: `cd my-project && bento gen module Feature --context xxx`

**Q: 可以修改生成的代码吗？**
A: 完全可以！生成的是模板，你应该添加业务逻辑。

**Q: 支持哪些字段类型？**
A: 目前支持 `str`, `int`, `float`, `bool`

---

## 📚 更多信息

- **[CLI_USAGE_GUIDE.md](./CLI_USAGE_GUIDE.md)** - 完整命令参考
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - 测试运行指南 ⭐

---

**Bento CLI - 让 DDD 开发更简单！** 🍱
