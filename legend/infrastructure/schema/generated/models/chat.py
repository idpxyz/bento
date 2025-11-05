"""

从 chat.proto 自动生成的 Pydantic 模型

"""



from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional



class Chat(BaseModel):
    """
    Chat 事件模型
    """
    id: Optional[str] = None  # 唯一ID
    data: Optional[str] = None  # 示例数据字段
    created_at: Optional[datetime] = None  # 创建时间

    model_config = {
        "json_schema_extra": {"description": "Chat 事件模型"},
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }