"""
Logto 配置管理
"""

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel


@dataclass
class LogtoConfig:
    """Logto 配置"""
    endpoint: str
    app_id: str
    app_secret: str
    redirect_uri: str
    scopes: List[str] = None
    tenant_id: Optional[str] = None
    
    def __post_init__(self):
        """验证配置"""
        if not self.endpoint:
            raise ValueError("Logto endpoint is required")
        if not self.app_id:
            raise ValueError("Logto app_id is required")
        if not self.app_secret:
            raise ValueError("Logto app_secret is required")
        if not self.redirect_uri:
            raise ValueError("Logto redirect_uri is required")
        
        # 设置默认 scopes
        if self.scopes is None:
            self.scopes = ["openid", "profile", "email"]


class LogtoConfigModel(BaseModel):
    """Logto 配置模型（用于配置文件）"""
    endpoint: str
    app_id: str
    app_secret: str
    redirect_uri: str
    scopes: List[str] = ["openid", "profile", "email"]
    tenant_id: Optional[str] = None
    
    def to_config(self) -> LogtoConfig:
        """转换为LogtoConfig对象"""
        return LogtoConfig(
            endpoint=self.endpoint,
            app_id=self.app_id,
            app_secret=self.app_secret,
            redirect_uri=self.redirect_uri,
            scopes=self.scopes,
            tenant_id=self.tenant_id
        ) 