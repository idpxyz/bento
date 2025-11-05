from typing import Dict, Optional

from idp.framework.domain.messaging.aggregate import MessageAggregate
from idp.framework.domain.messaging.repository import MessageRepository
from idp.framework.domain.messaging.vo import MessageId


class InMemoryMessageRepository(MessageRepository):
    """内存消息仓储实现"""
    
    def __init__(self):
        self._storage: Dict[str, MessageAggregate] = {}
    
    async def save(self, aggregate: MessageAggregate) -> None:
        """保存消息聚合根"""
        self._storage[aggregate.id.value] = aggregate
    
    async def find_by_id(self, id: MessageId) -> Optional[MessageAggregate]:
        """根据ID查找消息聚合根"""
        return self._storage.get(id.value)
    
    async def delete(self, id: MessageId) -> None:
        """删除消息聚合根"""
        if id.value in self._storage:
            del self._storage[id.value] 