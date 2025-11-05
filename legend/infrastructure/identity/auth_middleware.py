"""
认证中间件 - 用于 FastAPI 应用
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import LogtoConfig
from .logto_adapter import LogtoAdapter, LogtoUser

# 全局 Logto 适配器实例
_logto_adapter: Optional[LogtoAdapter] = None


def init_logto_adapter(config: LogtoConfig):
    """初始化 Logto 适配器"""
    global _logto_adapter
    _logto_adapter = LogtoAdapter(config)


def get_logto_adapter() -> LogtoAdapter:
    """获取 Logto 适配器实例"""
    if _logto_adapter is None:
        raise RuntimeError("Logto adapter not initialized. Call init_logto_adapter() first.")
    return _logto_adapter


class AuthMiddleware:
    """
    认证中间件 - 用于 FastAPI 应用
    
    遵循开闭原则：可扩展的中间件设计
    """
    
    def __init__(self, logto_adapter: LogtoAdapter):
        self.logto_adapter = logto_adapter
        self.security = HTTPBearer()
    
    async def authenticate_request(self, request: Request) -> Optional[LogtoUser]:
        """认证请求"""
        try:
            # 获取 Authorization 头
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            access_token = auth_header[7:]  # 移除 "Bearer " 前缀
            
            # 验证令牌
            if not await self.logto_adapter.validate_token(access_token):
                return None
            
            # 获取用户信息
            return await self.logto_adapter.get_user_info(access_token)
        except Exception:
            return None
    
    async def require_authentication(self, request: Request) -> LogtoUser:
        """要求认证"""
        user = await self.authenticate_request(request)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        return user
    
    async def require_permission(
        self, 
        request: Request, 
        permission: str
    ) -> LogtoUser:
        """要求特定权限"""
        user = await self.require_authentication(request)
        
        if permission not in (user.permissions or []):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required"
            )
        
        return user
    
    async def require_role(
        self, 
        request: Request, 
        role: str
    ) -> LogtoUser:
        """要求特定角色"""
        user = await self.require_authentication(request)
        
        if role not in (user.roles or []):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' required"
            )
        
        return user


# 依赖注入函数
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> LogtoUser:
    """获取当前用户 - 用于依赖注入"""
    logto_adapter = get_logto_adapter()
    
    # 验证令牌
    if not await logto_adapter.validate_token(credentials.credentials):
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    
    # 获取用户信息
    return await logto_adapter.get_user_info(credentials.credentials)


async def require_permission(permission: str):
    """要求特定权限的依赖函数"""
    async def _require_permission(
        user: LogtoUser = Depends(get_current_user)
    ) -> LogtoUser:
        if permission not in (user.permissions or []):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required"
            )
        return user
    
    return _require_permission


async def require_role(role: str):
    """要求特定角色的依赖函数"""
    async def _require_role(
        user: LogtoUser = Depends(get_current_user)
    ) -> LogtoUser:
        if role not in (user.roles or []):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' required"
            )
        return user
    
    return _require_role


# 便捷的认证检查函数
async def is_authenticated(request: Request) -> bool:
    """检查是否已认证"""
    logto_adapter = get_logto_adapter()
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    
    access_token = auth_header[7:]
    return await logto_adapter.validate_token(access_token)


async def get_user_permissions(request: Request) -> list:
    """获取用户权限"""
    user = await get_current_user_from_request(request)
    return user.permissions if user else []


async def get_current_user_from_request(request: Request) -> Optional[LogtoUser]:
    """从请求中获取当前用户"""
    logto_adapter = get_logto_adapter()
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    access_token = auth_header[7:]
    
    if not await logto_adapter.validate_token(access_token):
        return None
    
    return await logto_adapter.get_user_info(access_token) 