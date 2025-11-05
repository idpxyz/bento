"""
Logto 适配器 - 与 Logto 服务交互
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import jwt

from .config import LogtoConfig


@dataclass
class LogtoUser:
    """Logto 用户信息"""
    id: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    tenant_id: Optional[str] = None


@dataclass
class LogtoToken:
    """Logto 令牌信息"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class LogtoAdapter:
    """
    Logto 适配器 - 与 Logto 服务交互
    
    遵循单一职责原则：专注于与 Logto 的通信
    """
    
    def __init__(self, config: LogtoConfig):
        self.config = config
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_authorization_url(
        self, 
        state: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """获取授权 URL"""
        params = {
            "client_id": self.config.app_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes)
        }
        
        if state:
            params["state"] = state
        if prompt:
            params["prompt"] = prompt
        
        return f"{self.config.endpoint}/oidc/auth?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> LogtoToken:
        """使用授权码交换访问令牌"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.app_id,
            "client_secret": self.config.app_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri
        }
        
        response = await self._http_client.post(
            f"{self.config.endpoint}/oidc/token",
            data=data
        )
        response.raise_for_status()
        
        token_data = response.json()
        return LogtoToken(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data["expires_in"]
        )
    
    async def refresh_access_token(self, refresh_token: str) -> LogtoToken:
        """刷新访问令牌"""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.app_id,
            "client_secret": self.config.app_secret,
            "refresh_token": refresh_token
        }
        
        response = await self._http_client.post(
            f"{self.config.endpoint}/oidc/token",
            data=data
        )
        response.raise_for_status()
        
        token_data = response.json()
        return LogtoToken(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data["expires_in"]
        )
    
    async def get_user_info(self, access_token: str) -> LogtoUser:
        """获取用户信息"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await self._http_client.get(
            f"{self.config.endpoint}/oidc/me",
            headers=headers
        )
        response.raise_for_status()
        
        user_data = response.json()
        return LogtoUser(
            id=user_data["sub"],
            username=user_data.get("username"),
            email=user_data.get("email"),
            name=user_data.get("name"),
            avatar=user_data.get("picture"),
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", []),
            tenant_id=user_data.get("tenant_id")
        )
    
    async def validate_token(self, access_token: str) -> bool:
        """验证访问令牌"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await self._http_client.get(
                f"{self.config.endpoint}/oidc/me",
                headers=headers
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def revoke_token(self, token: str, token_type: str = "access_token") -> bool:
        """撤销令牌"""
        try:
            data = {
                "client_id": self.config.app_id,
                "client_secret": self.config.app_secret,
                "token": token,
                "token_type_hint": token_type
            }
            
            response = await self._http_client.post(
                f"{self.config.endpoint}/oidc/revoke",
                data=data
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_organization_scope(self, access_token: str) -> List[str]:
        """获取组织范围（多租户）"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = await self._http_client.get(
                f"{self.config.endpoint}/oidc/me/organizations",
                headers=headers
            )
            response.raise_for_status()
            
            org_data = response.json()
            return [org["id"] for org in org_data.get("organizations", [])]
        except Exception:
            return []
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self._http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 