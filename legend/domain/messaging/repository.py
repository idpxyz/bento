from abc import ABC, abstractmethod
from typing import Optional

from .aggregate import MessageAggregate
from .vo import MessageId


class MessageRepository(ABC):
    """消息仓储接口"""
    
    @abstractmethod
    async def save(self, aggregate: MessageAggregate) -> None:
        """保存消息聚合根"""
        pass
    
    @abstractmethod
    async def find_by_id(self, id: MessageId) -> Optional[MessageAggregate]:
        """根据ID查找消息聚合根"""
        pass
    
    @abstractmethod
    async def delete(self, id: MessageId) -> None:
        """删除消息聚合根"""
        pass 