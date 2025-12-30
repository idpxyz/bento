# my-shop 脚本

本目录包含 my-shop 应用的各种脚本和工具。

---

## 📁 目录结构

```
scripts/
├── demo/          # 演示脚本
├── debug/         # 调试工具
└── test/          # 测试脚本
```

---

## 🎯 demo/ - 演示脚本

**用途**: 演示框架功能和使用模式

### 可用脚本

- `demo_event_handlers.py` - 事件处理器演示
- `demo_repository_mixins.py` - Repository Mixins 演示
- `scenario_complete_shopping_flow.py` - 完整购物流程演示

### 使用方式

```bash
# 运行事件处理器演示
python scripts/demo/demo_event_handlers.py

# 运行完整购物流程
python scripts/demo/scenario_complete_shopping_flow.py
```

---

## 🐛 debug/ - 调试工具

**用途**: 调试和问题排查工具

### 可用工具

- `debug_tenant.py` - 租户调试工具
- `manual_test_outbox.py` - Outbox 手动测试
- `verify_outbox.sql` - Outbox 验证 SQL

### 使用方式

```bash
# 调试租户功能
python scripts/debug/debug_tenant.py

# 手动测试 Outbox
python scripts/debug/manual_test_outbox.py

# 验证 Outbox 记录
sqlite3 my_shop.db < scripts/debug/verify_outbox.sql
```

---

## 🧪 test/ - 测试脚本

**用途**: 自动化测试脚本

### 可用脚本

- `test_idempotency.sh` - 幂等性测试
- `test_idempotency_simple.sh` - 简化幂等性测试
- `test_middleware.sh` - 中间件测试
- `test_order_flow.sh` - 订单流程测试
- `run_scenario_clean.sh` - 清理场景测试

### 使用方式

```bash
# 运行幂等性测试
bash scripts/test/test_idempotency.sh

# 运行中间件测试
bash scripts/test/test_middleware.sh

# 运行订单流程测试
bash scripts/test/test_order_flow.sh
```

---

## 🎓 最佳实践

### 1. 脚本命名
- 演示脚本: `demo_*.py`
- 调试工具: `debug_*.py` 或 `manual_*.py`
- 测试脚本: `test_*.sh` 或 `run_*.sh`

### 2. 脚本位置
- 演示相关 → `demo/`
- 调试相关 → `debug/`
- 测试相关 → `test/`

### 3. 脚本文档
每个脚本应包含：
- 用途说明
- 使用示例
- 依赖要求

### 4. 可执行权限
```bash
# 添加执行权限
chmod +x scripts/test/*.sh
```

---

## 📝 添加新脚本

1. 确定脚本类型（demo/debug/test）
2. 在对应目录创建脚本
3. 添加清晰的文档字符串
4. 更新本 README

---

## 🔧 常用命令

### 查看所有脚本
```bash
find scripts/ -type f -name "*.py" -o -name "*.sh"
```

### 批量添加执行权限
```bash
chmod +x scripts/**/*.sh
```

### 运行所有测试脚本
```bash
for script in scripts/test/*.sh; do
    echo "Running $script..."
    bash "$script"
done
```

---

**最后更新**: 2024-12-30
