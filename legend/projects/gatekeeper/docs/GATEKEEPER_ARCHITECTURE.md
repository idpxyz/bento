# Logto 中心身份基座 - Gatekeeper 项目架构

## 重新设计的架构

```
workspace/
├── src/idp/projects/
│   ├── gatekeeper/                     # 🏛️ 中心身份基座 (独立项目)
│   │   ├── pyproject.toml
│   │   ├── src/gatekeeper/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                # FastAPI应用入口
│   │   │   ├── api/                   # API路由
│   │   │   │   ├── auth.py           # 认证API
│   │   │   │   ├── users.py          # 用户管理API
│   │   │   │   ├── roles.py          # 角色管理API
│   │   │   │   └── tenants.py        # 租户管理API
│   │   │   ├── domain/               # 领域层
│   │   │   │   ├── user.py           # 用户聚合根
│   │   │   │   ├── role.py           # 角色实体
│   │   │   │   ├── permission.py     # 权限值对象
│   │   │   │   └── tenant.py         # 租户实体
│   │   │   ├── application/          # 应用层
│   │   │   │   ├── auth_service.py   # 认证服务
│   │   │   │   ├── user_service.py   # 用户服务
│   │   │   │   ├── role_service.py   # 角色服务
│   │   │   │   └── tenant_service.py # 租户服务
│   │   │   └── infrastructure/       # 基础设施层
│   │   │       ├── logto_adapter.py  # Logto适配器
│   │   │       ├── vault_client.py   # Secret Vault客户端
│   │   │       ├── user_repository.py # 用户仓储
│   │   │       └── role_repository.py # 角色仓储
│   │   ├── tests/
│   │   ├── .env.gatekeeper           # Gatekeeper环境配置
│   │   └── README.md                 # Gatekeeper项目文档
│   │
│   ├── wms/                          # 📦 WMS系统
│   │   ├── pyproject.toml
│   │   ├── src/wms/
│   │   │   ├── main.py              # FastAPI应用入口
│   │   │   ├── api/                 # API路由
│   │   │   ├── domain/              # 领域层
│   │   │   ├── application/         # 应用层
│   │   │   └── infrastructure/      # 基础设施层
│   │   └── .env.wms                 # WMS环境配置
│   │
│   ├── godata/                       # 📊 GoData系统
│   └── cms/                          # 📝 CMS系统
│
├── libs/                             # 📚 共享库
│   ├── auth_logto/                   # Logto认证库 (PyPI包)
│   │   ├── pyproject.toml
│   │   ├── src/auth_logto/
│   │   │   ├── middleware.py        # JWT验签中间件
│   │   │   ├── dependencies.py      # FastAPI依赖注入
│   │   │   └── config.py            # 配置管理
│   │   └── tests/
│   │
│   └── gatekeeper_client/            # Gatekeeper客户端库
│       ├── pyproject.toml
│       ├── src/gatekeeper_client/
│       │   ├── client.py            # HTTP客户端
│       │   ├── models.py            # 数据模型
│       │   └── exceptions.py        # 异常定义
│       └── tests/
│
├── infra/                            # 🏗️ 基础设施配置
│   ├── gatekeeper/                   # Gatekeeper部署配置
│   │   ├── values.yaml              # Helm values
│   │   ├── ingress.yaml             # Ingress配置
│   │   └── secrets.yaml             # 密钥配置
│   ├── logto/                       # Logto部署配置
│   │   ├── values.yaml              # Helm values
│   │   └── secrets.yaml             # 密钥配置
│   └── monitoring/                  # 监控配置
│
├── scripts/                         # 🔧 自动化脚本
│   ├── seed-logto.ts                # Logto种子数据脚本
│   ├── seed-gatekeeper.ts           # Gatekeeper种子数据脚本
│   └── deploy.sh                    # 部署脚本
│
├── .github/workflows/               # 🚀 GitHub Actions
│   ├── build.yml                    # 构建流水线
│   ├── test.yml                     # 测试流水线
│   └── deploy.yml                   # 部署流水线
│
├── docs/                            # 📖 文档
│   ├── architecture.md              # 架构文档
│   ├── gatekeeper.md                # Gatekeeper文档
│   └── deployment.md                # 部署文档
│
├── .env.shared                      # 共享环境变量
└── README.md                        # 项目总览
```

## Gatekeeper 项目设计

### 1. Gatekeeper 作为中心身份基座

#### 核心职责：
- **统一认证**: 处理所有子应用的认证请求
- **用户管理**: 用户CRUD、密码管理、MFA配置
- **角色权限**: 角色定义、权限分配、策略管理
- **租户管理**: 多租户隔离、资源配额、配置管理
- **审计日志**: 完整的操作审计记录
- **安全策略**: 密码策略、登录限制、风险控制

#### 架构优势：
```
┌─────────────────────────────────────────────────────────────┐
│                    Logto 身份服务 (外部)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   OAuth2    │ │   OIDC      │ │   管理台    │ │   API   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Gatekeeper      │
                    │  ┌─────────────┐  │
                    │  │  认证服务    │  │
                    │  │  用户管理    │  │
                    │  │  角色权限    │  │
                    │  │  租户管理    │  │
                    │  │  审计日志    │  │
                    │  └─────────────┘  │
                    └─────────┬─────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼──────┐ ┌▼──────┐ ┌▼──────┐
            │   WMS        │ │ GoData│ │  CMS  │
            │  系统        │ │ 系统  │ │ 系统  │
            └──────────────┘ └───────┘ └───────┘
```

### 2. Gatekeeper 项目结构

#### src/gatekeeper/main.py
```python
"""
Gatekeeper - 中心身份基座
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .api import auth, users, roles, tenants
from .infrastructure.logto_adapter import LogtoAdapter
from .application.auth_service import AuthService

app = FastAPI(
    title="Gatekeeper - Identity Management",
    description="Centralized identity management system",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(roles.router, prefix="/api/roles", tags=["roles"])
app.include_router(tenants.router, prefix="/api/tenants", tags=["tenants"])

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "gatekeeper",
        "version": "1.0.0"
    }

@app.get("/api/me")
async def get_current_user(user = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "permissions": user.permissions,
        "tenant_id": user.tenant_id
    }
```

#### src/gatekeeper/api/auth.py
```python
"""
认证API
"""
from fastapi import APIRouter, Depends, HTTPException
from ..application.auth_service import AuthService
from ..domain.user import User
from ..infrastructure.logto_adapter import LogtoAdapter

router = APIRouter()

@router.post("/login")
async def login(credentials: LoginCredentials):
    """用户登录"""
    auth_service = AuthService()
    result = await auth_service.authenticate_user(credentials)
    
    if not result.success:
        raise HTTPException(status_code=401, detail=result.error_message)
    
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "expires_in": result.expires_in,
        "user": result.user
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """刷新访问令牌"""
    auth_service = AuthService()
    result = await auth_service.refresh_token(refresh_token)
    
    if not result.success:
        raise HTTPException(status_code=401, detail=result.error_message)
    
    return {
        "access_token": result.access_token,
        "expires_in": result.expires_in
    }

@router.post("/logout")
async def logout(user = Depends(get_current_user)):
    """用户登出"""
    auth_service = AuthService()
    await auth_service.logout_user(user.id)
    return {"message": "Logged out successfully"}
```

#### src/gatekeeper/api/users.py
```python
"""
用户管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from ..application.user_service import UserService
from ..domain.user import User, CreateUserCommand, UpdateUserCommand

router = APIRouter()

@router.get("/")
async def list_users(
    tenant_id: str = None,
    page: int = 1,
    size: int = 20,
    user = Depends(require_permission("users:read"))
):
    """获取用户列表"""
    user_service = UserService()
    users = await user_service.list_users(
        tenant_id=tenant_id or user.tenant_id,
        page=page,
        size=size
    )
    return users

@router.post("/")
async def create_user(
    command: CreateUserCommand,
    user = Depends(require_permission("users:create"))
):
    """创建用户"""
    user_service = UserService()
    new_user = await user_service.create_user(command, user.tenant_id)
    return new_user

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user = Depends(require_permission("users:read"))
):
    """获取用户详情"""
    user_service = UserService()
    user = await user_service.get_user(user_id, current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    command: UpdateUserCommand,
    current_user = Depends(require_permission("users:update"))
):
    """更新用户"""
    user_service = UserService()
    updated_user = await user_service.update_user(
        user_id, 
        command, 
        current_user.tenant_id
    )
    return updated_user

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_permission("users:delete"))
):
    """删除用户"""
    user_service = UserService()
    await user_service.delete_user(user_id, current_user.tenant_id)
    return {"message": "User deleted successfully"}
```

### 3. 共享库设计

#### libs/gatekeeper_client/pyproject.toml
```toml
[project]
name = "gatekeeper-client"
version = "1.0.0"
description = "Gatekeeper client library"
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.0.0"
]
```

#### libs/gatekeeper_client/src/gatekeeper_client/client.py
```python
"""
Gatekeeper客户端
"""
import httpx
from typing import Optional, Dict, Any
from .models import User, Role, Tenant
from .exceptions import GatekeeperException

class GatekeeperClient:
    """Gatekeeper客户端"""
    
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0
        )
    
    async def get_current_user(self) -> User:
        """获取当前用户"""
        response = await self._client.get("/api/me")
        response.raise_for_status()
        return User(**response.json())
    
    async def list_users(
        self, 
        tenant_id: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """获取用户列表"""
        params = {"page": page, "size": size}
        if tenant_id:
            params["tenant_id"] = tenant_id
        
        response = await self._client.get("/api/users", params=params)
        response.raise_for_status()
        return response.json()
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建用户"""
        response = await self._client.post("/api/users", json=user_data)
        response.raise_for_status()
        return User(**response.json())
    
    async def get_user(self, user_id: str) -> User:
        """获取用户详情"""
        response = await self._client.get(f"/api/users/{user_id}")
        response.raise_for_status()
        return User(**response.json())
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> User:
        """更新用户"""
        response = await self._client.put(f"/api/users/{user_id}", json=user_data)
        response.raise_for_status()
        return User(**response.json())
    
    async def delete_user(self, user_id: str) -> None:
        """删除用户"""
        response = await self._client.delete(f"/api/users/{user_id}")
        response.raise_for_status()
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
```

### 4. 子应用集成

#### src/wms/main.py (使用Gatekeeper)
```python
"""
WMS系统主入口 - 使用Gatekeeper
"""
from fastapi import FastAPI, Depends, HTTPException
from auth_logto.middleware import auth_middleware
from auth_logto.dependencies import Permission, CurrentUser
from gatekeeper_client import GatekeeperClient
import os

app = FastAPI(title="WMS System")

# 添加认证中间件
app.middleware("http")(auth_middleware)

# Gatekeeper客户端
gatekeeper_client = GatekeeperClient(
    base_url=os.getenv("GATEKEEPER_URL"),
    access_token=os.getenv("GATEKEEPER_TOKEN")
)

@app.get("/api/orders")
async def list_orders(
    user = Depends(CurrentUser),
    _ = Depends(Permission("orders:read"))
):
    """获取订单列表"""
    # 通过Gatekeeper验证用户权限
    current_user = await gatekeeper_client.get_current_user()
    
    return {
        "orders": [],
        "user": current_user.username,
        "tenant": current_user.tenant_id
    }

@app.post("/api/orders")
async def create_order(
    order_data: dict,
    user = Depends(CurrentUser),
    _ = Depends(Permission("orders:write"))
):
    """创建订单"""
    # 通过Gatekeeper验证用户权限
    current_user = await gatekeeper_client.get_current_user()
    
    return {
        "message": "Order created",
        "created_by": current_user.username
    }

@app.get("/api/users")
async def list_wms_users(
    user = Depends(CurrentUser),
    _ = Depends(Permission("users:read"))
):
    """获取WMS用户列表"""
    # 通过Gatekeeper获取用户列表
    users = await gatekeeper_client.list_users(
        tenant_id=user.get("org_id")
    )
    return users
```

### 5. 部署配置

#### infra/gatekeeper/values.yaml
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
    - name: LOGTO_APP_ID
      valueFrom:
        secretKeyRef:
          name: gatekeeper-secrets
          key: logto-app-id
    - name: LOGTO_APP_SECRET
      valueFrom:
        secretKeyRef:
          name: gatekeeper-secrets
          key: logto-app-secret
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: gatekeeper-secrets
          key: database-url
  
  ingress:
    enabled: true
    className: nginx
    hosts:
      - host: gatekeeper.acme.io
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: gatekeeper-tls
        hosts:
          - gatekeeper.acme.io
  
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"
```

## 架构优势

### 1. **职责清晰**
- **Gatekeeper**: 专门负责身份管理
- **子应用**: 专注业务逻辑，通过客户端调用Gatekeeper
- **共享库**: 提供标准化的客户端接口

### 2. **可维护性强**
- 身份管理逻辑集中在一个项目
- 统一的API接口和数据结构
- 独立的部署和扩展

### 3. **安全性高**
- 统一的权限控制
- 集中的审计日志
- 标准化的安全策略

### 4. **扩展性好**
- 新应用只需集成客户端库
- 支持多种认证方式
- 灵活的多租户架构

### 5. **运维友好**
- 独立的监控和日志
- 统一的配置管理
- 简化的部署流程

## 总结

将Logto中心身份基座作为独立的`gatekeeper`项目确实更加科学和合理：

1. **符合微服务架构**: 每个服务职责单一
2. **便于团队协作**: 身份管理团队专注Gatekeeper
3. **提高可维护性**: 身份逻辑集中管理
4. **增强安全性**: 统一的安全策略和审计
5. **简化集成**: 子应用只需集成客户端库

这种架构设计既保持了DDD的纯净性，又提供了完整的企业级身份管理能力！ 🏛️ 