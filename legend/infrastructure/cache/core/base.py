from abc import ABC, abstractmethod
from typing import Any, Optional, Union
from datetime import timedelta

class ICache(ABC):
    """缓存接口"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化缓存"""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> None:
        """设置缓存值"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存值"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空缓存"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭缓存连接"""
        pass 

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> None:
        """删除符合模式的缓存"""
        pass

