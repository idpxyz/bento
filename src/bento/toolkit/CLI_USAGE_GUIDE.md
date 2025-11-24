# Bento CLI 命令参考

完整的命令使用指南和示例。

---

## 📋 命令总览

```bash
bento init <project>              # 初始化项目
bento gen module <name>           # 生成完整模块
bento gen aggregate <name>        # 生成聚合根
bento gen usecase <name>          # 生成用例
bento gen event <name>            # 生成领域事件
```

**所有 gen 命令都需要 `--context` 参数。**

---

## 1️⃣ 初始化项目

### 命令

```bash
bento init <project_name> [options]
```

### 参数

| 参数 | 必填 | 说明 | 默认值 |
|-----|------|------|--------|
| `project_name` | ✅ | 项目名称 | - |
| `--description` | ❌ | 项目描述 | 自动生成 |
| `--output` | ❌ | 输出目录 | `.` |

### 示例

```bash
# 基本用法
bento init my-shop

# 带描述
bento init my-shop --description "E-commerce platform"

# 指定输出目录
bento init my-shop --output ~/projects
```

### 生成内容

```
my-shop/
├── contexts/shared/      # 共享内核
├── api/                  # API 层
├── tests/                # 测试
├── main.py               # 应用入口
├── config.py             # 配置
├── pyproject.toml        # 项目配置
├── .env.example          # 环境变量模板
├── pytest.ini            # 测试配置
└── README.md             # 文档
```

---

## 2️⃣ 生成模块

### 命令

```bash
bento gen module <name> --context <context> [options]
```

### 参数

| 参数 | 必填 | 说明 | 示例 |
|-----|------|------|------|
| `name` | ✅ | 模块名称 | `Product`, `Order` |
| `--context` | ✅ | 边界上下文 | `catalog`, `ordering` |
| `--fields` | ❌ | 字段定义 | `"name:str,price:float"` |
| `--output` | ❌ | 输出目录 | `.` |

### 字段语法

```bash
--fields "field1:type1,field2:type2,field3:type3"
```

**支持的类型**：`str`, `int`, `float`, `bool`

### 示例

```bash
# 产品模块
bento gen module Product \
  --context catalog \
  --fields "name:str,description:str,price:float,stock:int"

# 订单模块
bento gen module Order \
  --context ordering \
  --fields "customer_id:str,total:float,status:str,created_at:str"

# 用户模块
bento gen module User \
  --context identity \
  --fields "username:str,email:str,hashed_password:str,is_active:bool"
```

### 生成内容（每个模块 9 个文件）

```
contexts/<context>/
├── domain/
│   ├── <name>.py                     # 聚合根
│   └── events/
│       └── <name>created_event.py    # 领域事件
├── application/
│   └── usecases/
│       └── create_<name>.py          # 用例
└── infrastructure/
    ├── models/
    │   └── <name>_po.py              # 持久化对象
    ├── mappers/
    │   └── <name>_mapper.py          # 映射器接口
    └── repositories/
        └── <name>_repository.py      # 仓储接口

tests/<context>/
├── unit/
│   ├── domain/
│   │   └── test_<name>.py            # 聚合根测试
│   └── application/
│       └── test_create_<name>.py     # 用例测试
└── integration/
    └── test_<name>_repository.py     # 仓储测试
```

---

## 3️⃣ 生成单独组件

### 聚合根

```bash
bento gen aggregate <name> --context <context> [--fields FIELDS]
```

**示例**：
```bash
bento gen aggregate Category \
  --context catalog \
  --fields "name:str,parent_id:str"
```

### 用例

```bash
bento gen usecase <name> --context <context>
```

**示例**：
```bash
bento gen usecase UpdateProduct --context catalog
bento gen usecase CancelOrder --context ordering
```

### 领域事件

```bash
bento gen event <name> --context <context>
```

**示例**：
```bash
bento gen event ProductDeactivated --context catalog
bento gen event OrderCancelled --context ordering
```

### 仓储接口

```bash
bento gen repository <name> --context <context>
```

### 映射器接口

```bash
bento gen mapper <name> --context <context>
```

### 持久化对象

```bash
bento gen po <name> --context <context> [--fields FIELDS]
```

---

## 🎨 完整示例：电商应用

```bash
# 1. 初始化项目
bento init ecommerce --description "E-commerce platform with DDD"

cd ecommerce

# 2. 产品目录上下文
bento gen module Product \
  --context catalog \
  --fields "name:str,description:str,price:float,category:str,stock:int,is_active:bool"

bento gen module Category \
  --context catalog \
  --fields "name:str,parent_id:str,description:str,image_url:str"

# 3. 订单上下文
bento gen module Order \
  --context ordering \
  --fields "customer_id:str,total:float,status:str,created_at:str,updated_at:str"

bento gen module OrderItem \
  --context ordering \
  --fields "order_id:str,product_id:str,quantity:int,price:float,subtotal:float"

# 4. 用户上下文
bento gen module User \
  --context identity \
  --fields "username:str,email:str,hashed_password:str,is_active:bool,role:str"

bento gen module Role \
  --context identity \
  --fields "name:str,permissions:str,description:str"

# 5. 库存上下文
bento gen module Stock \
  --context inventory \
  --fields "product_id:str,quantity:int,warehouse:str,location:str,updated_at:str"

bento gen module Warehouse \
  --context inventory \
  --fields "name:str,address:str,capacity:int,manager:str"

# 6. 支付上下文
bento gen module Payment \
  --context payment \
  --fields "order_id:str,amount:float,method:str,status:str,transaction_id:str"

# 7. 安装依赖和测试
uv pip install -e ".[dev]"

# 8. 运行测试
uv run pytest -v

# 9. 检查覆盖率
uv run pytest --cov --cov-report=html

# 10. 配置和运行
cp .env.example .env
vim .env  # 编辑配置

uvicorn main:app --reload
```

### 最终结构

```
ecommerce/
├── contexts/
│   ├── catalog/          # 产品目录（Product, Category）
│   ├── ordering/         # 订单（Order, OrderItem）
│   ├── identity/         # 用户（User, Role）
│   ├── inventory/        # 库存（Stock, Warehouse）
│   ├── payment/          # 支付（Payment）
│   └── shared/           # 共享内核
├── tests/
│   ├── catalog/
│   ├── ordering/
│   ├── identity/
│   ├── inventory/
│   └── payment/
├── api/
├── main.py
└── config.py
```

---

## 🔧 开发工作流

### 步骤 1: 实现领域逻辑

编辑 `contexts/<context>/domain/<name>.py`：

```python
# contexts/catalog/domain/product.py
class Product(AggregateRoot):
    def decrease_stock(self, quantity: int):
        """减少库存"""
        if self.stock < quantity:
            raise ValueError("库存不足")

        self.stock -= quantity
        self.add_event(ProductStockDecreasedEvent(
            product_id=self.id,
            quantity=quantity
        ))

    def update_price(self, new_price: float):
        """更新价格"""
        old_price = self.price
        self.price = new_price

        # 发布集成事件（跨上下文）
        self.add_event(ProductPriceChangedEvent(
            product_id=self.id,
            old_price=old_price,
            new_price=new_price
        ))
```

### 步骤 2: 实现用例

编辑 `contexts/<context>/application/usecases/<name>.py`

### 步骤 3: 实现仓储

根据生成的接口创建具体实现

### 步骤 4: 编写测试

完善测试骨架

### 步骤 5: 运行测试

```bash
# 首先安装 dev 依赖（包含 pytest）
uv pip install -e ".[dev]"

# 所有测试
uv run pytest -v

# 特定上下文
uv run pytest tests/catalog/ -v

# 单元测试
uv run pytest tests/catalog/unit/ -v

# 集成测试
uv run pytest tests/catalog/integration/ -v

# 带覆盖率
uv run pytest --cov

# 详细覆盖率报告
uv run pytest --cov --cov-report=html
```

> 💡 **提示**: 详细的测试指南请查看 [TESTING_GUIDE.md](./TESTING_GUIDE.md)

---

## 💡 最佳实践

### 上下文命名

**按业务能力命名**：

```bash
# ✅ 好
--context catalog       # 产品目录管理
--context ordering      # 订单处理
--context identity      # 用户身份
--context inventory     # 库存管理
--context payment       # 支付处理
--context shipping      # 物流配送

# ❌ 不好
--context crud          # 技术操作
--context database      # 基础设施
--context api           # 技术层
```

### 模块命名

**使用单数形式，首字母大写**：

```bash
# ✅ 正确
bento gen module Product --context catalog
bento gen module Order --context ordering

# ❌ 错误
bento gen module Products --context catalog  # 不要复数
bento gen module product --context catalog   # 首字母要大写
```

### 上下文大小

- **2-10 个聚合根** - 理想大小
- **单一职责** - 一个核心业务能力
- **独立演化** - 可独立修改和部署

---

## ❓ 常见问题

### Q: 忘记指定 --context 怎么办？

```bash
bento gen module Product --fields "name:str"
# ❌ error: the following arguments are required: --context
```

**解决**: context 是必填参数，必须指定。

### Q: 如何在现有项目中生成模块？

```bash
cd my-existing-project
bento gen module NewFeature --context <context> --output .
```

### Q: 可以修改生成的代码吗？

**完全可以**！生成的是模板代码，你应该：
- 添加业务逻辑到聚合根
- 实现用例的具体逻辑
- 根据注释集成 Bento 框架
- 编写完整的测试

### Q: 支持哪些字段类型？

目前支持：`str`, `int`, `float`, `bool`

如需其他类型，可以手动修改生成的代码。

### Q: 如何自定义模板？

编辑 `/workspace/bento/src/bento/toolkit/templates/*.tpl` 文件。

### Q: 生成的测试需要手动完善吗？

是的。CLI 生成测试骨架（结构和 fixtures），具体测试逻辑需要开发者实现。

---

## 📚 更多资源

- **快速开始**: 查看 [README.md](./README.md)
- **测试指南**: 查看 [TESTING_GUIDE.md](./TESTING_GUIDE.md) ⭐
- **示例项目**: `/workspace/bento/applications/ecommerce-modular/`
- **模板文件**: `/workspace/bento/src/bento/toolkit/templates/`

---

**Bento CLI - 快速构建 DDD 应用！** 🍱
