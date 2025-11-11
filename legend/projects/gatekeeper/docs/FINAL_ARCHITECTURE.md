# Gatekeeper 最终架构设计

## 核心理念

**Gatekeeper = Policy BFF + 审计聚合器**，专注业务策略编排和审计聚合，不重复实现IAM功能。

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    Logto Core (v1.30.1)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   OAuth2    │ │   OIDC      │ │   管理台    │ │   API   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   API Gateway     │
                    │  • JWT验签        │
                    │  • Scope→Policy   │
                    └─────────┬─────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼──────┐ ┌▼──────┐ ┌▼──────┐
            │  Gatekeeper  │ │ WMS   │ │GoData │
            │ (策略&审计)   │ │       │ │       │
            └──────────────┘ └───────┘ └───────┘
```

## 核心职责

### 1. **业务策略编排**
- 复杂业务规则评估（如：仓库管理员可在所属仓库代下单）
- 动态权限计算（基于时间、地点、金额等上下文）
- 策略缓存和性能优化

### 2. **审计聚合**
- 聚合Logto Webhook事件
- 聚合微服务业务事件
- 统一审计日志存储和查询

### 3. **事件驱动**
- 处理组织创建/用户角色变更等事件
- 触发业务流程（如：租户配额设置、计费记录创建）
- 发送通知和集成外部系统

## 项目结构

```
src/idp/projects/gatekeeper/
├── pyproject.toml
├── src/gatekeeper/
│   ├── __init__.py
│   ├── main.py                    # FastAPI应用入口
│   ├── api/                       # API路由
│   │   ├── policy.py             # 策略评估API
│   │   ├── audit.py              # 审计查询API
│   │   └── events.py             # 事件接收API
│   ├── application/              # 应用层
│   │   ├── policy_service.py     # 策略编排服务
│   │   ├── audit_service.py      # 审计聚合服务
│   │   └── event_handler.py      # 事件处理器
│   ├── domain/                   # 领域层
│   │   ├── policy.py             # 策略值对象
│   │   ├── audit_event.py        # 审计事件
│   │   └── business_rule.py      # 业务规则
│   └── infrastructure/           # 基础设施层
│       ├── logto_client.py       # Logto Management API客户端
│       ├── audit_repository.py   # 审计仓储
│       └── event_bus.py          # 事件总线
├── tests/
├── config/                       # 配置文件
│   ├── policies.yaml             # 策略配置
│   └── scopes.yaml               # Scope映射配置
└── .env.gatekeeper
```

## 核心API设计

### 1. **策略评估API** (`/policy/evaluate`)
```python
@router.post("/evaluate")
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    policy_service: PolicyService = Depends()
) -> PolicyResult:
    """业务策略评估"""
    try:
        result = await policy_service.evaluate_business_policy(
            user_id=request.user_id,
            action=request.action,
            resource=request.resource,
            context=request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. **审计查询API** (`/audit/events`)
```python
@router.get("/events")
async def get_audit_events(
    user_id: str = Query(None),
    organization_id: str = Query(None),
    event_type: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    audit_service: AuditService = Depends()
):
    """查询审计事件"""
    events = await audit_service.get_audit_events(
        user_id=user_id,
        organization_id=organization_id,
        event_type=event_type,
        page=page,
        size=size
    )
    return events
```

### 3. **事件接收API**
```python
@router.post("/webhook/logto")
async def logto_webhook(
    event: dict,
    event_handler: EventHandler = Depends()
):
    """接收Logto Webhook事件"""
    try:
        await event_handler.handle_logto_event(event)
        return {"status": "processed", "event_id": event.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/microservice")
async def microservice_event(
    event: dict,
    event_handler: EventHandler = Depends()
):
    """接收微服务自定义事件"""
    try:
        await event_handler.handle_microservice_event(event)
        return {"status": "processed", "event_id": event.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 动态M2M Token管理

```python
class LogtoClient:
    """Logto Management API客户端"""
    
    async def _get_m2m_token(self) -> str:
        """动态获取M2M Token"""
        # 检查缓存
        if self._token_cache:
            token, expiry = self._token_cache
            if expiry > datetime.utcnow() + timedelta(seconds=60):
                return token
        
        # 获取新Token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "management:read management:write",
        }
        
        response = await self._http_client.post(
            f"{self.endpoint}/oidc/token",
            data=data,
            timeout=5
        )
        response.raise_for_status()
        
        token_data = response.json()
        token = token_data["access_token"]
        expires_in = token_data["expires_in"]
        
        # 缓存Token
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        self._token_cache = (token, expiry)
        
        return token
```

## 配置管理

### 1. **策略配置** (`config/policies.yaml`)
```yaml
policies:
  order.create:
    rules:
      - name: "warehouse_manager"
        condition: "user.is_warehouse_manager(resource)"
        allowed: true
        reason: "warehouse_manager"
      - name: "amount_limit"
        condition: "context.amount <= 10000"
        allowed: true
        reason: "standard_permission"
      - name: "finance_approver"
        condition: "user.has_scope('finance:approve')"
        allowed: true
        reason: "finance_approver"
```

### 2. **Scope映射配置** (`config/scopes.yaml`)
```yaml
scope_mappings:
  "orders:read":
    - "order.read"
  "orders:write":
    - "order.create"
    - "order.update"
  "warehouse:manage":
    - "warehouse.manage"
```

## 子应用集成

### 1. **WMS系统集成**
```python
@app.post("/api/orders")
async def create_order(
    order_data: dict,
    user = Depends(CurrentUser),
    _ = Depends(Permission("orders:write"))
):
    """创建订单 - 需要业务策略评估"""
    
    # 调用Gatekeeper进行业务策略评估
    policy_result = await gatekeeper_client.evaluate_policy({
        "user_id": user["sub"],
        "action": "order.create",
        "resource": order_data["warehouse_id"],
        "context": {
            "amount": order_data["amount"],
            "customer_id": order_data["customer_id"]
        }
    })
    
    if not policy_result.allowed:
        raise HTTPException(403, detail=policy_result.reason)
    
    # 创建订单
    order = await order_service.create_order(order_data, user["sub"])
    
    # 发送审计事件
    await gatekeeper_client.record_event({
        "type": "order.created",
        "user_id": user["sub"],
        "resource": order.id,
        "metadata": order_data
    })
    
    return order
```

## 可观测性

### 1. **OpenTelemetry集成**
```python
@router.post("/evaluate")
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    policy_service: PolicyService = Depends()
) -> PolicyResult:
    with tracer.start_as_current_span("policy.evaluate") as span:
        span.set_attribute("user_id", request.user_id)
        span.set_attribute("action", request.action)
        span.set_attribute("resource", request.resource)
        
        result = await policy_service.evaluate_business_policy(
            user_id=request.user_id,
            action=request.action,
            resource=request.resource,
            context=request.context
        )
        
        span.set_attribute("result.allowed", result.allowed)
        span.set_attribute("result.reason", result.reason)
        
        return result
```

### 2. **Prometheus指标**
```python
# 策略评估指标
policy_evaluations_total = Counter(
    'policy_evaluations_total',
    'Total number of policy evaluations',
    ['action', 'result']
)

policy_evaluation_duration = Histogram(
    'policy_evaluation_duration_seconds',
    'Time spent evaluating policies',
    ['action']
)

# 审计事件指标
audit_events_total = Counter(
    'audit_events_total',
    'Total number of audit events',
    ['source', 'type']
)
```

## 部署配置

### 1. **Helm Values** (`infra/gatekeeper/values.yaml`)
```yaml
gatekeeper:
  replicaCount: 2
  
  image:
    repository: acme/gatekeeper
    tag: "1.0.0"
    pullPolicy: IfNotPresent
  
  env:
    - name: LOGTO_ENDPOINT
      value: "https://auth.acme.io"
    - name: LOGTO_M2M_ID
      valueFrom:
        secretKeyRef:
          name: gatekeeper-secrets
          key: logto-m2m-id
    - name: LOGTO_M2M_SECRET
      valueFrom:
        secretKeyRef:
          name: gatekeeper-secrets
          key: logto-m2m-secret
  
  # 可观测性配置
  monitoring:
    enabled: true
    serviceMonitor:
      enabled: true
      interval: "30s"
  
  # 回滚钩子
  hooks:
    preRollback:
      enabled: true
      command: ["/bin/sh", "-c", "echo 'Pre-rollback hook executed'"]
```

## 最小路由清单

| 路由 | 方法 | 说明 |
|------|------|------|
| `/policy/evaluate` | POST | 业务策略评估 |
| `/audit/events` | GET | 查询审计事件 |
| `/webhook/logto` | POST | Logto Webhook入站 |
| `/events/microservice` | POST | 微服务自定义事件 |

## 总结

这个最终架构设计：

### 1. **职责收敛一致**
- ✅ 完全移除用户/角色/租户CRUD
- ✅ 完全移除登录/刷新/登出API
- ✅ 专注策略编排和审计聚合

### 2. **技术细节完整**
- ✅ 动态M2M Token管理
- ✅ 策略缓存和性能优化
- ✅ 幂等键和重试机制

### 3. **端到端闭环**
- ✅ Gateway Scope→Policy转换
- ✅ 前端策略配置获取
- ✅ 完整审计链路

### 4. **可观测和运维**
- ✅ OpenTelemetry集成
- ✅ Prometheus指标
- ✅ Helm回滚钩子

这个架构真正实现了**"Policy BFF + 审计聚合器"**的定位，避免了功能重复，提供了完整的企业级能力！ 🎯 