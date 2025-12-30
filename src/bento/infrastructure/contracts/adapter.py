"""Contracts Adapter - Infrastructure Layer Implementation.

This module provides the concrete implementation of the ContractsPort protocol,
adapting the contracts module for use in the application layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bento.domain.ports.contracts import ContractsPort, ReasonCodeInfo

if TYPE_CHECKING:
    from bento.contracts import Contracts


class ContractsAdapter(ContractsPort):
    """Adapter that implements ContractsPort using the contracts module.

    This adapter wraps the Contracts container and provides the interface
    expected by the application layer.

    Example:
        ```python
        from bento.contracts import ContractLoader
        from bento.infrastructure.contracts import ContractsAdapter

        contracts = ContractLoader.load_from_dir("./")
        adapter = ContractsAdapter(contracts)

        # Use in application layer
        adapter.validate_transition("Order", "DRAFT", "Submit")
        ```
    """

    def __init__(self, contracts: "Contracts"):
        """Initialize adapter with contracts container.

        Args:
            contracts: Loaded Contracts instance
        """
        self._contracts = contracts

    def validate_transition(
        self,
        aggregate: str,
        current_state: str,
        command: str,
    ) -> None:
        """Validate that a state transition is allowed.

        Args:
            aggregate: Name of the aggregate
            current_state: Current state of the aggregate
            command: Command being executed

        Raises:
            StateTransitionException: If the transition is not allowed
        """
        self._contracts.state_machines.validate(aggregate, current_state, command)

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
        return self._contracts.state_machines.get_allowed_commands(
            aggregate, current_state
        )

    def get_reason_code(self, code: str) -> ReasonCodeInfo | None:
        """Get reason code information.

        Args:
            code: Reason code identifier

        Returns:
            ReasonCodeInfo if found, None otherwise
        """
        rc = self._contracts.reason_codes.get(code)
        if rc is None:
            return None

        return ReasonCodeInfo(
            code=rc.code,
            http_status=rc.http_status,
            category=rc.category,
            message=rc.message,
            retryable=rc.retryable,
        )

    def get_event_topic(self, event_type: str) -> str:
        """Get the topic for an event type.

        Args:
            event_type: Type of event

        Returns:
            Topic name

        Raises:
            KeyError: If event type is not routed
        """
        return self._contracts.routing.topic_for(event_type)

    @property
    def contracts(self) -> "Contracts":
        """Access the underlying Contracts instance."""
        return self._contracts
