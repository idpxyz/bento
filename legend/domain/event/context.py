"""领域事件上下文模块。

提供领域事件的上下文管理功能，用于跟踪事件之间的因果关系。
"""

from contextvars import ContextVar
from typing import Dict, Any, Optional
from uuid import uuid4

# 上下文变量
current_correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')
current_causation_id: ContextVar[str] = ContextVar('causation_id', default='')
current_user_id: ContextVar[str] = ContextVar('user_id', default='')
current_tenant_id: ContextVar[str] = ContextVar('tenant_id', default='')

def get_correlation_id() -> str:
    """获取当前关联ID
    
    Returns:
        当前关联ID，如果未设置则返回空字符串
    """
    return current_correlation_id.get()

def set_correlation_id(correlation_id: str) -> None:
    """设置当前关联ID
    
    Args:
        correlation_id: 关联ID
    """
    current_correlation_id.set(correlation_id)

def get_causation_id() -> str:
    """获取当前因果ID
    
    Returns:
        当前因果ID，如果未设置则返回空字符串
    """
    return current_causation_id.get()

def set_causation_id(causation_id: str) -> None:
    """设置当前因果ID
    
    Args:
        causation_id: 因果ID
    """
    current_causation_id.set(causation_id)

def get_user_id() -> str:
    """获取当前用户ID
    
    Returns:
        当前用户ID，如果未设置则返回空字符串
    """
    return current_user_id.get()

def set_user_id(user_id: str) -> None:
    """设置当前用户ID
    
    Args:
        user_id: 用户ID
    """
    current_user_id.set(user_id)

def get_tenant_id() -> str:
    """获取当前租户ID
    
    Returns:
        当前租户ID，如果未设置则返回空字符串
    """
    return current_tenant_id.get()

def set_tenant_id(tenant_id: str) -> None:
    """设置当前租户ID
    
    Args:
        tenant_id: 租户ID
    """
    current_tenant_id.set(tenant_id)

def get_event_context() -> Dict[str, Any]:
    """获取当前事件上下文
    
    Returns:
        包含所有上下文变量的字典
    """
    return {
        'correlation_id': get_correlation_id(),
        'causation_id': get_causation_id(),
        'user_id': get_user_id(),
        'tenant_id': get_tenant_id()
    }

def generate_id() -> str:
    """生成唯一ID
    
    Returns:
        生成的唯一ID
    """
    return str(uuid4())

class EventContext:
    """事件上下文管理器
    
    用于在执行代码块期间设置事件上下文，并在退出时恢复原始值
    """
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """初始化事件上下文
        
        Args:
            correlation_id: 关联ID，如果为None则生成新ID
            causation_id: 因果ID
            user_id: 用户ID
            tenant_id: 租户ID
        """
        self.correlation_id = correlation_id or generate_id()
        self.causation_id = causation_id
        self.user_id = user_id
        self.tenant_id = tenant_id
        
        # 保存原始值的令牌
        self.correlation_id_token = None
        self.causation_id_token = None
        self.user_id_token = None
        self.tenant_id_token = None
    
    def __enter__(self):
        """进入上下文
        
        Returns:
            上下文管理器实例
        """
        # 保存原始值并设置新值
        self.correlation_id_token = current_correlation_id.set(self.correlation_id)
        
        if self.causation_id:
            self.causation_id_token = current_causation_id.set(self.causation_id)
        
        if self.user_id:
            self.user_id_token = current_user_id.set(self.user_id)
        
        if self.tenant_id:
            self.tenant_id_token = current_tenant_id.set(self.tenant_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常回溯
        """
        # 恢复原始值
        if self.correlation_id_token:
            current_correlation_id.reset(self.correlation_id_token)
        
        if self.causation_id_token:
            current_causation_id.reset(self.causation_id_token)
        
        if self.user_id_token:
            current_user_id.reset(self.user_id_token)
        
        if self.tenant_id_token:
            current_tenant_id.reset(self.tenant_id_token) 