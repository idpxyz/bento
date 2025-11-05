# Logto 中心身份基座实施计划

## 概述

基于您现有的DDD框架，将Logto作为"中心身份基座"集成到IDP Framework中，实现所有子应用的统一身份认证、授权、多租户和安全合规能力。

## 架构设计

### 1. 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                    Logto 身份服务 (外部)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   OAuth2    │ │   OIDC      │ │   管理台    │ │   API   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼──────┐ ┌▼──────┐ ┌▼──────┐
            │   WMS        │ │ GoData│ │  CMS  │
            │  系统        │ │ 系统  │ │ 系统  │
            └──────────────┘ └───────┘ └───────┘
                              │
                    ┌─────────▼─────────┐
                    │   IDP Framework   │
                    │  ┌─────────────┐  │
                    │  │  Logto      │  │
                    │  │  Adapter    │  │
                    │  └─────────────┘  │
                    └───────────────────┘
```

### 2. Framework 集成结构
```
src/idp/framework/infrastructure/identity/
├── __init__.py                 # 模块导出
├── config.py                   # Logto 配置管理
├── logto_adapter.py            # Logto API 适配器
├── auth_middleware.py          # 认证中间件
├── README.md                   # 架构文档
├── example_usage.py            # 使用示例
└── IMPLEMENTATION_PLAN.md      # 实施计划
```

## 核心功能

### 1. 统一认证 (SSO)
- **OAuth 2.1 / OpenID Connect** 标准协议
- **多种认证方式**: 密码、社交登录、MFA
- **统一登录体验**: 一次登录，访问所有子应用

### 2. 基于角色的访问控制 (RBAC)
- **细粒度权限控制**: 基于权限和角色的访问控制
- **动态权限分配**: 通过Logto管理台动态分配
- **权限继承机制**: 角色继承和权限组合

### 3. 多租户支持
- **租户隔离**: 数据和服务级别的租户隔离
- **资源配额管理**: 每个租户的资源限制
- **租户配置管理**: 独立的租户配置

### 4. 安全合规
- **审计日志**: 完整的操作审计记录
- **数据加密**: 敏感数据加密传输
- **合规报告**: 自动生成合规报告

## 实施步骤

### 阶段一：Logto 部署和配置 (1-2天)

#### 1.1 部署 Logto 服务
```bash
# 使用 Docker 部署 Logto
docker run -d \
  --name logto \
  -p 3001:3001 \
  -p 3002:3002 \
  -e DB_URL=postgresql://user:pass@localhost:5432/logto \
  -e ADMIN_CONSOLE_URL=http://localhost:3002 \
  -e API_ENDPOINT=http://localhost:3001 \
  logto/logto:latest
```

#### 1.2 配置多租户
- 在Logto管理台创建租户
- 配置租户隔离策略
- 设置资源配额

#### 1.3 创建应用配置
- 为每个子应用创建OAuth应用
- 配置重定向URI
- 设置权限范围

### 阶段二：Framework 集成 (2-3天)

#### 2.1 实现核心组件
- [x] Logto配置管理 (`config.py`)
- [x] Logto适配器 (`logto_adapter.py`)
- [x] 认证中间件 (`auth_middleware.py`)

#### 2.2 集成到Framework
```python
# 在 Framework 的依赖注入中注册
from idp.framework.infrastructure.identity import LogtoAdapter, LogtoConfig

def register_identity_services(container):
    # 注册 Logto 配置
    logto_config = LogtoConfig(
        endpoint=os.getenv("LOGTO_ENDPOINT"),
        app_id=os.getenv("LOGTO_APP_ID"),
        app_secret=os.getenv("LOGTO_APP_SECRET"),
        redirect_uri=os.getenv("LOGTO_REDIRECT_URI")
    )
    
    # 注册 Logto 适配器
    container.register(LogtoAdapter, lambda: LogtoAdapter(logto_config))
```

#### 2.3 添加配置支持
```yaml
# config/identity.yml
logto:
  endpoint: "https://logto.example.com"
  app_id: "${LOGTO_APP_ID}"
  app_secret: "${LOGTO_APP_SECRET}"
  redirect_uri: "http://localhost:8000/auth/callback"
  scopes:
    - "openid"
    - "profile"
    - "email"
```

### 阶段三：子应用集成 (3-5天)

#### 3.1 WMS 系统集成
```python
# src/idp/projects/wms/main.py
from fastapi import FastAPI, Depends
from idp.framework.infrastructure.identity import (
    init_logto_adapter, 
    get_current_user, 
    require_permission
)

app = FastAPI()

# 初始化 Logto
init_logto_adapter(wms_logto_config)

@app.get("/api/orders")
async def get_orders(user = Depends(get_current_user)):
    return {"orders": [], "user": user.username}

@app.post("/api/orders")
async def create_order(
    order_data: dict,
    user = Depends(require_permission("wms:write"))
):
    return {"message": "Order created"}
```

#### 3.2 GoData 系统集成
```python
# src/idp/projects/godata/main.py
from idp.framework.infrastructure.identity import (
    init_logto_adapter, 
    get_current_user, 
    require_role
)

app = FastAPI()

# 初始化 Logto
init_logto_adapter(godata_logto_config)

@app.get("/api/records")
async def get_records(user = Depends(get_current_user)):
    return {"records": [], "tenant": user.tenant_id}

@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: str,
    user = Depends(require_role("data_admin"))
):
    return {"message": f"Record {record_id} deleted"}
```

#### 3.3 CMS 系统集成
```python
# src/idp/projects/cms/main.py
from idp.framework.infrastructure.identity import (
    init_logto_adapter, 
    get_current_user, 
    require_permission
)

app = FastAPI()

# 初始化 Logto
init_logto_adapter(cms_logto_config)

@app.get("/api/content")
async def get_content(user = Depends(get_current_user)):
    return {"content": [], "user": user.username}

@app.post("/api/content")
async def create_content(
    content_data: dict,
    user = Depends(require_permission("cms:write"))
):
    return {"message": "Content created"}
```

### 阶段四：测试和优化 (2-3天)

#### 4.1 功能测试
- [ ] SSO 登录流程测试
- [ ] 权限控制测试
- [ ] 多租户隔离测试
- [ ] 令牌刷新测试

#### 4.2 性能测试
- [ ] 并发用户测试
- [ ] 响应时间测试
- [ ] 内存使用测试

#### 4.3 安全测试
- [ ] 令牌验证测试
- [ ] 权限绕过测试
- [ ] 租户隔离测试

## 配置示例

### 1. 环境变量配置
```bash
# .env
LOGTO_ENDPOINT=https://logto.example.com
LOGTO_APP_ID=your-app-id
LOGTO_APP_SECRET=your-app-secret
LOGTO_REDIRECT_URI=http://localhost:8000/auth/callback
```

### 2. 应用配置
```python
# 每个子应用的配置
wms_config = LogtoConfig(
    endpoint="https://logto.example.com",
    app_id="wms-app-id",
    app_secret="wms-app-secret",
    redirect_uri="http://localhost:8000/auth/callback",
    scopes=["openid", "profile", "email", "wms:read", "wms:write"]
)

godata_config = LogtoConfig(
    endpoint="https://logto.example.com",
    app_id="godata-app-id",
    app_secret="godata-app-secret",
    redirect_uri="http://localhost:8001/auth/callback",
    scopes=["openid", "profile", "email", "godata:read", "godata:write"]
)
```

## 优势

### 1. 标准化
- 使用 OAuth 2.1 / OpenID Connect 标准
- 兼容现有的身份管理工具
- 支持多种客户端类型

### 2. 简化开发
- 无需实现复杂的身份逻辑
- 统一的API接口
- 自动处理令牌管理

### 3. 安全性
- 专业的安全团队维护
- 定期安全更新
- 完整的审计日志

### 4. 可扩展性
- 支持多种认证方式
- 灵活的角色权限模型
- 多租户架构

## 总结

通过这个简化的集成方案，我们实现了：

1. **最小化代码**: 只需要3个核心文件
2. **标准化集成**: 使用OAuth 2.1/OIDC标准
3. **天然SSO**: 所有子应用自动支持SSO
4. **统一管理**: 通过Logto管理台统一管理用户和权限
5. **安全可靠**: 专业的安全团队维护

这个方案充分利用了Logto的能力，避免了重复造轮子，同时保持了代码的简洁性和可维护性。 