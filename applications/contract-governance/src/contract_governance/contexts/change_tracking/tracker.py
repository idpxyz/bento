from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ChangeRecord:
    change_id: str
    contract_id: str
    from_version: str
    to_version: str
    change_type: str
    author: str
    summary: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChangeHistory:
    contract_id: str
    records: list[ChangeRecord] = field(default_factory=list)

    def append(self, record: ChangeRecord) -> None:
        if record.contract_id != self.contract_id:
            raise ValueError("Contract mismatch for change record")
        self.records.append(record)

    def extend(self, records: Iterable[ChangeRecord]) -> None:
        for record in records:
            self.append(record)

    def latest(self) -> ChangeRecord | None:
        return max(self.records, key=lambda r: r.created_at, default=None)

    def between(self, from_version: str, to_version: str) -> list[ChangeRecord]:
        return [
            record
            for record in self.records
            if record.from_version >= from_version and record.to_version <= to_version
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "changes": [
                {
                    "change_id": record.change_id,
                    "from_version": record.from_version,
                    "to_version": record.to_version,
                    "change_type": record.change_type,
                    "summary": record.summary,
                    "author": record.author,
                    "created_at": record.created_at.isoformat(),
                }
                for record in self.records
            ],
        }
