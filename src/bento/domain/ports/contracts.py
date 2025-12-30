"""Contracts Port - Domain Layer Interface.

This module defines the contracts port that the domain layer depends on
for state machine validation and reason code lookups.

This follows the hexagonal architecture pattern where the domain layer
defines the port (interface) and the infrastructure layer provides the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class ReasonCodeInfo:
    """Reason code information from contracts.

    Attributes:
        code: Unique reason code identifier
        http_status: Suggested HTTP status code
        category: Category (DOMAIN, VALIDATION, etc.)
        message: Human-readable message
        retryable: Whether the operation can be retried
    """

    code: str
    http_status: int
    category: str
    message: str
    retryable: bool = False


class ContractsPort(Protocol):
    """Port for contracts access from domain/application layer.

    This protocol defines the interface that the application layer uses
    to interact with contracts. The infrastructure layer provides the
    concrete implementation.

    Example:
        ```python
        class SubmitOrderHandler(CommandHandler):
            def __init__(self, uow: UnitOfWork):
                self.uow = uow

            async def handle(self, command):
                # Validate state transition
                self.uow.contracts.validate_transition(
                    "Order", order.status, "Submit"
                )
        ```
    """

    def validate_transition(
        self,
        aggregate: str,
        current_state: str,
        command: str,
    ) -> None:
        """Validate that a state transition is allowed.

        Args:
            aggregate: Name of the aggregate (e.g., "Order")
            current_state: Current state of the aggregate
            command: Command being executed

        Raises:
            StateTransitionException: If the transition is not allowed
        """
        ...

    def get_allowed_commands(
        self,
        aggregate: str,
        current_state: str,
    ) -> list[str]:
        """Get commands allowed from the current state.

        Args:
            aggregate: Name of the aggregate
            current_state: Current state

        Returns:
            List of allowed command names
        """
        ...

    def get_reason_code(self, code: str) -> ReasonCodeInfo | None:
        """Get reason code information.

        Args:
            code: Reason code identifier

        Returns:
            ReasonCodeInfo if found, None otherwise
        """
        ...

    def get_event_topic(self, event_type: str) -> str:
        """Get the topic for an event type.

        Args:
            event_type: Type of event

        Returns:
            Topic name

        Raises:
            KeyError: If event type is not routed
        """
        ...
