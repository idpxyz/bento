# Applications Built with Bento Framework

这个目录包含基于 Bento 框架构建的实际应用。每个应用都展示了如何使用框架的不同特性。

## 📁 **应用列表**

### 1. **E-commerce (电商系统)** ✅

一个完整的电商订单管理系统，展示了 DDD、CQRS、Event-Driven Architecture 等模式。

**特性**:
- ✅ Order 模块 (订单管理)
- ✅ 完整的 DDD 战术模式
- ✅ Hexagonal Architecture
- ✅ CQRS 模式
- ✅ Event-Driven Architecture
- ✅ Transactional Outbox
- ✅ RESTful API
- ✅ 完整文档

**快速开始**:
```bash
cd applications/ecommerce
pip install -r requirements.txt
uvicorn applications.ecommerce.main:app --reload
```

**文档**:
- [README](ecommerce/README.md) - 完整使用指南
- [QUICKSTART](ecommerce/QUICKSTART.md) - 快速开始
- [ARCHITECTURE](ecommerce/docs/ARCHITECTURE.md) - 架构详解

**代码统计**:
- 📄 文件数: 20+
- 📝 代码行数: ~2,100 行
- 🎯 模块数: 1 (Order)
- 📡 API 端点: 4

---

## 🚀 **快速对比**

| 应用 | 类型 | 复杂度 | 状态 | 推荐用途 |
|------|------|--------|------|----------|
| **E-commerce** | 订单系统 | ⭐⭐⭐ | ✅ 完成 | 学习 DDD/CQRS/Event-Driven |

## 📚 **学习路径**

### 初学者

1. **阅读文档**: 先阅读 [E-commerce README](ecommerce/README.md)
2. **运行应用**: 按照 QUICKSTART 启动应用
3. **测试 API**: 使用 Swagger UI 测试
4. **理解架构**: 阅读 ARCHITECTURE.md

### 进阶

1. **研究代码**: 从 Domain 层开始，逐层向外
2. **修改功能**: 尝试添加新字段或方法
3. **扩展模块**: 参考 Order 模块，创建新模块
4. **编写测试**: 为现有功能编写测试

### 高级

1. **性能优化**: 添加缓存、数据库索引
2. **微服务拆分**: 将模块拆分为独立服务
3. **事件溯源**: 实现完整的 Event Sourcing
4. **分布式事务**: 实现 Saga 模式

## 🎯 **核心概念示例**

### 1. **DDD 聚合根**

查看 `ecommerce/modules/order/domain/order.py`:

```python
class Order(AggregateRoot):
    """订单聚合根"""

    def pay(self):
        # 业务规则
        if not self.items:
            raise DomainException(...)

        # 状态变更
        self.status = OrderStatus.PAID

        # 发布事件
        self.add_event(OrderPaid(...))
```

### 2. **CQRS Use Case**

查看 `ecommerce/modules/order/application/commands/`:

```python
class PayOrderUseCase:
    async def execute(self, command: PayOrderCommand):
        async with self.uow:
            order = await self.repo.find_by_id(...)
            order.pay()
            await self.repo.update(order)
            await self.uow.commit()
```

### 3. **RESTful API**

查看 `ecommerce/modules/order/interfaces/order_api.py`:

```python
@router.post("/{order_id}/pay")
async def pay_order(
    order_id: str,
    use_case: PayOrderUseCase = Depends(...)
):
    command = PayOrderCommand(order_id=order_id)
    return await use_case.execute(command)
```

## 🏗️ **通用架构模式**

所有应用都遵循相同的架构模式：

```
applications/{app_name}/
├── modules/                # 业务模块 (Bounded Contexts)
│   └── {module}/
│       ├── errors.py       # 错误码
│       ├── domain/         # 领域层
│       ├── application/    # 应用层
│       ├── adapters/       # 适配器层
│       └── interfaces/     # 接口层
├── runtime/                # 运行时配置
│   ├── composition.py      # 依赖注入
│   └── bootstrap.py        # 应用启动
├── main.py                 # 入口文件
├── requirements.txt        # 依赖
└── README.md               # 文档
```

## 🔧 **开发工具**

### 启动应用

```bash
# 进入应用目录
cd applications/{app_name}

# 安装依赖
pip install -r requirements.txt

# 启动应用
uvicorn applications.{app_name}.main:app --reload
```

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 查看 Swagger 文档
open http://localhost:8000/docs
```

### 查看日志

```bash
# 应用日志会输出到终端
# 包含 SQL 查询、请求响应等
```

## 📖 **相关文档**

- [Bento Framework Documentation](../docs/README.md)
- [Domain Modeling Guide](../docs/conventions/domain-modeling-guide.md)
- [Exception System Guide](../docs/infrastructure/EXCEPTION_USAGE.md)
- [Persistence Guide](../docs/infrastructure/PROJECTION_USAGE.md)

## 🤝 **贡献**

欢迎贡献新的示例应用！请遵循以下准则：

1. **遵循架构**: 使用标准的分层架构
2. **完整文档**: 包含 README、QUICKSTART、ARCHITECTURE
3. **代码质量**: 类型提示、文档字符串、无 linter 错误
4. **可运行**: 提供完整的依赖和启动脚本

## 💡 **应用创意**

以下是一些可以构建的应用示例：

### 电商领域
- ✅ Order Management (已完成)
- ⬜ Product Catalog
- ⬜ Inventory Management
- ⬜ Shopping Cart
- ⬜ Payment Gateway

### 其他领域
- ⬜ Blog Platform
- ⬜ Task Management
- ⬜ Event Booking
- ⬜ Social Network
- ⬜ CMS System

## 🌟 **最佳实践**

1. **从 Domain 开始**: 先设计领域模型，再实现技术细节
2. **小步迭代**: 从简单功能开始，逐步扩展
3. **测试驱动**: 为关键业务逻辑编写测试
4. **文档优先**: 写代码前先写文档，理清思路
5. **参考示例**: 遇到问题时参考 E-commerce 应用

## 📞 **获取帮助**

- 📖 阅读框架文档: [docs/](../docs/)
- 🔍 查看示例代码: [ecommerce/](ecommerce/)
- 💬 提问讨论: [GitHub Discussions](https://github.com/your-repo/discussions)
- 🐛 报告问题: [GitHub Issues](https://github.com/your-repo/issues)

---

**开始构建你的应用吧！** 🚀

