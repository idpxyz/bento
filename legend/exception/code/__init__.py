"""错误码包

此包定义了所有IDP错误码，按DDD分层组织:
1. domain - 领域层错误码
2. application - 应用层错误码 
3. infrastructure - 基础设施层错误码

每个模块中的错误码都使用ErrorCode数据类定义，包含:
- code: 错误码
- message: 错误消息
- http_status: HTTP状态码
"""

from .database import DatabaseErrorCode


__all__ = [
    'DatabaseErrorCode'
] 