from dataclasses import dataclass

from bento.core.ids import EntityId


@dataclass
class Entity:
    id: EntityId
