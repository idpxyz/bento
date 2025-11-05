from dataclasses import dataclass
from core.ids import EntityId
from domain.entity import Entity

@dataclass
class {{Name}}(Entity):
    name: str
