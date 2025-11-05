"""
Identity Infrastructure Module

基于 Logto 的中心身份基座集成，提供简化的认证、授权和多租户功能。
"""

from .auth_middleware import AuthMiddleware, get_current_user
from .config import LogtoConfig
from .logto_adapter import LogtoAdapter

__all__ = [
    "LogtoAdapter",
    "AuthMiddleware", 
    "get_current_user",
    "LogtoConfig"
] 