# Bento Framework 架构验证指南

## 🎯 目标

确保 Bento Framework 项目严格遵循 DDD 和六边形架构原则。

## 🔧 使用方法

### 基本验证

```bash
# 验证整个项目
bento validate

# 验证特定上下文
bento validate --context catalog

# 输出详细报告
bento validate --output validation_report.json

# CI/CD 模式（有违规时返回错误码）
bento validate --fail-on-violations
```

### 验证内容

#### 1. 分层依赖检查
- Domain 层不能依赖 Application/Infrastructure
- Application 层不能依赖具体的 Infrastructure 实现
- 所有依赖必须通过 Protocol/Interface

#### 2. ApplicationService 模式检查
- 必须继承 StandardApplicationService
- 必须使用 UnitOfWork 管理事务
- 必须使用 `async with uow:` 事务边界

#### 3. Domain 层纯度检查
- 无基础设施依赖（SQLAlchemy、Redis 等）
- 无直接数据访问代码
- 只包含纯业务逻辑

#### 4. UoW 使用模式检查
- Repository 访问必须通过 `uow.repository()`
- 不允许直接注入 Repository
- 事务提交通过 `uow.commit()`

## 📊 评分标准

| 分数范围 | 等级 | 描述 |
|---------|------|------|
| 95-100 | A+ | 架构完美，零违规 |
| 90-94 | A | 优秀，轻微问题 |
| 80-89 | B | 良好，需要改进 |
| 70-79 | C | 及格，较多问题 |
| < 70 | D | 不及格，需要重构 |

## 🔍 常见违规及修复

### 违规类型 1: Domain 层依赖基础设施

**❌ 错误示例:**
```python
# contexts/catalog/domain/product.py
from sqlalchemy import Column, String  # ❌ Domain 层导入 SQLAlchemy
```

**✅ 正确修复:**
```python
# contexts/catalog/domain/product.py
from bento.domain.aggregate import AggregateRoot  # ✅ 只依赖框架抽象
```

### 违规类型 2: ApplicationService 模式错误

**❌ 错误示例:**
```python
class ProductService:
    def __init__(self, product_repo: ProductRepository):  # ❌ 直接注入 Repository
        self.product_repo = product_repo

    async def create_product(self, data):
        product = Product(data)
        return await self.product_repo.save(product)  # ❌ 无事务管理
```

**✅ 正确修复:**
```python
class ProductApplicationService(StandardApplicationService[CreateProductCommand, ProductResult]):
    def __init__(self, uow: UnitOfWork):  # ✅ 注入 UoW
        super().__init__(uow)

    async def execute(self, command: CreateProductCommand) -> ApplicationServiceResult[ProductResult]:
        async with self.uow:  # ✅ 事务边界
            product_repo = self.uow.repository(Product)  # ✅ 通过 UoW 获取
            product = Product.create_new(command.name, command.price)

            saved_product = await product_repo.save(product)
            await self.uow.commit()  # ✅ 事务提交

            return ApplicationServiceResult.success(
                ProductResult.from_aggregate(saved_product)
            )
```

### 违规类型 3: 跨层直接调用

**❌ 错误示例:**
```python
# Application 层直接导入具体实现
from bento.adapters.messaging.pulsar.message_bus import PulsarMessageBus  # ❌
```

**✅ 正确修复:**
```python
# Application 层只依赖抽象
from bento.application.ports.message_bus import MessageBus  # ✅
```

## 🎯 集成到开发流程

### 1. 开发时验证

```bash
# 生成新模块后立即验证
bento gen module Product --context catalog
bento validate --context catalog
```

### 2. Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash
bento validate --fail-on-violations
if [ $? -ne 0 ]; then
    echo "❌ Architecture validation failed. Please fix violations before committing."
    exit 1
fi
```

### 3. CI/CD 流水线

```yaml
# .github/workflows/validation.yml
- name: Architecture Validation
  run: |
    bento validate --fail-on-violations --output validation_report.json

- name: Upload Validation Report
  uses: actions/upload-artifact@v2
  with:
    name: validation-report
    path: validation_report.json
```

## 📈 持续改进

### 监控合规性趋势
```bash
# 每日运行并记录分数
bento validate --output "reports/validation_$(date +%Y%m%d).json"

# 对比历史趋势
python scripts/analyze_validation_trend.py
```

### 团队培训指标
- 新人代码合规率目标: > 90%
- 每月架构评审必须包含验证报告
- 违规修复时间: < 1 工作日

## 🏆 最佳实践

### 1. 预防优于修复
- 使用 Bento CLI 生成标准代码
- 代码审查时检查架构合规性
- 定期团队培训 DDD 原则

### 2. 渐进式改进
- 优先修复高优先级违规
- 新代码必须 100% 合规
- 老代码逐步重构

### 3. 工具化流程
- IDE 插件实时检查
- 自动化修复建议
- 可视化架构依赖图

## ⚡ 性能优化

验证工具性能优化建议:
- 只验证变更的文件（增量验证）
- 并行检查多个上下文
- 缓存 AST 解析结果

## 🎯 目标和期望

通过持续的架构验证，团队应该达到:
- 📊 **合规分数**: 持续保持 95+ 分
- 🚀 **开发效率**: 减少架构返工时间
- 🧠 **团队能力**: 人人理解 DDD 原则
- 🏗️ **代码质量**: 架构清晰、易维护

**记住: 架构验证不是为了限制，而是为了确保我们构建高质量、可维护的系统！** 🌟
