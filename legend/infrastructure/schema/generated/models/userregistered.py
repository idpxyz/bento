"""

从 user_registered.proto 自动生成的 Pydantic 模型

"""



from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional



class RegistrationType(str, Enum):
    """枚举类型"""
    STANDARD = "standard"  # 标准注册
    SOCIAL = "social"  # 社交媒体注册
    INVITATION = "invitation"  # 邀请注册



class UserRegistered(BaseModel):
    """
    UserRegistered 事件模型
    """
    user_id: Optional[str] = None  # 用户ID
    username: Optional[str] = None  # 用户名
    email: Optional[str] = None  # 邮箱
    registered_at: Optional[datetime] = None  # 注册时间
    registration_type: Optional[RegistrationType] = None  # 注册类型

    model_config = {
        "json_schema_extra": {"description": "UserRegistered 事件模型"},
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }