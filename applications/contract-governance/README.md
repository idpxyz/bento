# Contract Governance Platform (P3)

企业级契约治理平台，基于 Bento Framework 的 P1/P2 能力构建。

## 概述

Contract Governance Platform 是一个独立的企业级产品，用于管理契约的生命周期、版本、审批和依赖关系。它与 Bento Framework 的 P1（Breaking Change 检测）和 P2（Mock/SDK/Generator）集成，提供完整的契约管理解决方案。

## 核心功能

### 1. 契约版本管理
- 创建和管理多个契约版本
- 版本发布和废弃
- 版本标签管理（latest, stable, deprecated）
- 版本历史查询

### 2. 审批工作流
- 创建审批流程
- 多级审批支持
- 审批意见记录
- 审批状态追踪

### 3. 变更历史
- 记录契约变更
- 变更对比分析
- 变更原因说明
- 变更审计日志

### 4. 依赖关系管理
- 追踪服务依赖
- 依赖关系查询
- 影响分析
- 依赖状态管理

## 快速开始

### 安装依赖

```bash
cd /workspace/bento/applications/contract-governance
uv sync
```

### 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等
```

### 启动应用

```bash
uv run python main.py
```

应用将在 `http://localhost:8001` 启动。

访问 API 文档：`http://localhost:8001/docs`

## API 端点

### 契约版本管理

#### 创建版本
```bash
POST /api/v1/contract-versions
Content-Type: application/json

{
  "contract_id": "order-service",
  "version": "1.0.0",
  "contract_schema": {
    "type": "object",
    "properties": {
      "order_id": {"type": "string"},
      "amount": {"type": "number"}
    }
  },
  "released_by": "john@example.com",
  "release_notes": "Initial release"
}
```

#### 获取版本
```bash
GET /api/v1/contract-versions/{contract_id}/{version}
```

#### 列出所有版本
```bash
GET /api/v1/contract-versions/{contract_id}
```

#### 发布版本
```bash
POST /api/v1/contract-versions/{contract_id}/{version}/release
```

#### 废弃版本
```bash
POST /api/v1/contract-versions/{contract_id}/{version}/deprecate
```

### 审批工作流

#### 创建审批
```bash
POST /api/v1/approvals
Content-Type: application/json

{
  "contract_id": "order-service",
  "version": "1.0.0",
  "approvers": ["alice@example.com", "bob@example.com"]
}
```

#### 获取审批
```bash
GET /api/v1/approvals/{approval_id}
```

#### 批准
```bash
POST /api/v1/approvals/{approval_id}/approve?approver=alice@example.com
```

### 变更历史

#### 记录变更
```bash
POST /api/v1/changes
Content-Type: application/json

{
  "contract_id": "order-service",
  "from_version": "1.0.0",
  "to_version": "1.1.0",
  "changed_by": "john@example.com",
  "change_type": "compatible",
  "changes": {
    "added_fields": ["status"],
    "removed_fields": []
  },
  "reason": "Add order status field"
}
```

#### 列出变更
```bash
GET /api/v1/changes/{contract_id}
```

### 依赖关系管理

#### 创建依赖
```bash
POST /api/v1/dependencies
Content-Type: application/json

{
  "contract_id": "order-service",
  "service_id": "payment-service",
  "version": "1.0.0",
  "dependency_type": "producer"
}
```

#### 列出契约依赖
```bash
GET /api/v1/dependencies/{contract_id}
```

#### 列出服务依赖
```bash
GET /api/v1/dependencies/service/{service_id}
```

## 数据库架构

### contract_versions
- id: 版本 ID
- contract_id: 契约 ID
- version: 版本号
- schema: JSON Schema 定义
- released_by: 发布人
- release_notes: 发布说明
- tags: 版本标签
- status: 版本状态 (draft, released, deprecated)
- created_at: 创建时间
- released_at: 发布时间

### contract_approvals
- id: 审批 ID
- contract_id: 契约 ID
- version: 版本号
- status: 审批状态 (pending, approved, rejected)
- approvers: 审批人列表
- approvals: 各审批人的意见
- comments: 审批意见
- created_at: 创建时间
- completed_at: 完成时间

### contract_changes
- id: 变更 ID
- contract_id: 契约 ID
- from_version: 从版本
- to_version: 到版本
- changed_by: 变更人
- change_type: 变更类型 (breaking, compatible, patch)
- changes: 具体变更内容
- reason: 变更原因
- created_at: 创建时间

### contract_dependencies
- id: 依赖 ID
- contract_id: 契约 ID
- service_id: 服务 ID
- version: 依赖版本
- dependency_type: 依赖类型 (producer, consumer)
- status: 状态 (active, deprecated, removed)
- added_at: 添加时间
- removed_at: 移除时间

## 与 Bento Framework 集成

### P1 Breaking Change 检测

```python
from bento.contracts import BreakingChangeDetector

detector = BreakingChangeDetector()
report = detector.detect(old_schema, new_schema, "1.0.0", "1.1.0")

if not report.is_compatible:
    # 记录变更
    change = ContractChange(
        contract_id="order-service",
        from_version="1.0.0",
        to_version="1.1.0",
        changed_by="john@example.com",
        change_type="breaking",
        changes=report.to_dict(),
        reason="API breaking change"
    )
```

### P2 Mock 数据生成

```python
from bento.contracts import MockGenerator

generator = MockGenerator()
mock_data = generator.generate(schema, seed=42)

# 用于测试审批流程
```

## 最佳实践

### 版本管理
1. 使用语义化版本 (Semantic Versioning)
2. 每个版本发布前进行审批
3. 记录所有变更原因
4. 维护版本兼容性矩阵

### 审批流程
1. 定义清晰的审批人列表
2. 记录所有审批意见
3. 设置审批超时机制
4. 自动通知相关方

### 依赖管理
1. 定期更新依赖关系
2. 进行影响分析
3. 规划迁移路径
4. 监控废弃版本使用

## 架构设计

```
Contract Governance Platform
├── API 层 (FastAPI)
│   ├── 版本管理端点
│   ├── 审批工作流端点
│   ├── 变更历史端点
│   └── 依赖关系端点
│
├── 业务逻辑层
│   ├── 版本管理服务
│   ├── 审批引擎
│   ├── 变更追踪
│   └── 依赖分析
│
├── 数据访问层 (SQLAlchemy)
│   ├── ContractVersion
│   ├── ContractApproval
│   ├── ContractChange
│   └── ContractDependency
│
└── 集成层
    ├── Bento P1 (Breaking Change)
    ├── Bento P2 (Mock/SDK/Generator)
    └── 外部系统 (Git, CI/CD, Slack)
```

## 后续功能

### Phase 2
- [ ] 前端管理界面 (React/Vue)
- [ ] 版本对比可视化
- [ ] 依赖关系图展示
- [ ] 兼容性矩阵可视化

### Phase 3
- [ ] Git 集成（自动检测变更）
- [ ] CI/CD 集成（自动审批）
- [ ] Slack/钉钉 通知
- [ ] 监控告警

### Phase 4
- [ ] 权限管理 (RBAC)
- [ ] 审计日志
- [ ] 数据导出
- [ ] 性能优化

## 开发指南

### 添加新端点

1. 在 `schemas.py` 中定义 Pydantic 模型
2. 在 `models.py` 中定义 SQLAlchemy 模型
3. 在 `api.py` 中实现路由

### 运行测试

```bash
uv run pytest tests/
```

### 代码风格

遵循 PEP 8 和 Black 格式化标准。

## 许可证

Proprietary - Bento Framework

## 支持

如有问题，请联系 Bento Framework 团队。
