# Logto 中心身份基座目录结构设计

## 整体目录架构

```
workspace/
├── libs/auth_logto/                    # 共享认证库 (PyPI包)
│   ├── pyproject.toml
│   ├── src/auth_logto/
│   │   ├── __init__.py
│   │   ├── middleware.py              # JWT验签中间件
│   │   ├── dependencies.py            # FastAPI依赖注入
│   │   ├── vault.py                   # Secret Vault客户端
│   │   └── config.py                  # 配置管理
│   └── tests/
│
├── src/idp/framework/                  # IDP Framework
│   ├── infrastructure/identity/        # 身份基础设施层
│   │   ├── __init__.py
│   │   ├── current_user.py            # CurrentUser值对象
│   │   ├── tenant_aware_repo.py       # 租户感知仓储
│   │   └── permission_evaluator.py    # 权限评估器
│   ├── application/identity/           # 身份应用层
│   │   ├── current_user_service.py
│   │   └── authorization_service.py
│   └── domain/identity/               # 身份领域层
│       ├── user.py                    # 用户聚合根
│       ├── role.py                    # 角色实体
│       └── permission.py              # 权限值对象
│
├── src/idp/projects/                   # 子应用
│   ├── wms/                           # WMS系统
│   │   ├── pyproject.toml
│   │   ├── src/wms/
│   │   │   ├── main.py               # FastAPI应用入口
│   │   │   ├── api/                  # API路由
│   │   │   ├── domain/               # 领域层
│   │   │   ├── application/          # 应用层
│   │   │   └── infrastructure/       # 基础设施层
│   │   └── .env.wms                  # WMS环境配置
│   ├── godata/                        # GoData系统
│   └── cms/                           # CMS系统
│
├── infra/                             # 基础设施配置
│   ├── logto/                        # Logto部署配置
│   │   ├── values.yaml               # Helm values
│   │   └── secrets.yaml              # 密钥配置
│   └── monitoring/                   # 监控配置
│
├── scripts/                          # 自动化脚本
│   ├── seed-logto.ts                 # Logto种子数据脚本
│   └── deploy.sh                     # 部署脚本
│
├── .github/workflows/                # GitHub Actions
│   ├── build.yml                     # 构建流水线
│   ├── test.yml                      # 测试流水线
│   └── deploy.yml                    # 部署流水线
│
├── docs/                             # 文档
│   ├── architecture.md               # 架构文档
│   └── deployment.md                 # 部署文档
│
├── .env.shared                       # 共享环境变量
└── README.md                         # 项目总览
```

## 核心文件说明

### 1. libs/auth_logto/ (共享库)

#### pyproject.toml
```toml
[project]
name = "auth-logto"
version = "1.0.0"
description = "Logto authentication library for FastAPI"
dependencies = [
    "fastapi>=0.111.0",
    "pyjwt>=2.8.0",
    "httpx>=0.27.0",
    "cachetools>=5.0.0",
    "python-jose[cryptography]>=3.3.0"
]
```

#### src/auth_logto/middleware.py
```python
"""
Logto JWT验证中间件
"""
from fastapi import Request, HTTPException, status
from jose import jwt
import cachetools, httpx, os

ISSUER = f"{os.getenv('LOGTO_ENDPOINT').rstrip('/')}/oidc"
AUDIENCE = os.getenv("LOGTO_API_AUD")
JWKS_URI = f"{ISSUER}/jwks"

@cachetools.cached(cachetools.TTLCache(1, 3600))
def jwks():
    return httpx.get(JWKS_URI, timeout=5).json()["keys"]

async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)

    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing token")

    try:
        claims = _verify(auth[7:])
        request.state.principal = {
            "sub": claims["sub"],
            "scope": set(claims.get("scope", "").split()),
            "org_id": claims.get("organization_id"),
            "amr": claims.get("amr"),
        }
    except Exception as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    return await call_next(request)
```

#### src/auth_logto/dependencies.py
```python
"""
FastAPI依赖注入函数
"""
from fastapi import Depends, HTTPException, status, Request

def Permission(*required: str):
    def dep(req: Request):
        scopes = req.state.principal["scope"]
        miss = [s for s in required if s not in scopes]
        if miss:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"missing scope: {', '.join(miss)}"
            )
        return req.state.principal
    return Depends(dep)

def CurrentUser(req: Request):
    return req.state.principal
```

### 2. src/idp/framework/infrastructure/identity/

#### current_user.py
```python
"""
当前用户值对象
"""
from dataclasses import dataclass
from typing import Set, Optional

@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str
    email: Optional[str] = None
    scopes: Set[str] = None
    tenant_id: Optional[str] = None
    
    def has_scope(self, scope: str) -> bool:
        return scope in (self.scopes or set())
```

#### tenant_aware_repo.py
```python
"""
租户感知仓储基类
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List
from sqlalchemy import select

T = TypeVar('T')

class TenantAwareRepository(Generic[T], ABC):
    async def list_by_tenant(self, tenant_id: str) -> List[T]:
        stmt = select(self.model).where(self.model.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### 3. 子应用示例 (WMS)

#### src/wms/main.py
```python
"""
WMS系统主入口
"""
from fastapi import FastAPI, Depends
from auth_logto.middleware import auth_middleware
from auth_logto.dependencies import Permission, CurrentUser

app = FastAPI(title="WMS System")

# 添加认证中间件
app.middleware("http")(auth_middleware)

@app.get("/api/orders")
async def list_orders(
    user = Depends(CurrentUser),
    _ = Depends(Permission("orders:read"))
):
    return {"orders": [], "user": user["sub"]}

@app.post("/api/orders")
async def create_order(
    order_data: dict,
    user = Depends(CurrentUser),
    _ = Depends(Permission("orders:write"))
):
    return {"message": "Order created"}
```

### 4. 基础设施配置

#### infra/logto/values.yaml
```yaml
logto:
  replicaCount: 2
  image:
    repository: logto/logto
    tag: "1.30.1"
  env:
    - name: DB_URL
      value: "postgresql://logto:password@postgres:5432/logto"
    - name: API_ENDPOINT
      value: "https://auth.acme.io"
  ingress:
    enabled: true
    hosts:
      - host: auth.acme.io
```

#### scripts/seed-logto.ts
```typescript
import { LogtoClient } from '@logto/api';

const client = new LogtoClient({
  endpoint: process.env.LOGTO_ENDPOINT!,
  accessToken: process.env.LOGTO_ACCESS_TOKEN!,
});

async function seedLogto() {
  // 创建组织
  const org = await client.organizations.create({
    name: 'Acme Corp',
    description: 'Acme Corporation',
  });

  // 创建角色
  const adminRole = await client.roles.create({
    name: 'admin',
    description: 'Administrator',
    scopeIds: ['orders:read', 'orders:write', 'orders:delete'],
  });

  console.log('Logto seeded successfully');
}

seedLogto().catch(console.error);
```

## 目录结构优势

### 1. **清晰的职责分离**
- `libs/auth_logto/`: 可复用的认证库
- `framework/infrastructure/identity/`: 框架级身份基础设施
- `projects/*/`: 具体的业务应用

### 2. **DDD完美落地**
- 每层都有明确的职责
- 领域层纯业务语言
- 基础设施层处理技术细节

### 3. **易于维护和扩展**
- 模块化设计
- 清晰的依赖关系
- 自动化部署和测试

### 4. **企业级特性**
- 完整的CI/CD流水线
- 监控和日志
- 安全配置
- 灾难恢复

这个目录结构设计充分体现了现代软件工程的最佳实践，既保持了DDD的纯净性，又提供了完整的企业级功能支持。 