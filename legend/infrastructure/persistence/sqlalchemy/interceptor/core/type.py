"""SQLAlchemy拦截器类型定义

定义拦截器系统使用的上下文类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, ForwardRef, Generic, List, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from .common import OperationType

T = TypeVar('T')

@dataclass
class InterceptorContext(Generic[T]):
    """拦截器执行上下文
    
    包含拦截器执行时需要的所有上下文信息。
    
    Attributes:
        session: 数据库会话
        entity_type: 实体类型
        operation: 操作类型
        entity: 当前操作的实体（可选）
        entities: 批量操作的实体列表（可选）
        actor: 当前操作者（可选）
        config: 拦截器配置（可选）
        context_data: 额外的上下文数据
    """
    session: AsyncSession
    entity_type: Type[T]
    operation: OperationType
    entity: Optional[T] = None
    entities: Optional[List[T]] = None
    actor: Optional[str] = None
    config: Optional[Any] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    def is_batch_operation(self) -> bool:
        """检查是否为批量操作"""
        return self.operation in (
            OperationType.BATCH_CREATE,
            OperationType.BATCH_UPDATE,
            OperationType.BATCH_DELETE
        )
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """获取上下文数据值"""
        return self.context_data.get(key, default)
    
    def set_context_value(self, key: str, value: Any) -> None:
        """设置上下文数据值"""
        self.context_data[key] = value
