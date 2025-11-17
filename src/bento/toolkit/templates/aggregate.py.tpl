"""{{Name}} 聚合根"""
from dataclasses import dataclass
from bento.domain.aggregate import AggregateRoot
from bento.core.ids import ID

@dataclass
class {{Name}}(AggregateRoot):
    """{{Name}} 聚合根
    
    开发人员只需要：
    1. 定义字段
    2. 实现业务方法
    
    框架自动处理：
    - 事件收集（调用 add_event）
    - 持久化（Repository）
    - 事务管理（UnitOfWork）
    """
{{fields}}
    
    def __post_init__(self):
        super().__init__(id=self.id)
    
    # TODO: 在这里添加业务方法
    # 例如:
    # def deactivate(self):
    #     self.is_active = False
    #     self.add_event({{Name}}DeactivatedEvent({{name_lower}}_id=self.id))
