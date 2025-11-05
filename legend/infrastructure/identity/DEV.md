
下面给出 **“Logto 中心身份基座 × Python DDD Framework”** 的完整落地方案，已对齐 **Logto v 1.30.1 (2025-07-31)** 全量特性 —— 包括 **Secret Vault、Management API SDK、Security Center、Passkey 登录、QQ/SAML Connector** 等最新能力。阅读顺序：**架构总览 → 实施里程碑 → 代码与目录骨架 → 运行时与 CI/CD → 可观测 & 安全治理**。

---

## 1  目标架构

```
┌──── Logto Core v1.30.1 ────┐
│  OIDC / JWKS / SecretVault │
│  Management API / Account  │
└──────────┬─────────────────┘
           │JWT (sub, scope, organization_id, amr[passkey])
       ┌───▼───────────────────────────────────────────┐
       │ API Gateway / BFF  (FastAPI)                  │
       │  • auth_logto.middleware  ↔  JWKS TTLCache    │
       │  • PermissionEvaluator → CurrentPrincipal VO  │
       └───┬──────────┬──────────────────────────┬────┘
           │          │                          │
   ┌───────▼───┐ ┌────▼────────┐ …        ┌──────▼─────┐
   │ OrderSvc  │ │ WMS Svc     │          │ 其它微服务 │
   │ TenantAwareRepo           │          │            │
   └──────────┘ └──────────────┘          └────────────┘
```

> **一次验签**：只有 Gateway 校验 JWT；下游服务信任 `X-Principal` Header 或 mTLS。
> **DDD 落点**：
> *Infrastructure* — `auth_logto`、`jwks_cache`、`VaultClient`
> *Application* — `CurrentUser`, `AuthorizationService`
> *Domain* — 纯业务语言，不见 JWT/Logto 细节

---

## 2  实施里程碑（4 Sprint）

| Sprint         | 交付物                                                                                                                | 说明                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| **S0 基座**      | Helm Chart 部署 Logto v1.30.1<br>`infra/logto/values.yaml`<br>`SECRET_VAULT_KEK` 已配置                                 | TLS via Ingress；PG 挂载 PVC               |
| **S1 共享包**     | `libs/auth_logto/` (PyPI)<br>  • `middleware.py`<br>  • `dependencies.py`<br>  • `vault.py`<br>  • `management.py` | 单次编写，所有服务 `pip install` 即用              |
| **S2 DDD 内化**  | `idp_framework.identity` 模块<br>  • `CurrentUser` VO<br>  • `TenantAwareRepository`<br>  • `PermissionEvaluator`    | 仓储级租户隔离；Scope→Policy                    |
| **S3 运维 & 质控** | GitHub Actions<br>  • `seed-logto.ts` 用 `@logto/api` 种租户/角色<br>Playwright e2e：Passkey 登录                           | Prom + OTel dashboards；pg\_dump CronJob |

---

## 3  代码骨架

### 3.1  `libs/auth_logto/middleware.py`

```python
from fastapi import Request, HTTPException, status
from jose import jwt
import cachetools, httpx, os

ISSUER   = f"{os.getenv('LOGTO_ENDPOINT').rstrip('/')}/oidc"
AUDIENCE = os.getenv("LOGTO_API_AUD")
JWKS_URI = f"{ISSUER}/jwks"

@cachetools.cached(cachetools.TTLCache(1, 3600))
def jwks():
    return httpx.get(JWKS_URI, timeout=5).json()["keys"]

def _verify(token: str):
    hdr = jwt.get_unverified_header(token)
    key = next(k for k in jwks() if k["kid"] == hdr["kid"])
    return jwt.decode(
        token, key,
        algorithms=[key["alg"]],
        audience=AUDIENCE, issuer=ISSUER,
        options={"verify_exp": True, "verify_nbf": True},
    )

async def auth_mw(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)

    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing token")

    claims = _verify(auth[7:])
    request.state.principal = {
        "sub": claims["sub"],
        "scope": set(claims.get("scope", "").split()),
        "org_id": claims.get("organization_id"),  # 多租户上下文 :contentReference[oaicite:0]{index=0}
        "amr":  claims.get("amr"),                # passkey / pwd / social
    }
    return await call_next(request)
```

### 3.2  `libs/auth_logto/dependencies.py`

```python
from fastapi import Depends, HTTPException, status, Request

def Permission(*required: str):
    def dep(req: Request):
        scopes = req.state.principal["scope"]
        miss = [s for s in required if s not in scopes]
        if miss:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail=f"missing scope {miss}")
        return req.state.principal
    return Depends(dep)
```

### 3.3  `libs/auth_logto/vault.py` (新功能)

```python
import httpx, os, datetime

class VaultClient:
    def __init__(self):
        self._aud = f"{os.getenv('LOGTO_ENDPOINT')}/api"
        self._token_cache: tuple[str, datetime.datetime] | None = None

    async def _get_m2m_token(self) -> str:
        token, exp = self._token_cache or ("", datetime.datetime.min)
        if exp > datetime.datetime.utcnow() + datetime.timedelta(seconds=60):
            return token
        data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("LOGTO_M2M_ID"),
            "client_secret": os.getenv("LOGTO_M2M_SECRET"),
            "scope": "secrets:read",
        }
        r = await httpx.post(f"{os.getenv('LOGTO_ENDPOINT')}/oidc/token", data=data)
        r.raise_for_status()
        tok = r.json()
        self._token_cache = (tok["access_token"],
                             datetime.datetime.utcnow() + datetime.timedelta(seconds=tok["expires_in"]))
        return tok["access_token"]

    async def get_secret(self, secret_id: str):
        hdrs = {"authorization": f"Bearer {await self._get_m2m_token()}"}
        r = await httpx.get(f"{self._aud}/secrets/{secret_id}", headers=hdrs)  # Secret Vault API :contentReference[oaicite:1]{index=1}
        r.raise_for_status()
        return r.json()
```

### 3.4  应用层引用

```python
@router.post("/orders", dependencies=[Permission("orders:create")])
async def create(cmd: CreateOrder, principal=Depends(CurrentUser)):
    return order_uc.handle(cmd, principal)
```

### 3.5  `TenantAwareRepository`

```python
class TenantAwareRepo(Generic[T]):
    async def list(self, tenant: UUID):
        stmt = select(self.model).where(self.model.tenant_id == tenant)
        ...
```

---

## 4  环境与部署

| 文件                    | 样例内容                                                                          |
| --------------------- | ----------------------------------------------------------------------------- |
| `.env.shared`         | `LOGTO_ENDPOINT=https://auth.acme.io`<br>`LOGTO_API_AUD=https://api.acme.io`  |
| `.env.gateway`        | `SECRET_VAULT_KEK=<base64-32-byte>`                                           |
| `.env.orders-service` | `LOGTO_M2M_ID=svc-orders`<br>`LOGTO_M2M_SECRET=${{ vault.logto.svc-orders }}` |
| Helm Chart            | 设置 `replicaCount`, `resources`, `TRUST_PROXY_HEADER=1`, 数据卷挂载                 |

---

## 5  CI / CD Pipeline 关键节点

| 阶段          | 动作                                                                                            |
| ----------- | --------------------------------------------------------------------------------------------- |
| **Build**   | `tox` → unit tests → mypy → security scanner                                                  |
| **Seed**    | `npx ts-node scripts/seed-logto.ts` 通过 **`@logto/api` SDK** 建组织/角色/Scope ([docs.logto.io][1]) |
| **e2e**     | Playwright：Passkey 登录 → 拿 JWT → 调 `/orders` 正常；缺 Scope 得 403                                  |
| **Release** | Helm upgrade：先滚 Logto（带 Vault 变量），再滚服务；`preStop` 延迟 10s 确保连接关闭                                |
| **Backup**  | `pg_dump logto > s3://backups/logto/$(date).sql` CronJob                                      |

---

## 6  可观测 & 安全治理

| 维度                  | 实践                                                                            |
| ------------------- | ----------------------------------------------------------------------------- |
| **Trace**           | 在 `auth_middleware` 创建 OTel span `jwt.verify`; 记录 kid、duration                |
| **Metrics**         | `auth_fail_total{reason}`, `jwks_cache_hits` 推送到 Prometheus                   |
| **Security Center** | Console 打开 CAPTCHA、Identifier Lockout、Password Policy (min-length, symbol)    |
| **Passkeys**        | 前端用 `signInWithPasskey()`；后端记录 `amr=passkey`（无需代码变更）                          |
| **Email Blocklist** | Console → Security Center 勾选 “Disposable mail” (2025-05 功能) ([Logto blog][2]) |

---

## 7  版本与兼容性矩阵

| 组件               | 推荐版本                                         | 说明                          |
| ---------------- | -------------------------------------------- | --------------------------- |
| **Logto Core**   | `1.30.1`                                     | 含 Secret Vault、API SDK      |
| **@logto/api**   | `^1.30.0`                                    | CI 脚本                       |
| **@logto/react** | `^1.27.0`                                    | `signInWithPasskey()` 支持    |
| **Python deps**  | `PyJWT 2.8+`, `httpx 0.27+`, `cachetools 5+` |                             |
| **FastAPI**      | `0.111+`                                     | 支持 lifespan & OpenTelemetry |

---

### 完成标志

* **JWT 验签**：任一 API 返回 header `X-Principal-Sub` 对应前端用户 ID
* **租户隔离**：跨租户访问返回 404 / 403
* **Secret Vault**：服务端成功读取第三方 token 存储
* **e2e 通过**：Passkey+Scope 正常 / Scope 缺失403
* **Grafana**：看得到 `auth_fail_total` 曲线

---

## 8  后续深化

1. **Scope → Policy 代码生成**：CI 调 Logto Management API 导出 → Jinja2 模板生成 `permissions.py`。
2. **组织/角色继承树**：在 Domain 层实现 `Role.assign(parent)`，结合 `organization_id` 自动扩散 Scope。
3. **微服务通信**：以 M2M Token 调其他服务；或用 SPIFFE SVID 让 Gateway 颁发 mTLS 证书。
4. **灾难演练**：脚本恢复 Logto DB + S3 Secret Vault 快照 → e2e 全通过。

---

> 依照以上 Blueprint 落地，你的 **Python DDD 后端** 将：
>
> * **一次集成 Logto**，所有微服务天然继承 **SSO / RBAC / 多租户 / Secret Vault / Passkey**；
> * 操作性上由 Helm、Vault、CI Job 全流程自动化；
> * 运维面具备 OTel Trace 与 Prom Metrics；
> * 安全层与 Logto Security Center 同步策略。
>
> 如果需要具体的 **Helm values.yaml、seed-logto.ts** 脚本或 **TenantAwareRepository** 的完整实现示例，告诉我，我立即补充！

[1]: https://docs.logto.io/integrate-logto/interact-with-management-api?utm_source=chatgpt.com "Interact with Management API - Logto docs"
[2]: https://blog.logto.io/?utm_source=chatgpt.com "Logto blog · The content hub of the Logto community"
