下面是 **Gatekeeper（策略中心 & 审计聚合）** 的**最终完整方案**与**实施步骤/方法**。设计已经与 **Logto v1.30+** 对齐，确保**不复刻 IAM**（登录/用户/角色/组织、MFA/Passkey、Security Center、Secret Vault 仍由 Logto 提供），Gatekeeper 只做 **授权策略（RBAC→ABAC/场景化）** 与 **统一审计**；对外给 **Guardian（BFF）** 和各领域微服务一个**一致**且**低侵入**的授权与审计接口。

---

## 0. 边界与目标

* **Logto（唯一 IAM）**：OIDC 登录、Token 签发与续签、用户/角色/组织（多租户）、Security Center、Secret Vault、Management API（M2M）。
* **Gatekeeper（你要实现）**：

  1. `policy.evaluate`：把 **JWT scope（RBAC）+ 上下文属性（ABAC/SoD/时段/租户）** 统一裁决；
  2. `audit`：聚合 BFF/微服务/Logto Webhook 的审计事件；
  3. `webhook`：接收 Logto 事件触发策略缓存刷新/补审计。
* **Guardian（BFF）**：面向前端的聚合/变形/缓存/实验；调用 Gatekeeper 的策略与审计接口。

> **纪律**：Gatekeeper 不提供 `auth/login|refresh|logout`、`users/*`、`roles/*`、`orgs/*` 等接口，不建对应数据表。

---

## 1. 目标架构

```
Browser ──(OIDC)──► Logto
   │  JWT                ▲ Webhook
   ▼                     │
Guardian(BFF) ──► Gatekeeper ◄───────┐
   │         policy/audit            │
   ├─────────► Order/WMS/... (BC) ───┘ 审计写入
```

---

## 2. API 规范（Gatekeeper 对外）

### 2.1 策略评估（单条/批量）

* `POST /policy/evaluate`

```json
{
  "principal": { "sub":"u1","org_id":"o1","scope":["orders:create","orders:read"], "attrs":{"dept":"Sales"} },
  "action": "create",
  "resource": "orders",
  "context": { "org_id":"o1", "ip":"1.2.3.4" }
}
```

**响应**

```json
{ "allow": true, "obligations": ["log_reason:business_hours_only"], "explain": "rule#12" }
```

* `POST /policy/batch`（可选）：一次评估多条 action/resource，列表/表格权限批量加速。

### 2.2 审计

* `POST /audit`

```json
{
  "actor_sub":"u1","org_id":"o1","action":"orders.create","resource_id":"ord-99",
  "decision":"allow","reason":"rule#12","scope_snapshot":"orders:create orders:read",
  "req_id":"trace-abc","extra":{"duration_ms":42}
}
```

* `GET /audit/events?actor_sub=u1&from=...&to=...&limit=100`

### 2.3 Webhook（来自 Logto）

* `POST /webhook/logto`：用户/角色/组织变更 → 失效相关缓存、补审计。

---

## 3. 数据与策略模型

### 3.1 审计表（PostgreSQL）

```sql
CREATE TABLE audit_event (
  id BIGSERIAL PRIMARY KEY,
  event_time    TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_sub     TEXT NOT NULL,
  org_id        TEXT,
  action        TEXT NOT NULL,
  resource_id   TEXT,
  decision      TEXT,                 -- allow/deny/na
  reason        TEXT,
  scope_snapshot TEXT,
  ip            INET,
  user_agent    TEXT,
  req_id        TEXT,
  extra         JSONB
);
CREATE INDEX ON audit_event (event_time DESC);
CREATE INDEX ON audit_event (actor_sub, event_time DESC);
CREATE INDEX ON audit_event (org_id, event_time DESC);
```

### 3.2 策略后端（两选一或并存）

* **OPA/Rego**（推荐）：规则声明式、测试友好；Gatekeeper 通过 HTTP 调 OPA 执行。
* **自定义 YAML DSL**：便于非技术同事维护；由 Gatekeeper 解析执行。

> Gatekeeper 的 `PolicyService` 以接口 `Executor` 抽象，OPA 与 DSL 可随配置切换；支持**短 TTL 缓存**和**批量评估**。

---

## 4. DDD 分层与目录

```
gatekeeper/
├─ app/                      # Interfaces（FastAPI）
│  ├─ routers/
│  │  ├─ policy.py
│  │  ├─ audit.py
│  │  └─ webhook_logto.py
│  └─ main.py
├─ application/              # Application
│  ├─ services/
│  │  ├─ policy_service.py   # 执行器 + 缓存 + 回退
│  │  └─ audit_service.py
│  └─ dto.py
├─ domain/                   # Domain（纯业务语言）
│  ├─ models.py              # PolicyRule/Set, AuditEvent
│  ├─ dsl.py                 # DSL 抽象/校验
│  └─ policies/              # 版本化策略（Git 管控）
├─ infrastructure/           # Infra
│  ├─ persistence.py         # SQLAlchemy 审计仓储
│  ├─ opa_client.py          # OPA 执行器
│  ├─ dsl_executor.py        # DSL 执行器
│  ├─ logto_m2m.py           # M2M token 获取/缓存（httpx+cachetools）
│  ├─ cache.py               # 短 TTL 缓存
│  ├─ telemetry.py           # OTel/Prom
│  └─ settings.py            # ENV 装载/校验
└─ tests/
   ├─ unit/
   ├─ integration/
   └─ policy/                # OPA/DSL 规则测试样例
```

---

## 5. 关键实现骨架（可直接改名落仓）

### 5.1 启动与路由

```python
# app/main.py
from fastapi import FastAPI
from app.routers import policy, audit, webhook_logto
from infrastructure.telemetry import setup_telemetry

app = FastAPI(title="Gatekeeper")
setup_telemetry(app)
app.include_router(policy.router,  prefix="/policy",  tags=["policy"])
app.include_router(audit.router,   prefix="/audit",   tags=["audit"])
app.include_router(webhook_logto.router, prefix="/webhook", tags=["webhook"])
```

### 5.2 PolicyService（带缓存与回退）

```python
# application/services/policy_service.py
from infrastructure.opa_client import OPAExecutor
from cachetools import TTLCache

class PolicyService:
    def __init__(self, executor=None, ttl=5):
        self.exec = executor or OPAExecutor()
        self.cache = TTLCache(maxsize=5000, ttl=ttl)

    async def evaluate(self, principal, action, resource, context):
        key = (principal.get("sub"), action, resource, principal.get("org_id"))
        if key in self.cache: return self.cache[key]
        try:
            allowed, meta = await self.exec.allow({
                "user":principal, "action":action, "resource":resource, "context":context
            })
        except Exception:
            # 回退：仅基于 scope 的最小授权（短时降级）
            scopes = set(principal.get("scope", []))
            need = f"{resource}:{action}"
            allowed, meta = (need in scopes, {"reason":"fallback_scope_only"})
        self.cache[key] = (allowed, meta)
        return allowed, meta
```

### 5.3 OPA 执行器

```python
# infrastructure/opa_client.py
import httpx, os
class OPAExecutor:
    def __init__(self): self.url = os.getenv("OPA_URL","http://opa:8181")
    async def allow(self, input_data: dict) -> tuple[bool, dict]:
        r = await httpx.post(f"{self.url}/v1/data/policy/allow", json={"input":input_data}, timeout=2)
        r.raise_for_status()
        allowed = bool(r.json().get("result"))
        # 可扩展查询 obligations/explain
        return allowed, {}
```

### 5.4 审计服务

```python
# application/services/audit_service.py
from infrastructure.persistence import AuditRepo
class AuditService:
    def __init__(self, repo: AuditRepo): self.repo = repo
    async def write(self, ev: dict): await self.repo.insert(ev)   # 幂等键：req_id+action+target
    async def query(self, filters: dict): return await self.repo.query(filters)
```

### 5.5 Logto M2M Token（缓存续签）

```python
# infrastructure/logto_m2m.py
import httpx, os
from cachetools import TTLCache, cached

ISSUER = os.getenv("LOGTO_ENDPOINT").rstrip("/") + "/oidc"
_cache = TTLCache(maxsize=1, ttl=300)

@cached(_cache)
def get_m2m_token():
    data = {
      "grant_type":"client_credentials",
      "client_id":os.getenv("LOGTO_M2M_ID"),
      "client_secret":os.getenv("LOGTO_M2M_SECRET"),
      "scope":"management:read management:write"
    }
    r = httpx.post(f"{ISSUER}/token", data=data, timeout=5); r.raise_for_status()
    tok = r.json(); _cache.ttl = max(30, tok["expires_in"] - 60)
    return tok["access_token"]
```

### 5.6 路由（示例）

```python
# app/routers/policy.py
from fastapi import APIRouter, Depends
from application.services.policy_service import PolicyService
router = APIRouter()

@router.post("/evaluate")
async def evaluate(payload: dict, svc: PolicyService = Depends()):
    allowed, meta = await svc.evaluate(
        payload["principal"], payload["action"], payload["resource"], payload.get("context", {})
    )
    return {"allow": bool(allowed), **({"obligations": meta.get("obligations")} if allowed else {"explain": meta.get("reason")})}
```

---

## 6. 与 Guardian/微服务接入

### 6.1 轻量客户端（libs/gatekeeper\_client）

```python
import httpx, os

class GatekeeperClient:
    def __init__(self, base=None):
        self.base = base or os.getenv("GK_BASE_URL","http://gatekeeper:8000")

    async def evaluate(self, principal, action, resource, context=None):
        r = await httpx.post(f"{self.base}/policy/evaluate",
            json={"principal":principal,"action":action,"resource":resource,"context":context or {}}, timeout=2)
        r.raise_for_status()
        if not r.json().get("allow"): raise PermissionError("policy denied")

    async def audit(self, event):
        try: await httpx.post(f"{self.base}/audit", json=event, timeout=1.5)
        except httpx.HTTPError: pass
```

### 6.2 在 BFF/服务中使用

```python
await gk.evaluate(user.dict(), "create", "orders", {"org_id": user.org_id})
# 成功后写审计（失败不阻断主流程）
await gk.audit({"actor_sub":user.id,"org_id":user.org_id,"action":"orders.create","decision":"allow","req_id":trace_id})
```

---

## 7. 安全与配置

* **服务间信任**：mTLS（首选）或 HMAC 签名头（`X-Signature: HMAC(key, timestamp|nonce|body)`）
* **最小权限**：Gatekeeper 仅持 M2M 的最小 Scope；密钥从 Vault/KMS 注入，不入镜像/代码
* **Webhook 验签**：Logto Webhook Secret + 幂等键/过期时间
* **CORS/限流**：在 Ingress/ALB 层完成；GK 只对内网或受控调用暴露

**环境变量最小集**

```bash
LOGTO_ENDPOINT=https://auth.example.com
LOGTO_M2M_ID=svc-gk
LOGTO_M2M_SECRET=********
OPA_URL=http://opa:8181
GK_BASE_URL=http://gatekeeper:8000
```

---

## 8. 观测与性能

* **OTel Traces**：`policy.evaluate`、`audit.write`；贯穿 `req_id/trace_id`

* **Prom 指标**：

  * `gatekeeper_policy_evaluate_latency_ms_bucket`
  * `gatekeeper_policy_denied_total{reason}`
  * `gatekeeper_audit_saved_total`
  * `gatekeeper_m2m_token_refresh_total{result}`

* **性能基线**（可通过基准脚本/CI 执行）：

  * 目标：p95 `< 20ms`（缓存命中 `< 5ms`），错误率 `< 0.1%`；
  * 调优：短 TTL 缓存（2–10s）、批量评估、连接池/HTTP2、并发执行器。

---

## 9. 部署（Helm 摘要）

`helm/gatekeeper/values.yaml`

```yaml
image:
  repository: ghcr.io/acme/gatekeeper
  tag: "1.0.0"
env:
  LOGTO_ENDPOINT: "https://auth.example.com"
  LOGTO_M2M_ID: "svc-gk"
  LOGTO_M2M_SECRET: "${{ vault.logto.svc-gk }}"
  OPA_URL: "http://opa:8181"
service:
  type: ClusterIP
ingress:
  enabled: false
resources:
  requests: { cpu: "100m", memory: "256Mi" }
  limits: { cpu: "500m", memory: "512Mi" }
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 60
```

---

## 10. CI/CD（GitHub Actions 样例）

```yaml
name: Gatekeeper CI
on: [push, pull_request]
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e .[dev]  # 安装依赖
      - run: pytest -q              # 单元/集成/策略测试
  compliance-guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r tools/gk-guard/requirements.txt
      - run: python tools/gk-guard/gk_guard.py all  # 路由/表/密钥扫描 + mTLS 配置 + bench
  deploy:
    if: github.ref == 'refs/heads/main' && needs.build-test.result == 'success'
    runs-on: ubuntu-latest
    steps:
      - uses: azure/setup-helm@v4
      - run: helm upgrade --install gatekeeper helm/gatekeeper -f helm/values-prod.yaml
```

> **说明**：`tools/gk-guard` 是我给你的合规脚本（可选但强烈建议），会阻止“影子 IAM”回弹、检查 TLS/mTLS、跑 `/policy/evaluate` 基线。

---

## 11. 实施路线（逐 Sprint）

* **S0 基座（1 周）**：仓库/骨架、健康检查、Helm（初版）、Postgres schema、基础 CI。
* **S1 策略（2 周）**：OPA sidecar 或 DSL 执行器、`/policy/evaluate`、缓存与回退、策略单测。
* **S2 审计（1 周）**：`/audit`、查询、幂等与重试、结构化日志。
* **S3 对接 Logto（1 周）**：Webhook、M2M 管理调用（在需要时）、缓存失效。
* **S4 观测与安全（1 周）**：OTel/Prom、mTLS/HMAC、WAF/限流、备份。
* **S5 压测与灰度（0.5–1 周）**：p95<20ms，灰度发布/回滚演练。

---

## 12. 迁移与验收

**迁移**

* 从旧系统移除登录/用户/角色/组织 CRUD 与本地密码/刷新逻辑；前端统一走 Logto。
* 微服务/BFF 全部改为 `GK /policy/evaluate`；UI 侧根据 scope/策略隐藏按钮。

**验收 Checklist**

* [ ] 禁用 `orders:create` scope → 列表按钮隐藏、API 403、GK 审计记录 `deny`
* [ ] OPA 暂不可用 → GK 回退“只看 scope”，同时报警
* [ ] Grafana 有 `policy_denied_total` 曲线，bench p95 < 20ms
* [ ] PR 合规检查：无 IAM 路由/表/前端密钥，Helm 声明 TLS/mTLS，bench 通过

---

### 总结

这套 **Gatekeeper 最终方案**保证：

* **不复刻 Logto**（IAM 职能完全在 Logto），只补**策略中台**与**审计中台**的企业刚需；
* **接入成本极低**：BFF 与微服务统一调用一个 `evaluate()` + `audit()`；
* **可运营**：策略可测试/可回滚/可观测；有合规护栏避免“越界开发”。

如果你把现有仓库的**路径/技术栈细节**贴给我，我可以把以上骨架与脚本**替换为可运行的最小模板**，并提供一份 **OPA/DSL 策略示例包**（含 30+ 单元规则测试），帮助你当天起步。
