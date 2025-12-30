"""
Contract Catalogs - Contracts-as-Code.

Provides catalogs for reason codes and event routing.
"""


class ReasonCodeCatalog:
    """Catalog of reason codes loaded from JSON contract."""

    def __init__(self, doc: dict):
        self._items = {x["reason_code"]: x for x in doc.get("reason_codes", [])}

    def get(self, reason_code: str) -> dict | None:
        return self._items.get(reason_code)

    def all(self) -> list[dict]:
        return list(self._items.values())


class RoutingMatrix:
    """Event routing matrix loaded from YAML contract."""

    def __init__(self, doc: dict):
        self._routes = doc.get("routes", [])

    def topic_for(self, event_type: str) -> str:
        for r in self._routes:
            if r.get("event_type") == event_type:
                return r["topic"]
        raise KeyError(f"event_type not routed: {event_type}")
