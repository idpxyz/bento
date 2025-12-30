"""State Machine Engine - Contracts-as-Code.

Validates aggregate state transitions based on YAML-defined state machines.
This enables declarative state machine definitions that can be version-controlled
and validated at startup.

YAML Contract Format:
    ```yaml
    version: "1.0.0"
    aggregate: Order
    states:
      - DRAFT
      - SUBMITTED
      - COMPLETED
      - CANCELLED

    transitions:
      - from: DRAFT
        command: Submit
        to: SUBMITTED
      - from: [DRAFT, SUBMITTED]  # Multiple source states
        command: Cancel
        to: CANCELLED
      - from: null  # Wildcard - any state
        command: Audit
        to: null  # No state change
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bento.core.exceptions import DomainException


class StateMachineEngine:
    """Validates state transitions for aggregates based on YAML definitions.

    This engine loads state machine definitions from YAML files and provides
    runtime validation of state transitions. Invalid transitions raise
    StateTransitionException.

    Example:
        ```python
        engine = StateMachineEngine({
            "Order": order_sm_yaml,
            "Shipment": shipment_sm_yaml,
        })

        # Validate transition (raises if invalid)
        engine.validate("Order", "DRAFT", "Submit")
        ```

    Args:
        machines: Dict mapping aggregate names to their state machine definitions
    """

    def __init__(self, machines: dict[str, dict[str, Any]]):
        self._machines = machines

    def validate(self, aggregate: str, current_state: str, command: str) -> None:
        """Validate that a command is allowed from the current state.

        Args:
            aggregate: Name of the aggregate (e.g., "Order", "Shipment")
            current_state: Current state of the aggregate
            command: Command being executed

        Raises:
            StateTransitionException: If the transition is not allowed
        """
        sm = self._machines.get(aggregate) or {}
        transitions = sm.get("transitions", [])

        for t in transitions:
            frm = t.get("from")
            cmd = t.get("command")

            if cmd != command:
                continue

            # Wildcard - allowed from any state
            if frm is None:
                return

            # Multiple source states
            if isinstance(frm, list) and current_state in frm:
                return

            # Single source state
            if isinstance(frm, str) and current_state == frm:
                return

        raise StateTransitionException(
            reason_code="STATE_TRANSITION_INVALID",
            aggregate=aggregate,
            current_state=current_state,
            command=command,
        )

    def get_allowed_commands(self, aggregate: str, current_state: str) -> list[str]:
        """Get list of commands allowed from the current state.

        Args:
            aggregate: Name of the aggregate
            current_state: Current state of the aggregate

        Returns:
            List of allowed command names
        """
        sm = self._machines.get(aggregate) or {}
        transitions = sm.get("transitions", [])
        allowed = []

        for t in transitions:
            frm = t.get("from")
            cmd = t.get("command")

            if frm is None:  # Wildcard
                allowed.append(cmd)
            elif isinstance(frm, list) and current_state in frm:
                allowed.append(cmd)
            elif isinstance(frm, str) and current_state == frm:
                allowed.append(cmd)

        return list(set(allowed))

    def get_states(self, aggregate: str) -> list[str]:
        """Get all defined states for an aggregate.

        Args:
            aggregate: Name of the aggregate

        Returns:
            List of state names
        """
        sm = self._machines.get(aggregate) or {}
        return sm.get("states", [])

    def get_terminal_states(self, aggregate: str) -> list[str]:
        """Get terminal (final) states for an aggregate.

        Args:
            aggregate: Name of the aggregate

        Returns:
            List of terminal state names
        """
        sm = self._machines.get(aggregate) or {}
        return sm.get("terminal_states", [])

    @property
    def aggregates(self) -> list[str]:
        """Get list of all registered aggregate names."""
        return list(self._machines.keys())


@dataclass
class StateTransitionException(DomainException):
    """Raised when an invalid state transition is attempted.

    Inherits from DomainException for consistent exception handling
    and automatic integration with Contract-as-Code reason codes.

    Attributes:
        aggregate: Name of the aggregate
        current_state: Current state when transition was attempted
        command: Command that was rejected
    """

    aggregate: str = ""
    current_state: str = ""
    command: str = ""

    def __post_init__(self):
        # Set reason_code before calling parent
        if not self.reason_code:
            object.__setattr__(self, 'reason_code', "STATE_TRANSITION_INVALID")
        # Build message
        msg = (
            f"{self.aggregate}: command '{self.command}' "
            f"not allowed in state '{self.current_state}'"
        )
        if not self.message:
            object.__setattr__(self, 'message', msg)
        # Add state details
        self.details.update({
            "aggregate": self.aggregate,
            "current_state": self.current_state,
            "command": self.command,
        })
        super().__post_init__()
