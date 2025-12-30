from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class CompatibilityLevel(str, Enum):
    COMPATIBLE = "compatible"
    WARNING = "warning"
    BREAKING = "breaking"


@dataclass(frozen=True, slots=True)
class CompatibilityRule:
    from_version: str
    to_version: str
    level: CompatibilityLevel
    notes: str = ""


class CompatibilityMatrix:
    """Keeps track of version-to-version compatibility decisions."""

    def __init__(self, rules: Iterable[CompatibilityRule] | None = None) -> None:
        self._rules: dict[tuple[str, str], CompatibilityRule] = {}
        if rules:
            for rule in rules:
                self.register(rule)

    def register(self, rule: CompatibilityRule) -> None:
        key = (rule.from_version, rule.to_version)
        if key in self._rules:
            raise ValueError(f"Compatibility rule {key} already registered")
        self._rules[key] = rule

    def update(self, rule: CompatibilityRule) -> None:
        self._rules[(rule.from_version, rule.to_version)] = rule

    def evaluate(self, from_version: str, to_version: str) -> CompatibilityRule:
        key = (from_version, to_version)
        if key not in self._rules:
            return CompatibilityRule(from_version, to_version, CompatibilityLevel.WARNING, notes="No rule defined")
        return self._rules[key]

    def compatible(self, from_version: str, to_version: str) -> bool:
        return self.evaluate(from_version, to_version).level is CompatibilityLevel.COMPATIBLE

    def breaking(self, from_version: str, to_version: str) -> bool:
        return self.evaluate(from_version, to_version).level is CompatibilityLevel.BREAKING

    def as_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "rules": [
                {
                    "from": rule.from_version,
                    "to": rule.to_version,
                    "level": rule.level.value,
                    "notes": rule.notes,
                }
                for rule in self._rules.values()
            ]
        }
