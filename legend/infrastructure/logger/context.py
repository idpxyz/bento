"""
日志上下文模块

定义日志上下文相关的类和工具函数，提供结构化的上下文信息用于日志记录。
"""
import uuid
from typing import Any, Dict, Optional


class LogContext:
    """
    日志上下文类
    
    用于记录和传递日志的上下文信息，如服务名、组件、操作等。
    """
    
    def __init__(self, 
                 service: Optional[str] = None,
                 component: Optional[str] = None,
                 action: Optional[str] = None,
                 trace_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 error_id: Optional[str] = None,
                 **kwargs):
        """
        初始化日志上下文
        
        Args:
            service: 服务名称
            component: 组件名称
            action: 操作名称
            trace_id: 跟踪ID，用于跟踪请求
            session_id: 会话ID
            user_id: 用户ID
            error_id: 错误ID
            **kwargs: 其他上下文属性
        """
        self.service = service
        self.component = component
        self.action = action
        self.trace_id = trace_id or str(uuid.uuid4())
        self.session_id = session_id
        self.user_id = user_id
        self.error_id = error_id
        self.extra = kwargs
        
    def as_dict(self) -> Dict[str, Any]:
        """
        将上下文转换为字典
        
        Returns:
            包含所有上下文信息的字典
        """
        result = {
            "context": {
                key: value
                for key, value in {
                    "service": self.service,
                    "component": self.component,
                    "action": self.action,
                    "trace_id": self.trace_id,
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "error_id": self.error_id,
                }.items()
                if value is not None
            }
        }
        
        # 添加额外属性
        if self.extra:
            result["context"].update(self.extra)
            
        return result
    
    def update(self, **kwargs) -> 'LogContext':
        """
        更新上下文信息
        
        Args:
            **kwargs: 要更新的属性
            
        Returns:
            更新后的上下文对象
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra[key] = value
                
        return self
    
    def clone(self) -> 'LogContext':
        """
        创建上下文的副本
        
        Returns:
            上下文的副本
        """
        new_context = LogContext(
            service=self.service,
            component=self.component,
            action=self.action,
            trace_id=self.trace_id,
            session_id=self.session_id,
            user_id=self.user_id,
            error_id=self.error_id,
            **self.extra
        )
        return new_context


def create_context(**kwargs) -> LogContext:
    """
    创建日志上下文的便捷函数
    
    Args:
        **kwargs: 上下文属性
        
    Returns:
        新创建的日志上下文
    """
    return LogContext(**kwargs) 