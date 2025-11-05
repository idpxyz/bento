"""映射上下文模块。

提供映射过程中的上下文管理，用于处理循环引用和共享状态。

Key Components:
- MappingContext: 映射上下文，用于跟踪已映射对象和处理循环引用
"""

from typing import Any, Dict, Optional, TypeVar, Generic, Set

# 类型变量
S = TypeVar('S')  # 源类型
T = TypeVar('T')  # 目标类型


class MappingContext:
    """映射上下文
    
    用于在映射过程中跟踪已映射对象，防止循环引用导致的无限递归。
    同时提供共享状态管理，用于在映射过程中传递信息。
    """
    
    def __init__(self):
        """初始化映射上下文"""
        # 使用对象ID作为键，映射后的对象作为值，跟踪已映射对象
        self._mapped_objects: Dict[int, Any] = {}
        # 共享状态，用于在映射过程中传递信息
        self._state: Dict[str, Any] = {}
        # 跟踪当前映射路径，用于检测循环引用
        self._current_path: Set[int] = set()
    
    def has_mapped_object(self, source: Any) -> bool:
        """检查源对象是否已被映射
        
        Args:
            source: 源对象
            
        Returns:
            bool: 如果源对象已被映射，则返回True，否则返回False
        """
        if source is None:
            return False
        return id(source) in self._mapped_objects
    
    def get_mapped_object(self, source: Any) -> Any:
        """获取源对象对应的已映射对象
        
        Args:
            source: 源对象
            
        Returns:
            Any: 已映射的对象，如果源对象未被映射，则返回None
        """
        if source is None:
            return None
        return self._mapped_objects.get(id(source))
    
    def register_mapped_object(self, source: Any, target: Any) -> None:
        """注册已映射的对象
        
        Args:
            source: 源对象
            target: 映射后的目标对象
        """
        if source is not None:
            self._mapped_objects[id(source)] = target
    
    def set_state(self, key: str, value: Any) -> None:
        """设置共享状态
        
        Args:
            key: 状态键
            value: 状态值
        """
        self._state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取共享状态
        
        Args:
            key: 状态键
            default: 默认值，如果状态不存在，则返回此值
            
        Returns:
            Any: 状态值，如果状态不存在，则返回默认值
        """
        return self._state.get(key, default)
    
    def enter_mapping(self, source: Any) -> bool:
        """进入对象映射
        
        记录当前正在映射的对象，用于检测循环引用。
        
        Args:
            source: 源对象
            
        Returns:
            bool: 如果没有检测到循环引用，则返回True，否则返回False
        """
        if source is None:
            return True
        
        source_id = id(source)
        # 如果对象已在当前映射路径中，则检测到循环引用
        if source_id in self._current_path:
            return False
        
        # 将对象添加到当前映射路径
        self._current_path.add(source_id)
        return True
    
    def exit_mapping(self, source: Any) -> None:
        """退出对象映射
        
        从当前映射路径中移除对象。
        
        Args:
            source: 源对象
        """
        if source is not None:
            self._current_path.discard(id(source)) 