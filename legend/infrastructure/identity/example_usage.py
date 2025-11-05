"""
Logto 集成使用示例

展示如何在子应用中使用 Logto 中心身份基座
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBearer

from .auth_middleware import (
    get_current_user,
    init_logto_adapter,
    require_permission,
    require_role,
)
from .config import LogtoConfig

# 创建 FastAPI 应用
app = FastAPI(title="WMS System with Logto Integration")

# 初始化 Logto 配置
logto_config = LogtoConfig(
    endpoint="https://logto.example.com",
    app_id="wms-app-id",
    app_secret="wms-app-secret",
    redirect_uri="http://localhost:8000/auth/callback",
    scopes=["openid", "profile", "email", "wms:read", "wms:write"]
)

# 初始化 Logto 适配器
init_logto_adapter(logto_config)


# 示例 1: 基本认证
@app.get("/api/orders")
async def get_orders(user = Depends(get_current_user)):
    """获取订单列表 - 需要认证"""
    return {
        "message": f"Hello {user.username}",
        "orders": [
            {"id": "1", "status": "pending"},
            {"id": "2", "status": "completed"}
        ]
    }


# 示例 2: 基于权限的访问控制
@app.post("/api/orders")
async def create_order(
    order_data: dict,
    user = Depends(require_permission("wms:write"))
):
    """创建订单 - 需要 wms:write 权限"""
    return {
        "message": f"Order created by {user.username}",
        "order": order_data
    }


# 示例 3: 基于角色的访问控制
@app.delete("/api/orders/{order_id}")
async def delete_order(
    order_id: str,
    user = Depends(require_role("admin"))
):
    """删除订单 - 需要 admin 角色"""
    return {
        "message": f"Order {order_id} deleted by {user.username}"
    }


# 示例 4: 多租户支持
@app.get("/api/inventory")
async def get_inventory(user = Depends(get_current_user)):
    """获取库存 - 自动按租户过滤"""
    # user.tenant_id 会自动包含租户信息
    return {
        "tenant_id": user.tenant_id,
        "inventory": [
            {"item": "A", "quantity": 100},
            {"item": "B", "quantity": 200}
        ]
    }


# 示例 5: 登录端点
@app.get("/auth/login")
async def login():
    """重定向到 Logto 登录页面"""
    from .logto_adapter import LogtoAdapter
    
    adapter = LogtoAdapter(logto_config)
    auth_url = await adapter.get_authorization_url()
    
    return {"auth_url": auth_url}


# 示例 6: 回调端点
@app.get("/auth/callback")
async def auth_callback(code: str, state: str = None):
    """处理 Logto 认证回调"""
    from .logto_adapter import LogtoAdapter
    
    adapter = LogtoAdapter(logto_config)
    
    try:
        # 交换访问令牌
        token = await adapter.exchange_code_for_token(code)
        
        # 获取用户信息
        user = await adapter.get_user_info(token.access_token)
        
        return {
            "message": "Authentication successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": user.roles,
                "permissions": user.permissions,
                "tenant_id": user.tenant_id
            },
            "access_token": token.access_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 示例 7: 用户信息端点
@app.get("/api/me")
async def get_me(user = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "avatar": user.avatar,
        "roles": user.roles,
        "permissions": user.permissions,
        "tenant_id": user.tenant_id
    }


# 示例 8: 登出端点
@app.post("/auth/logout")
async def logout(user = Depends(get_current_user)):
    """登出用户"""
    from .logto_adapter import LogtoAdapter
    
    adapter = LogtoAdapter(logto_config)
    
    # 这里应该撤销用户的访问令牌
    # 实际实现中需要从请求中获取访问令牌
    
    return {"message": f"User {user.username} logged out successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 