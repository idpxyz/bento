from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Optional

@dataclass(frozen=True)
class ReasonCodeSpec:
    reason_code: str
    retryable: bool
    category: str
    http_status: int
    retry_after_hint_seconds: Optional[int] = None

class ReasonCodes:
    def __init__(self, mapping: dict[str, ReasonCodeSpec]):
        self._mapping = mapping

    @classmethod
    def load_from_file(cls, path: Path) -> "ReasonCodes":
        data = json.loads(path.read_text(encoding="utf-8"))
        reason_codes_list = data.get("reason_codes", data) if isinstance(data, dict) else data
        mapping: dict[str, ReasonCodeSpec] = {}
        for row in reason_codes_list:
            mapping[row["reason_code"]] = ReasonCodeSpec(
                reason_code=row["reason_code"],
                retryable=bool(row["retryable"]),
                category=row["category"],
                http_status=int(row["http_status"]),
                retry_after_hint_seconds=row.get("retry_after_hint_seconds"),
            )
        return cls(mapping)

    def contains(self, code: str) -> bool:
        return code in self._mapping

    def get(self, code: str) -> ReasonCodeSpec:
        return self._mapping[code]

    @property
    def whitelist(self) -> set[str]:
        return set(self._mapping.keys())
