# Ecommerce API 测试指南

本文档提供了测试 Ecommerce 应用 API 的快速指南，特别是新集成的 **FluentSpecificationBuilder** 功能。

---

## 🚀 启动应用

### 1. 初始化数据库

```bash
cd /workspace/bento
uv run python applications/ecommerce/init_db.py
```

**预期输出**：
```
Initializing database...
Creating tables for application...
Tables created successfully!

Verifying tables...
Found 3 tables:
  - orders
  - order_items
  - outbox

Database initialization complete!
```

### 2. 启动 API 服务器

```bash
cd /workspace/bento
uv run uvicorn applications.ecommerce.main:app --reload --port 8000
```

**预期输出**：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 📋 API 端点测试

### 1. 创建订单 (POST /orders)

**请求**：
```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-001",
    "items": [
      {
        "product_id": "prod-001",
        "product_name": "iPhone 15 Pro",
        "quantity": 1,
        "unit_price": 999.99
      },
      {
        "product_id": "prod-002",
        "product_name": "AirPods Pro",
        "quantity": 2,
        "unit_price": 249.99
      }
    ]
  }'
```

**预期响应**：
```json
{
  "order_id": "ord-xxxxx",
  "customer_id": "cust-001",
  "status": "pending",
  "total_amount": 1499.97,
  "items": [
    {
      "product_id": "prod-001",
      "product_name": "iPhone 15 Pro",
      "quantity": 1,
      "unit_price": 999.99
    },
    {
      "product_id": "prod-002",
      "product_name": "AirPods Pro",
      "quantity": 2,
      "unit_price": 249.99
    }
  ],
  "created_at": "2025-11-06T10:00:00",
  "created_by": "api"
}
```

---

### 2. ✨ 列出订单 (GET /orders) - FluentSpecificationBuilder

这是新集成的 **FluentSpecificationBuilder** 功能！

#### 2.1 列出所有订单

```bash
curl "http://localhost:8000/orders"
```

#### 2.2 按客户ID筛选

```bash
curl "http://localhost:8000/orders?customer_id=cust-001"
```

#### 2.3 按状态筛选

```bash
curl "http://localhost:8000/orders?status=paid"
```

#### 2.4 按金额范围筛选

```bash
curl "http://localhost:8000/orders?min_amount=100&max_amount=2000"
```

#### 2.5 组合条件

```bash
curl "http://localhost:8000/orders?customer_id=cust-001&status=pending&min_amount=500"
```

#### 2.6 分页

```bash
# 第1页，每页10条
curl "http://localhost:8000/orders?page=1&page_size=10"

# 第2页，每页20条
curl "http://localhost:8000/orders?page=2&page_size=20"
```

#### 2.7 完整示例（所有参数）

```bash
curl "http://localhost:8000/orders?customer_id=cust-001&status=paid&min_amount=100&max_amount=2000&page=1&page_size=20"
```

**预期响应**：
```json
{
  "items": [
    {
      "order_id": "ord-xxxxx",
      "customer_id": "cust-001",
      "status": "paid",
      "total_amount": 1499.97,
      "created_at": "2025-11-06T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 3. 查询单个订单 (GET /orders/{order_id})

```bash
curl "http://localhost:8000/orders/ord-xxxxx"
```

**预期响应**：
```json
{
  "order_id": "ord-xxxxx",
  "customer_id": "cust-001",
  "status": "pending",
  "total_amount": 1499.97,
  "items": [
    {
      "product_id": "prod-001",
      "product_name": "iPhone 15 Pro",
      "quantity": 1,
      "unit_price": 999.99
    }
  ],
  "created_at": "2025-11-06T10:00:00"
}
```

---

### 4. 支付订单 (POST /orders/{order_id}/pay)

```bash
curl -X POST "http://localhost:8000/orders/ord-xxxxx/pay" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**预期响应**：
```json
{
  "order_id": "ord-xxxxx",
  "status": "paid",
  "paid_at": "2025-11-06T10:05:00"
}
```

---

### 5. 取消订单 (POST /orders/{order_id}/cancel)

```bash
curl -X POST "http://localhost:8000/orders/ord-xxxxx/cancel" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Customer requested cancellation"
  }'
```

**预期响应**：
```json
{
  "order_id": "ord-xxxxx",
  "status": "cancelled",
  "cancelled_at": "2025-11-06T10:10:00",
  "reason": "Customer requested cancellation"
}
```

---

## 🧪 测试 FluentSpecificationBuilder 功能

### 完整测试流程

```bash
# 1. 创建多个订单
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-001", "items": [{"product_id": "p1", "product_name": "Product 1", "quantity": 1, "unit_price": 100}]}'

curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-001", "items": [{"product_id": "p2", "product_name": "Product 2", "quantity": 1, "unit_price": 500}]}'

curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-002", "items": [{"product_id": "p3", "product_name": "Product 3", "quantity": 1, "unit_price": 1500}]}'

# 2. 测试各种筛选条件
echo "=== Test 1: All orders ==="
curl "http://localhost:8000/orders"

echo "\n=== Test 2: Filter by customer ==="
curl "http://localhost:8000/orders?customer_id=cust-001"

echo "\n=== Test 3: Filter by amount range ==="
curl "http://localhost:8000/orders?min_amount=400&max_amount=1000"

echo "\n=== Test 4: Pagination ==="
curl "http://localhost:8000/orders?page=1&page_size=2"

# 3. 支付一个订单
ORDER_ID="<替换为实际 order_id>"
curl -X POST "http://localhost:8000/orders/${ORDER_ID}/pay" -H "Content-Type: application/json" -d '{}'

# 4. 测试状态筛选
echo "\n=== Test 5: Filter by status ==="
curl "http://localhost:8000/orders?status=paid"
curl "http://localhost:8000/orders?status=pending"
```

---

## 🎯 FluentSpecificationBuilder 特性验证

以下查询测试了 **FluentSpecificationBuilder** 的核心特性：

### 1. ✅ `equals()` 操作符
```bash
curl "http://localhost:8000/orders?customer_id=cust-001"
```
**验证**：返回指定客户的订单

### 2. ✅ `greater_than_or_equal()` / `less_than_or_equal()` 操作符
```bash
curl "http://localhost:8000/orders?min_amount=100&max_amount=1000"
```
**验证**：返回金额在 100-1000 范围内的订单

### 3. ✅ `order_by(descending=True)` 排序
```bash
curl "http://localhost:8000/orders"
```
**验证**：订单按 `created_at` 降序排列（最新的在前）

### 4. ✅ `paginate(page, size)` 分页
```bash
curl "http://localhost:8000/orders?page=1&page_size=10"
```
**验证**：返回第1页，每页10条，包含 `total`, `page`, `page_size` 等分页信息

### 5. ✅ 动态条件构建
```bash
# 只传部分参数
curl "http://localhost:8000/orders?customer_id=cust-001"

# 传所有参数
curl "http://localhost:8000/orders?customer_id=cust-001&status=paid&min_amount=100&max_amount=2000&page=1&page_size=20"
```
**验证**：FluentBuilder 能正确处理可选参数，只添加有值的过滤条件

### 6. ✅ 软删除自动过滤
```bash
curl "http://localhost:8000/orders"
```
**验证**：默认不返回 `deleted_at IS NOT NULL` 的订单（软删除记录）

---

## 📊 API 文档

启动应用后，可以访问以下地址查看自动生成的 API 文档：

- **Swagger UI**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc

---

## 🐛 常见问题

### 1. 端口被占用

**错误**：`[Errno 48] error while attempting to bind on address ('127.0.0.1', 8000): address already in use`

**解决**：
```bash
# 方式 1: 使用其他端口
uv run uvicorn applications.ecommerce.main:app --reload --port 8001

# 方式 2: 杀掉占用端口的进程
lsof -ti:8000 | xargs kill -9
```

### 2. 数据库表不存在

**错误**：`no such table: orders`

**解决**：
```bash
# 重新初始化数据库
uv run python applications/ecommerce/init_db.py
```

### 3. 订单创建失败

**错误**：`ValidationError: Order must have items`

**原因**：`items` 数组为空或 `null`

**解决**：确保请求中 `items` 数组至少包含一个商品

---

## 💡 提示

### 1. 使用 `jq` 格式化 JSON 响应

```bash
curl "http://localhost:8000/orders" | jq .
```

### 2. 使用 Postman 或 Insomnia

对于更复杂的测试，推荐使用图形化工具：
- **Postman**：https://www.postman.com/
- **Insomnia**：https://insomnia.rest/

### 3. 查看日志

```bash
# 查看应用日志
tail -f /workspace/bento/applications/ecommerce/app.log

# 或直接在终端查看 uvicorn 输出
```

---

## 🎓 延伸阅读

- **FluentSpecificationBuilder 完整指南**：`docs/guides/FLUENT_SPECIFICATION_GUIDE.md`
- **BaseUseCase 使用**：`src/bento/application/usecase.py`
- **融合升级计划**：`docs/migration/FUSION_UPGRADE_PLAN.md`
- **Phase 2 完成报告**：`FUSION_PHASE2_SUCCESS_REPORT.md`

---

**祝测试愉快！** 🚀

