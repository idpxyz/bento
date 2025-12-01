# Bento Framework 分层架构标准

## 🏗️ 分层职责定义

### 📚 Domain Layer (领域层)
**核心原则**: 纯业务逻辑，零基础设施依赖

#### ✅ 允许的依赖
```python
# 只能依赖同层或更内层组件
from bento.domain.aggregate import AggregateRoot
from bento.domain.entity import Entity
from bento.domain.value_object import ValueObject
from bento.domain.domain_event import DomainEvent
from bento.domain.domain_service import DomainService
from bento.core.ids import EntityId  # 核心基础类型
```

#### ❌ 禁止的依赖
```python
# 绝对不能依赖这些
from bento.persistence.uow import UnitOfWork           # ❌ 事务管理
from bento.infrastructure.repository import Repository # ❌ 数据访问
from bento.application.ports.message_bus import MessageBus # ❌ 消息总线
from bento.adapters.* import *                        # ❌ 任何适配器
```

#### 📋 职责清单
- ✅ **业务规则**: 封装在Entity/AggregateRoot内
- ✅ **业务计算**: 通过DomainService提供
- ✅ **业务验证**: 输入验证和业务约束
- ✅ **领域事件**: 发布业务状态变化事件
- ❌ **数据访问**: 不能直接访问数据库
- ❌ **事务管理**: 不能管理事务边界
- ❌ **基础设施**: 不能调用外部服务

---

### 📋 Application Layer (应用层)
**核心原则**: 协调Domain对象，管理用例和事务

#### ✅ 允许的依赖
```python
# 可以依赖Domain和自身层组件
from bento.domain.* import *                    # ✅ 所有Domain组件
from bento.application.ports.* import *        # ✅ 端口抽象
from bento.persistence.uow import UnitOfWork   # ✅ 事务管理
from bento.core.* import *                     # ✅ 核心组件
```

#### ❌ 禁止的依赖
```python
# 不能依赖具体实现
from bento.adapters.* import *                 # ❌ 具体适配器
from bento.infrastructure.database import *   # ❌ 数据库实现
from bento.persistence.repository.sqlalchemy import * # ❌ 具体Repository
```

#### 📋 职责清单
- ✅ **用例协调**: 实现业务用例流程
- ✅ **事务管理**: 通过UnitOfWork管理事务边界
- ✅ **Repository协调**: 通过UoW获取Repository
- ✅ **事件处理**: 处理领域事件和集成事件
- ✅ **DTO转换**: Domain对象与外部数据的转换
- ❌ **业务逻辑**: 不能包含业务规则
- ❌ **直接数据访问**: 不能绕过Repository抽象

---

### 🔧 Infrastructure Layer (基础设施层)
**核心原则**: 提供技术实现，适配外部系统

#### ✅ 允许的依赖
```python
# 可以依赖所有层的抽象
from bento.domain.ports.* import *             # ✅ Domain端口
from bento.application.ports.* import *       # ✅ Application端口
from bento.persistence.* import *             # ✅ 持久化抽象
from sqlalchemy import *                      # ✅ 外部技术库
from redis import *                           # ✅ 外部技术库
```

#### 📋 职责清单
- ✅ **Repository实现**: RepositoryAdapter适配Domain到Persistence
- ✅ **MessageBus实现**: 消息中间件的具体实现
- ✅ **外部API适配**: 第三方服务的防腐层
- ✅ **技术配置**: 数据库、缓存、消息队列配置
- ❌ **业务逻辑**: 不能包含业务规则
- ❌ **用例流程**: 不能实现业务用例

---

## 🔒 强制性约束

### 1. ApplicationService标准模板
```python
# ✅ 强制模式：所有ApplicationService必须遵循
class StandardApplicationService:
    def __init__(self, uow: UnitOfWork):  # 必须依赖UoW
        self.uow = uow

    async def execute_use_case(self, command: Command) -> Result:
        async with self.uow:  # 必须使用事务边界
            # 1. 输入验证
            # 2. 加载聚合 (通过uow.repository)
            # 3. 执行业务逻辑 (委托给Domain)
            # 4. 保存结果 (通过uow.commit)
            pass
```

### 2. Repository访问标准
```python
# ✅ 正确：通过UoW访问
async def use_case(self, command):
    async with self.uow:
        repo = self.uow.repository(Order)  # ✅ 标准方式
        order = await repo.get(command.order_id)

# ❌ 禁止：直接注入Repository
def __init__(self, order_repo: OrderRepository):  # ❌ 违反标准
    self.order_repo = order_repo
```

### 3. 事件发布标准
```python
# ✅ 正确：通过聚合发布，UoW自动处理
order.add_event(OrderCreatedEvent(...))  # Domain层发布
await self.uow.commit()                  # Application层处理

# ❌ 禁止：直接使用MessageBus
await self.message_bus.publish(event)    # ❌ 绕过UoW
```

---

## 🛡️ 架构守护规则

### 依赖方向检查
```python
# 工具脚本：检查依赖违规
def check_layer_dependencies():
    """检查分层依赖是否违规"""
    violations = []

    # Domain层不能依赖Application/Infrastructure
    domain_files = find_files("src/bento/domain/")
    for file in domain_files:
        if has_import(file, "bento.application") or has_import(file, "bento.infrastructure"):
            violations.append(f"Domain layer violation in {file}")

    return violations
```

### ApplicationService模式检查
```python
def check_application_service_pattern():
    """检查ApplicationService是否符合标准"""
    app_services = find_application_services()

    for service in app_services:
        # 必须有UoW依赖
        if not has_uow_dependency(service):
            violations.append(f"{service} must depend on UnitOfWork")

        # 必须使用事务边界
        if not uses_transaction_boundary(service):
            violations.append(f"{service} must use 'async with uow' pattern")
```

---

## 📊 合规性检查清单

### Domain Layer检查
- [ ] 无Repository/UoW/MessageBus依赖
- [ ] 业务逻辑封装在Entity/AggregateRoot内
- [ ] DomainService只包含纯函数
- [ ] 所有方法都是纯函数或有明确副作用边界

### Application Layer检查
- [ ] 所有ApplicationService依赖UnitOfWork
- [ ] 使用标准事务边界模式
- [ ] Repository访问通过uow.repository()
- [ ] 不包含业务逻辑，只有协调逻辑

### Infrastructure Layer检查
- [ ] 实现Domain/Application端口
- [ ] 不包含业务逻辑
- [ ] 正确的适配器模式实现
- [ ] 配置和技术细节封装

---

## 🎯 实施计划

### Phase 1: 现有代码审查
1. 运行依赖检查脚本
2. 识别违规组件
3. 制定修复优先级

### Phase 2: 逐步修复
1. 高优先级违规立即修复
2. 中优先级违规计划修复
3. 低优先级违规文档记录

### Phase 3: 防护机制
1. CI/CD集成检查脚本
2. 代码审查检查清单
3. 开发者培训和文档

这个标准将确保Bento Framework严格遵循DDD和六边形架构原则！
