"""
从 user_activity.json 自动生成的 Pydantic 模型
"""

from datetime import datetime
from ipaddress import IPv4Address
from pydantic import AnyUrl
from pydantic import BaseModel, Field
from typing import Dict, Any
from typing import Dict, List, Any, Optional
from typing import Literal
from typing import Optional


class Resource(BaseModel):
    """
    资源信息
    """
    type: Optional[str] = None  # 资源类型
    id: Optional[str] = None  # 资源ID
    name: Optional[str] = None  # 资源名称
    url: AnyUrl = None  # 资源URL

    class Config:
        """模型配置"""
        json_schema_extra = {
            'description': '资源信息'
        }

class Device(BaseModel):
    """
    设备信息
    """
    type: Optional[str] = None  # 设备类型
    os: Optional[str] = None  # 操作系统
    browser: Optional[str] = None  # 浏览器
    ip: IPv4Address = None  # IP地址

    class Config:
        """模型配置"""
        json_schema_extra = {
            'description': '设备信息'
        }

class UserActivity(BaseModel):
    """
    用户活动事件
    """
    activity_id: str  # 活动ID
    user_id: str  # 用户ID
    session_id: Optional[str] = None  # 会话ID
    action: Literal['login', 'logout', 'view', 'click', 'search', 'purchase']  # 活动类型
    resource: Resource = None  # 资源信息
    device: Device = None  # 设备信息
    timestamp: datetime  # 时间戳
    metadata: Dict[str, Any] = None  # 附加元数据

    class Config:
        """模型配置"""
        json_schema_extra = {
            'description': '附加元数据'
        }
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
