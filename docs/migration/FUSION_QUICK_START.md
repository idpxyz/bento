# Legend 融合升级 - 快速开始指南

> 🚀 **目标**：第一周立即开始，完成 Mapper 系统融合的基础搭建

**阅读时间**：5 分钟
**执行时间**：1 周

---

## ⚡ 5 分钟快速理解

### 我们要做什么？

**融合 Legend 的自动化和 Bento 的类型安全**，让开发者可以选择：

```python
# 方式1: 零配置（Legend风格）- 3行代码 ⭐ 推荐简单场景
class WarehouseRepo(EnhancedRepository[Warehouse, WarehousePO, str]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Warehouse, WarehousePO, AutoMapper(Warehouse, WarehousePO))

# 方式2: 混合模式（最佳实践）- 减少70%代码 ⭐⭐ 推荐复杂场景
class OrderRepo(EnhancedRepository[Order, OrderModel, str]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Order, OrderModel, HybridMapper(Order, OrderModel))

    # 只需添加特殊查询
    async def find_unpaid(self) -> List[Order]:
        spec = FluentBuilder(OrderModel).equals("status", "pending").build()
        return await self.find_many(spec)

# 方式3: 完全控制（Bento风格）- 保持现有方式
class CustomRepo(EnhancedRepository[Product, ProductPO, str]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Product, ProductPO, ExplicitMapper())
    # ... 完全手动控制
```

### 为什么要做？

| 指标 | 当前 Bento | 融合后 | 提升 |
|------|----------|--------|------|
| Repository 代码量 | 50-100 行 | 3-30 行 | **60-94% ↓** |
| Mapper 代码量 | 40 行 | 15 行 | **62% ↓** |
| Use Case 代码量 | 50 行 | 20 行 | **60% ↓** |
| 开发时间 | 1 天 | 1-2 小时 | **75% ↓** |

---

## 📅 第一周详细计划

### Day 1-2: Mapper 基础搭建（重点！）

#### 任务清单

**Morning - 创建目录结构**
```bash
# 1. 创建分支
cd /workspace/bento
git checkout -b fusion/week1-mapper-foundation

# 2. 创建目录
mkdir -p src/bento/infrastructure/mapper
mkdir -p tests/unit/infrastructure/mapper
mkdir -p tests/integration/infrastructure/mapper
mkdir -p examples/mapper
mkdir -p docs/infrastructure

# 3. 创建基础文件
touch src/bento/infrastructure/mapper/__init__.py
touch src/bento/infrastructure/mapper/base.py
touch src/bento/infrastructure/mapper/auto.py
touch src/bento/infrastructure/mapper/explicit.py
touch src/bento/infrastructure/mapper/hybrid.py

touch tests/unit/infrastructure/mapper/__init__.py
touch tests/unit/infrastructure/mapper/test_base.py
touch tests/unit/infrastructure/mapper/test_auto.py
touch tests/unit/infrastructure/mapper/test_hybrid.py

touch examples/mapper/__init__.py
touch examples/mapper/auto_mapper_demo.py
touch examples/mapper/hybrid_mapper_demo.py
```

**Afternoon - 实现 MapperStrategy 基类**

文件：`src/bento/infrastructure/mapper/base.py`

```python
"""Mapper 系统基础抽象

融合 Legend 的自动化和 Bento 的类型安全。
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T_Domain = TypeVar('T_Domain')
T_PO = TypeVar('T_PO')


class MapperStrategy(ABC, Generic[T_Domain, T_PO]):
    """映射器策略基类

    提供 Domain Entity ↔ Persistence Object 的双向映射。

    Example:
        ```python
        class UserMapper(MapperStrategy[User, UserPO]):
            def to_po(self, user: User) -> UserPO:
                return UserPO(id=user.id.value, name=user.name)

            def to_domain(self, po: UserPO) -> User:
                return User(id=ID(po.id), name=po.name)
        ```
    """

    @abstractmethod
    def to_po(self, domain: T_Domain) -> T_PO:
        """将 Domain Entity 转换为 Persistence Object

        Args:
            domain: 领域实体

        Returns:
            持久化对象
        """
        pass

    @abstractmethod
    def to_domain(self, po: T_PO) -> T_Domain:
        """将 Persistence Object 转换为 Domain Entity

        Args:
            po: 持久化对象

        Returns:
            领域实体
        """
        pass

    def to_po_list(self, domains: list[T_Domain]) -> list[T_PO]:
        """批量转换 Domain → PO"""
        return [self.to_po(d) for d in domains]

    def to_domain_list(self, pos: list[T_PO]) -> list[T_Domain]:
        """批量转换 PO → Domain"""
        return [self.to_domain(po) for po in pos]
```

**测试文件**：`tests/unit/infrastructure/mapper/test_base.py`

```python
"""MapperStrategy 基类测试"""

from dataclasses import dataclass
import pytest
from bento.infrastructure.mapper.base import MapperStrategy


@dataclass
class User:
    id: str
    name: str


@dataclass
class UserPO:
    id: str
    name: str


class SimpleMapper(MapperStrategy[User, UserPO]):
    """简单的测试映射器"""

    def to_po(self, domain: User) -> UserPO:
        return UserPO(id=domain.id, name=domain.name)

    def to_domain(self, po: UserPO) -> User:
        return User(id=po.id, name=po.name)


def test_to_po():
    """测试 Domain → PO"""
    mapper = SimpleMapper()
    user = User(id="1", name="Alice")
    po = mapper.to_po(user)

    assert po.id == "1"
    assert po.name == "Alice"


def test_to_domain():
    """测试 PO → Domain"""
    mapper = SimpleMapper()
    po = UserPO(id="1", name="Alice")
    user = mapper.to_domain(po)

    assert user.id == "1"
    assert user.name == "Alice"


def test_to_po_list():
    """测试批量转换 Domain → PO"""
    mapper = SimpleMapper()
    users = [
        User(id="1", name="Alice"),
        User(id="2", name="Bob"),
    ]
    pos = mapper.to_po_list(users)

    assert len(pos) == 2
    assert pos[0].id == "1"
    assert pos[1].id == "2"


def test_to_domain_list():
    """测试批量转换 PO → Domain"""
    mapper = SimpleMapper()
    pos = [
        UserPO(id="1", name="Alice"),
        UserPO(id="2", name="Bob"),
    ]
    users = mapper.to_domain_list(pos)

    assert len(users) == 2
    assert users[0].id == "1"
    assert users[1].id == "2"
```

**验收标准**：
- ✅ 文件创建完成
- ✅ 基类实现完成
- ✅ 4个测试全部通过
- ✅ 类型检查通过（`mypy src/bento/infrastructure/mapper/base.py`）

---

### Day 3-4: AutoMapper 实现

#### 核心实现

文件：`src/bento/infrastructure/mapper/auto.py`

```python
"""自动映射器 - Legend 风格

零配置，约定优于配置。
"""

from dataclasses import fields, is_dataclass
from typing import Type, Generic, TypeVar

from .base import MapperStrategy

T_Domain = TypeVar('T_Domain')
T_PO = TypeVar('T_PO')


class AutoMapper(MapperStrategy[T_Domain, T_PO]):
    """自动映射器

    特性：
    - ✅ 零配置，基于字段名自动匹配
    - ✅ 支持 dataclass 和普通类
    - ✅ 可选的字段名映射
    - ✅ 字段排除列表

    适用场景：
    - 简单 CRUD
    - 字段名一致的对象
    - 快速原型开发

    Example:
        ```python
        # 零配置使用
        mapper = AutoMapper(User, UserPO)
        po = mapper.to_po(user)

        # 自定义字段映射
        mapper = AutoMapper(
            User, UserPO,
            field_mapping={'user_id': 'id'},  # user.user_id → po.id
            exclude_fields={'password'}        # 排除 password 字段
        )
        ```
    """

    def __init__(
        self,
        domain_class: Type[T_Domain],
        po_class: Type[T_PO],
        field_mapping: dict[str, str] | None = None,
        exclude_fields: set[str] | None = None,
    ):
        """初始化自动映射器

        Args:
            domain_class: Domain 实体类
            po_class: PO 持久化对象类
            field_mapping: 字段名映射 {domain_field: po_field}
            exclude_fields: 需要排除的字段集合
        """
        self.domain_class = domain_class
        self.po_class = po_class
        self.field_mapping = field_mapping or {}
        self.exclude_fields = exclude_fields or set()

    def to_po(self, domain: T_Domain) -> T_PO:
        """自动映射 Domain → PO"""
        # 1. 提取 Domain 的字段
        if is_dataclass(domain):
            data = {
                f.name: getattr(domain, f.name)
                for f in fields(domain)
                if f.name not in self.exclude_fields
            }
        else:
            data = {
                k: v for k, v in domain.__dict__.items()
                if not k.startswith('_') and k not in self.exclude_fields
            }

        # 2. 应用字段映射
        for domain_field, po_field in self.field_mapping.items():
            if domain_field in data:
                data[po_field] = data.pop(domain_field)

        # 3. 创建 PO 对象
        return self.po_class(**data)

    def to_domain(self, po: T_PO) -> T_Domain:
        """自动映射 PO → Domain"""
        # 1. 提取 PO 的字段
        if is_dataclass(po):
            data = {
                f.name: getattr(po, f.name)
                for f in fields(po)
                if f.name not in self.exclude_fields
            }
        else:
            data = {
                k: v for k, v in po.__dict__.items()
                if not k.startswith('_') and k not in self.exclude_fields
            }

        # 2. 反向应用字段映射
        reverse_mapping = {v: k for k, v in self.field_mapping.items()}
        for po_field, domain_field in reverse_mapping.items():
            if po_field in data:
                data[domain_field] = data.pop(po_field)

        # 3. 创建 Domain 对象
        return self.domain_class(**data)
```

**测试文件**：`tests/unit/infrastructure/mapper/test_auto.py`（20+ 测试）

**示例文件**：`examples/mapper/auto_mapper_demo.py`

**验收标准**：
- ✅ AutoMapper 实现完成
- ✅ 20+ 测试全部通过
- ✅ 示例可运行
- ✅ 文档完善

---

### Day 5: 验证、文档和 Code Review

#### Morning - 集成测试

创建 `tests/integration/infrastructure/mapper/test_auto_integration.py`

测试 AutoMapper 与实际的 Domain 和 PO 对象集成。

#### Afternoon - 文档完善

创建 `docs/infrastructure/MAPPER_GUIDE.md`（第一版）

内容：
1. Mapper 系统概述
2. AutoMapper 使用指南
3. 最佳实践
4. 常见问题

#### Evening - Code Review

- ✅ 代码质量检查
- ✅ 类型检查
- ✅ 测试覆盖率（目标 > 85%）
- ✅ 文档完整性

---

## 🎯 Week 1 验收标准

### 必须完成 ✅

- [ ] `MapperStrategy` 基类实现
- [ ] `AutoMapper` 完整实现
- [ ] 25+ 单元测试通过
- [ ] 类型检查 100% 通过
- [ ] 基础文档完成

### 可选完成 ⭐

- [ ] `ExplicitMapper` 基类（简单）
- [ ] 集成测试（与现有 ecommerce 集成）
- [ ] 性能基准测试

---

## 📊 进度追踪

**每日检查点**：

| Day | 任务 | 预期成果 | 状态 |
|-----|------|---------|------|
| 1 | 目录结构 + 基类 | MapperStrategy 完成 | ⏳ |
| 2 | 基类测试 | 4个测试通过 | ⏳ |
| 3 | AutoMapper 实现 | 核心逻辑完成 | ⏳ |
| 4 | AutoMapper 测试 | 20个测试通过 | ⏳ |
| 5 | 文档 + Review | 文档完成，代码审查 | ⏳ |

---

## 🚀 立即开始

### 现在就可以执行的命令

```bash
# 1. 进入项目目录
cd /workspace/bento

# 2. 创建分支
git checkout -b fusion/week1-mapper-foundation

# 3. 运行目录创建脚本（复制上面的 Day 1 命令）
mkdir -p src/bento/infrastructure/mapper
mkdir -p tests/unit/infrastructure/mapper
mkdir -p examples/mapper

# 4. 创建第一个文件
cat > src/bento/infrastructure/mapper/__init__.py << 'EOF'
"""Mapper 系统 - 融合 Legend 和 Bento 的优势

提供三种映射策略：
- AutoMapper: 零配置，自动映射（Legend 风格）
- ExplicitMapper: 完全控制，手动映射（Bento 风格）
- HybridMapper: 混合模式，最佳实践
"""

from .base import MapperStrategy
from .auto import AutoMapper

__all__ = [
    "MapperStrategy",
    "AutoMapper",
]
EOF

# 5. 开始编码！
code src/bento/infrastructure/mapper/base.py
```

---

## 💡 开发建议

### TDD 方法

```bash
# 1. 先写测试（红灯）
vim tests/unit/infrastructure/mapper/test_base.py

# 2. 运行测试（应该失败）
uv run pytest tests/unit/infrastructure/mapper/test_base.py -v

# 3. 实现代码（绿灯）
vim src/bento/infrastructure/mapper/base.py

# 4. 再次运行测试（应该通过）
uv run pytest tests/unit/infrastructure/mapper/test_base.py -v

# 5. 重构（保持绿灯）
```

### 提交策略

```bash
# 每完成一个小功能就提交
git add src/bento/infrastructure/mapper/base.py
git commit -m "feat(mapper): add MapperStrategy base class"

git add tests/unit/infrastructure/mapper/test_base.py
git commit -m "test(mapper): add base mapper tests"

git add src/bento/infrastructure/mapper/auto.py
git commit -m "feat(mapper): add AutoMapper implementation"
```

---

## 🤝 需要帮助？

- 📋 查看 [完整融合计划](./FUSION_UPGRADE_PLAN.md)
- 💬 提问或讨论
- 🐛 报告问题

---

## 🎉 Week 1 完成后

你将拥有：
- ✅ 完整的 Mapper 基础架构
- ✅ 可用的 AutoMapper（减少 60%+ 代码）
- ✅ 25+ 单元测试
- ✅ 完整的文档和示例

下一步（Week 2-3）：
- HybridMapper 实现
- 与现有代码集成
- 开始 EnhancedRepository

**Let's Go! 🚀**

