from typing import Dict, List, Set, Tuple, Optional
from enum import Enum, auto

class ContextRelationshipType(Enum):
    """上下文关系类型"""
    PARTNERSHIP = auto()          # 合作关系
    SHARED_KERNEL = auto()        # 共享内核
    CUSTOMER_SUPPLIER = auto()    # 客户-供应商
    CONFORMIST = auto()           # 顺从者
    ANTICORRUPTION_LAYER = auto() # 防腐层
    OPEN_HOST_SERVICE = auto()    # 开放主机服务
    PUBLISHED_LANGUAGE = auto()   # 发布语言
    SEPARATE_WAYS = auto()        # 各行其道

class BoundedContext:
    """有界上下文"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.upstream_relationships: List[ContextRelationship] = []
        self.downstream_relationships: List[ContextRelationship] = []
    
    def add_upstream_relationship(self, relationship: 'ContextRelationship') -> None:
        """添加上游关系"""
        self.upstream_relationships.append(relationship)
    
    def add_downstream_relationship(self, relationship: 'ContextRelationship') -> None:
        """添加下游关系"""
        self.downstream_relationships.append(relationship)

class ContextRelationship:
    """上下文关系"""
    
    def __init__(self, 
                upstream: BoundedContext, 
                downstream: BoundedContext,
                relationship_type: ContextRelationshipType,
                description: str = ""):
        self.upstream = upstream
        self.downstream = downstream
        self.relationship_type = relationship_type
        self.description = description
        
        # 在上下文中注册关系
        upstream.add_downstream_relationship(self)
        downstream.add_upstream_relationship(self)

class ContextMap:
    """上下文映射 - 管理系统中的有界上下文及其关系"""
    
    def __init__(self):
        self.contexts: Dict[str, BoundedContext] = {}
        self.relationships: List[ContextRelationship] = []
    
    def add_context(self, name: str, description: str = "") -> BoundedContext:
        """添加上下文"""
        if name in self.contexts:
            raise ValueError(f"Context '{name}' already exists")
            
        context = BoundedContext(name, description)
        self.contexts[name] = context
        return context
    
    def add_relationship(self, 
                        upstream_name: str, 
                        downstream_name: str, 
                        relationship_type: ContextRelationshipType,
                        description: str = "") -> ContextRelationship:
        """添加上下文关系"""
        if upstream_name not in self.contexts:
            raise ValueError(f"Upstream context '{upstream_name}' not found")
        if downstream_name not in self.contexts:
            raise ValueError(f"Downstream context '{downstream_name}' not found")
            
        upstream = self.contexts[upstream_name]
        downstream = self.contexts[downstream_name]
        
        relationship = ContextRelationship(upstream, downstream, relationship_type, description)
        self.relationships.append(relationship)
        
        return relationship
    
    def get_context(self, name: str) -> Optional[BoundedContext]:
        """获取上下文"""
        return self.contexts.get(name)
    
    def get_all_contexts(self) -> List[BoundedContext]:
        """获取所有上下文"""
        return list(self.contexts.values())
    
    def get_all_relationships(self) -> List[ContextRelationship]:
        """获取所有关系"""
        return self.relationships
