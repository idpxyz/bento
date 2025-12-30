from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Any


@dataclass(frozen=True, slots=True)
class DependencyLink:
    source_service: str
    target_service: str
    contract_id: str
    version: str
    dependency_type: str = "consumer"


@dataclass
class DependencyGraph:
    contract_id: str
    links: set[DependencyLink] = field(default_factory=set)

    def add_link(self, link: DependencyLink) -> None:
        if link.contract_id != self.contract_id:
            raise ValueError("Contract mismatch for dependency link")
        self.links.add(link)

    def add_links(self, links: Iterable[DependencyLink]) -> None:
        for link in links:
            self.add_link(link)

    def remove_link(self, link: DependencyLink) -> None:
        self.links.discard(link)

    def dependencies_of(self, service: str) -> list[DependencyLink]:
        return [link for link in self.links if link.source_service == service]

    def dependents_of(self, service: str) -> list[DependencyLink]:
        return [link for link in self.links if link.target_service == service]

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "links": [
                {
                    "source": link.source_service,
                    "target": link.target_service,
                    "version": link.version,
                    "dependency_type": link.dependency_type,
                }
                for link in sorted(self.links, key=lambda l: (l.source_service, l.target_service))
            ],
        }
