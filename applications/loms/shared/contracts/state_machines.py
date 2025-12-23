"""
State Machine Engine - Contracts-as-Code.

Validates state transitions based on YAML-defined state machines.
"""


class StateMachineEngine:
    """
    Validates state transitions for aggregates based on YAML definitions.

    Usage:
        engine = StateMachineEngine({"Shipment": shipment_sm_yaml, "Leg": leg_sm_yaml})
        engine.validate("Shipment", "DRAFT", "PlaceHold")  # raises if invalid
    """

    def __init__(self, machines: dict):
        self._machines = machines

    def validate(self, aggregate: str, current_state: str, command: str) -> None:
        """
        Validate that a command is allowed from the current state.

        Raises:
            StateTransitionError: if the transition is not allowed
        """
        sm = self._machines.get(aggregate) or {}
        transitions = sm.get("transitions", [])

        for t in transitions:
            frm = t.get("from")
            cmd = t.get("command")
            if cmd != command:
                continue
            if frm is None:
                return  # Wildcard - allowed from any state
            if isinstance(frm, list) and current_state in frm:
                return
            if isinstance(frm, str) and current_state == frm:
                return

        raise StateTransitionError(
            aggregate=aggregate,
            current_state=current_state,
            command=command,
        )


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, aggregate: str, current_state: str, command: str):
        self.aggregate = aggregate
        self.current_state = current_state
        self.command = command
        super().__init__(
            f"{aggregate}: command '{command}' not allowed in state '{current_state}'"
        )
