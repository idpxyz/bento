"""Contract Catalogs - Contracts-as-Code.

Provides catalogs for reason codes and event routing loaded from contract files.

Reason Code Format (JSON):
    ```json
    {
      "version": "1.0.0",
      "reason_codes": [
        {
          "reason_code": "VALIDATION_FAILED",
          "http_status": 400,
          "category": "VALIDATION",
          "retryable": false,
          "message": "Validation failed"
        }
      ]
    }
    ```

Routing Matrix Format (YAML):
    ```yaml
    version: "1.0.0"
    routes:
      - event_type: OrderCreated
        topic: order.events
        consumers:
          - group: notification-service
            action: send_confirmation
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReasonCode:
    """A single reason code entry.

    Attributes:
        code: Unique reason code identifier
        http_status: Suggested HTTP status code
        category: Category (VALIDATION, DOMAIN, CLIENT, etc.)
        retryable: Whether the operation can be retried
        message: Human-readable message
    """

    code: str
    http_status: int
    category: str = "UNKNOWN"
    retryable: bool = False
    message: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReasonCode:
        """Create ReasonCode from dictionary."""
        return cls(
            code=data["reason_code"],
            http_status=data.get("http_status", 500),
            category=data.get("category", "UNKNOWN"),
            retryable=data.get("retryable", False),
            message=data.get("message", ""),
        )


class ReasonCodeCatalog:
    """Catalog of reason codes loaded from JSON contract.

    Provides lookup for error/reason codes with their metadata.

    Example:
        ```python
        catalog = ReasonCodeCatalog(json_doc)

        code = catalog.get("VALIDATION_FAILED")
        if code:
            print(f"HTTP {code.http_status}: {code.message}")
        ```
    """

    def __init__(self, doc: dict[str, Any]):
        """Initialize catalog from JSON document.

        Args:
            doc: Parsed JSON document with reason_codes array
        """
        self._items: dict[str, ReasonCode] = {}
        self._raw: dict[str, dict[str, Any]] = {}
        for item in doc.get("reason_codes", []):
            code = ReasonCode.from_dict(item)
            self._items[code.code] = code
            self._raw[code.code] = item

    def get(self, reason_code: str) -> ReasonCode | None:
        """Get reason code by identifier.

        Args:
            reason_code: The reason code to look up

        Returns:
            ReasonCode if found, None otherwise
        """
        return self._items.get(reason_code)

    def get_raw(self, reason_code: str) -> dict[str, Any] | None:
        """Get raw reason code dict by identifier.

        Args:
            reason_code: The reason code to look up

        Returns:
            Raw dict if found, None otherwise
        """
        return self._raw.get(reason_code)

    def all(self) -> list[ReasonCode]:
        """Get all reason codes.

        Returns:
            List of all ReasonCode entries
        """
        return list(self._items.values())

    def by_category(self, category: str) -> list[ReasonCode]:
        """Get reason codes by category.

        Args:
            category: Category to filter by

        Returns:
            List of ReasonCode entries in the category
        """
        return [c for c in self._items.values() if c.category == category]

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, reason_code: str) -> bool:
        return reason_code in self._items


@dataclass(frozen=True)
class Route:
    """A single event routing entry.

    Attributes:
        event_type: Type of event
        topic: Target message topic
        produced_by: Service that produces this event
        consumers: List of consumer configurations
    """

    event_type: str
    topic: str
    produced_by: str = ""
    consumers: list[dict[str, Any]] = field(default_factory=list)


class RoutingMatrix:
    """Event routing matrix loaded from YAML contract.

    Maps event types to message topics and consumer configurations.

    Example:
        ```python
        matrix = RoutingMatrix(yaml_doc)

        topic = matrix.topic_for("OrderCreated")
        print(f"Route to: {topic}")
        ```
    """

    def __init__(self, doc: dict[str, Any]):
        """Initialize routing matrix from YAML document.

        Args:
            doc: Parsed YAML document with routes array
        """
        self._routes: list[Route] = []
        self._by_event: dict[str, Route] = {}

        for r in doc.get("routes", []):
            route = Route(
                event_type=r.get("event_type", ""),
                topic=r.get("topic", ""),
                produced_by=r.get("produced_by", ""),
                consumers=r.get("consumers", []),
            )
            self._routes.append(route)
            self._by_event[route.event_type] = route

    def topic_for(self, event_type: str) -> str:
        """Get topic for an event type.

        Args:
            event_type: Type of event to route

        Returns:
            Topic name

        Raises:
            KeyError: If event type is not routed
        """
        route = self._by_event.get(event_type)
        if not route:
            raise KeyError(f"event_type not routed: {event_type}")
        return route.topic

    def get_route(self, event_type: str) -> Route | None:
        """Get full route configuration for an event type.

        Args:
            event_type: Type of event

        Returns:
            Route if found, None otherwise
        """
        return self._by_event.get(event_type)

    def all_routes(self) -> list[Route]:
        """Get all routes.

        Returns:
            List of all Route entries
        """
        return list(self._routes)

    def __len__(self) -> int:
        return len(self._routes)

    def __contains__(self, event_type: str) -> bool:
        return event_type in self._by_event
