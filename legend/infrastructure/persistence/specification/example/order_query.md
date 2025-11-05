好的，我来详细分析 `order_queries.py` 这个文件。这是一个非常好的规格模式（Specification Pattern）实践示例。

## 📋 文件概览

`order_queries.py` 是一个**规格模式查询示例库**，展示了如何使用 `SpecificationBuilder` 构建复杂的订单查询。

## 🏗️ 核心架构模式

### **规格模式（Specification Pattern）**
```python
# 基本模式
def query_function(params) -> Specification:
    return (SpecificationBuilder()
        .filter(field, value)
        .select(fields...)
        .include(relations...)
        .add_sort(field, direction)
        .build())
```

### **查询构建流程**
1. **创建 Builder** → `SpecificationBuilder()`
2. **添加过滤条件** → `.filter()`, `.where()`, `.between()`
3. **字段选择** → `.select()`
4. **关系预加载** → `.include()`
5. **排序分页** → `.add_sort()`, `.set_page()`
6. **构建规格** → `.build()`

## 🔍 查询功能分析

### 1. **简单查询** - `find_recent_orders()`
```python
def find_recent_orders(days: int = 7) -> Specification:
    return (SpecificationBuilder()
        .between("created_at", start_date, end_date)  # 日期范围
        .select("id", "order_number", "status"...)    # 字段选择
        .include("customer.name", "items")            # 关系预加载
        .add_sort("created_at", DESC)                 # 排序
        .build())
```

**特点：**
- 时间范围查询
- 字段选择优化
- 关系预加载
- 结果排序

### 2. **条件查询** - `find_orders_by_status()`
```python
def find_orders_by_status(status: str, customer_id: Optional[UUID] = None):
    builder = SpecificationBuilder().filter("status", status)
    
    if customer_id:  # 动态条件
        builder.filter("customer_id", customer_id)
    
    return builder.add_sort("created_at", DESC).build()
```

**特点：**
- 必选条件 + 可选条件
- 动态查询构建
- 分页支持

### 3. **全文搜索** - `search_orders()`
```python
def search_orders(search_text: str, min_amount, max_amount...):
    builder = SpecificationBuilder()
    
    # 多字段文本搜索 (OR 条件)
    builder.or_(
        lambda b: b.text_search("order_number", search_text),
        lambda b: b.text_search("customer.name", search_text)
    )
    
    # 金额范围
    if min_amount is not None or max_amount is not None:
        builder.between("total_amount", min_amount, max_amount)
    
    # 状态过滤
    if statuses:
        builder.where("status", "in", statuses)
```

**特点：**
- **OR 条件组合**：多字段搜索
- **范围查询**：金额、日期范围
- **IN 查询**：状态列表
- **动态条件**：根据参数决定是否添加

### 4. **统计查询** - `find_order_statistics()`
```python
def find_order_statistics(start_date, end_date):
    return (SpecificationBuilder()
        .between("created_at", start_date, end_date)
        .group_by("status", "DATE(created_at)")      # 分组
        .count("id", alias="order_count")            # 计数
        .sum("total_amount", alias="total_sales")    # 求和
        .avg("total_amount", alias="average_order_value")  # 平均值
        .count("customer_id", alias="unique_customers", distinct=True)  # 去重计数
        .having("order_count", ">=", 5)              # Having 条件
        .add_sort("DATE(created_at)")                # 排序
        .build())
```

**特点：**
- **聚合函数**：COUNT, SUM, AVG
- **分组查询**：GROUP BY
- **Having 条件**：聚合后过滤
- **别名支持**：字段重命名

### 5. **复杂业务规则** - `find_complex_orders()`
```python
def find_complex_orders(min_amount, vip_categories, days_ago):
    return (SpecificationBuilder()
        # 基础条件组 (AND)
        .and_(
            lambda b: b.where("total_amount", ">=", min_amount),
            lambda b: b.where("created_at", ">=", cutoff_date),
            lambda b: b.where("is_deleted", "=", False)
        )
        
        # 客户条件组 (OR) - 满足任一条件
        .or_(
            lambda b: b.where("customer.status", "=", "vip"),
            lambda b: b.where("customer.loyalty_points", ">", 1000),
            lambda b: b.where("items.category", "in", vip_categories)
        )
        
        # 支付条件组 (AND with nested OR)
        .and_(
            lambda b: b.where("payment.is_verified", "=", True),
            lambda b: b.or_(
                lambda b: b.where("payment.status", "=", "paid"),
                lambda b: b.and_(
                    lambda b: b.where("payment.has_deposit", "=", True),
                    lambda b: b.where("payment.is_scheduled", "=", True)
                )
            )
        )
        .build())
```

**业务规则分析：**
```
订单匹配条件 = 基础条件 AND 客户条件 AND 支付条件

基础条件 (必须全部满足):
├── 订单金额 >= 最小金额
├── 创建时间 >= 指定天数前  
└── 未删除

客户条件 (满足任一即可):
├── VIP 客户
├── 积分 > 1000
└── 购买过 VIP 类别商品

支付条件 (必须全部满足):
├── 支付已验证
└── 以下任一:
    ├── 已全额支付
    └── (有押金 AND 已安排分期)
```

## 🎯 设计模式亮点

### 1. **流式接口（Fluent Interface）**
```python
(SpecificationBuilder()
    .filter("status", "active")
    .select("id", "name")
    .include("customer")
    .add_sort("created_at")
    .build())
```

### 2. **Lambda 表达式组合**
```python
.or_(
    lambda b: b.text_search("order_number", text),
    lambda b: b.text_search("customer.name", text)
)
```

### 3. **动态查询构建**
```python
builder = SpecificationBuilder().filter("status", status)

if customer_id:  # 根据条件动态添加
    builder.filter("customer_id", customer_id)
```

### 4. **嵌套条件逻辑**
```python
.and_(
    lambda b: b.where("payment.is_verified", "=", True),
    lambda b: b.or_(  # 嵌套 OR 条件
        lambda b: b.where("payment.status", "=", "paid"),
        lambda b: b.and_(  # 再嵌套 AND 条件
            lambda b: b.where("payment.has_deposit", "=", True),
            lambda b: b.where("payment.is_scheduled", "=", True)
        )
    )
)
```

## 🔧 功能特性总结

| 功能 | 示例方法 | 核心特性 |
|------|----------|----------|
| **基础查询** | `find_recent_orders()` | 时间范围、字段选择、排序 |
| **条件查询** | `find_orders_by_status()` | 动态条件、分页 |
| **全文搜索** | `search_orders()` | OR条件、范围查询、IN查询 |
| **统计分析** | `find_order_statistics()` | 聚合函数、分组、Having |
| **复杂业务** | `find_complex_orders()` | 嵌套逻辑、业务规则组合 |

## 💡 架构优势

1. **类型安全**：通过 `Specification[T]` 提供编译时类型检查
2. **可组合性**：可以将简单规格组合成复杂查询
3. **可测试性**：每个查询函数独立，易于单元测试
4. **性能优化**：通过 `.select()` 和 `.include()` 控制查询字段
5. **业务语义**：查询函数名称直接表达业务意图

这个文件是规格模式在实际项目中的优秀实践，展示了如何用声明式的方式构建从简单到复杂的各种数据库查询。
