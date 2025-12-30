"""Contract Gate - Startup Validation.

Validates contracts at application startup to ensure all required
contracts are present and valid before serving requests.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass
class GateResult:
    """Result of gate validation.

    Attributes:
        passed: Whether validation passed
        errors: List of error messages
        warnings: List of warning messages
    """
    passed: bool
    errors: list[str]
    warnings: list[str]


class ContractGate:
    """Startup gate for contract validation.

    Validates that all required contracts are present and loadable.
    Should be called during application startup before serving requests.

    Example:
        ```python
        gate = ContractGate(contracts_root="./contracts")

        # Validate and raise on failure
        gate.validate()

        # Or check result manually
        result = gate.check()
        if not result.passed:
            for error in result.errors:
                print(f"ERROR: {error}")
        ```
    """

    def __init__(
        self,
        contracts_root: str,
        require_state_machines: bool = False,
        require_reason_codes: bool = True,
        require_routing: bool = False,
        require_schemas: bool = False,
    ):
        """Initialize gate with requirements.

        Args:
            contracts_root: Root directory for contracts
            require_state_machines: Fail if no state machines found
            require_reason_codes: Fail if no reason codes found
            require_routing: Fail if no routing matrix found
            require_schemas: Fail if no event schemas found
        """
        self.contracts_root = pathlib.Path(contracts_root)
        self.require_state_machines = require_state_machines
        self.require_reason_codes = require_reason_codes
        self.require_routing = require_routing
        self.require_schemas = require_schemas

    def check(self) -> GateResult:
        """Check contracts without raising exceptions.

        Returns:
            GateResult with validation status and messages
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check contracts root exists
        if not self.contracts_root.exists():
            errors.append(f"Contracts directory not found: {self.contracts_root}")
            return GateResult(passed=False, errors=errors, warnings=warnings)

        # Check reason codes
        reason_files = list(self.contracts_root.rglob("reason_codes*.json"))
        if not reason_files:
            msg = "No reason codes file found (reason_codes*.json)"
            if self.require_reason_codes:
                errors.append(msg)
            else:
                warnings.append(msg)
        else:
            # Try to load and validate
            try:
                import json
                for f in reason_files:
                    doc = json.loads(f.read_text(encoding="utf-8"))
                    if "reason_codes" not in doc:
                        errors.append(f"Invalid reason codes file: {f} (missing 'reason_codes' key)")
            except Exception as e:
                errors.append(f"Failed to load reason codes: {e}")

        # Check state machines
        sm_files = list(self.contracts_root.rglob("*.state-machine*.yaml"))
        if not sm_files:
            msg = "No state machine files found (*.state-machine*.yaml)"
            if self.require_state_machines:
                errors.append(msg)
            else:
                warnings.append(msg)
        else:
            # Try to load and validate
            try:
                import yaml
                for f in sm_files:
                    doc = yaml.safe_load(f.read_text(encoding="utf-8"))
                    if not doc or "transitions" not in doc:
                        warnings.append(f"State machine missing 'transitions': {f}")
            except Exception as e:
                errors.append(f"Failed to load state machines: {e}")

        # Check routing matrix
        routing_files = list(self.contracts_root.rglob("*routing*.yaml"))
        if not routing_files:
            msg = "No routing matrix found (*routing*.yaml)"
            if self.require_routing:
                errors.append(msg)
            else:
                warnings.append(msg)

        # Check event schemas
        schema_files = list(self.contracts_root.rglob("envelope.schema.json"))
        if not schema_files:
            msg = "No event envelope schema found (envelope.schema.json)"
            if self.require_schemas:
                errors.append(msg)
            else:
                warnings.append(msg)

        return GateResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate(self) -> None:
        """Validate contracts, raising exception on failure.

        Raises:
            ContractGateError: If validation fails
        """
        result = self.check()
        if not result.passed:
            raise ContractGateError(
                f"Contract gate failed with {len(result.errors)} error(s)",
                errors=result.errors,
                warnings=result.warnings,
            )


class ContractGateError(Exception):
    """Raised when contract gate validation fails.

    Attributes:
        errors: List of error messages
        warnings: List of warning messages
    """

    def __init__(
        self,
        message: str,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        super().__init__(message)
        self.errors = errors or []
        self.warnings = warnings or []

    def __str__(self) -> str:
        lines = [super().__str__()]
        for error in self.errors:
            lines.append(f"  - {error}")
        return "\n".join(lines)
