"""Contract Loader - Contracts-as-Code.

Unified loader for all contract types (state machines, reason codes, routing, schemas).
Provides configuration-driven contract loading with sensible defaults.

Usage:
    ```python
    from bento.contracts import ContractLoader, ContractConfig

    # With defaults
    contracts = ContractLoader.load_from_dir("./project_root")

    # With custom config
    config = ContractConfig(
        contracts_root="./contracts",
        state_machine_patterns=["*.state-machine.yaml"],
        reason_codes_file="reason_codes.json",
    )
    contracts = ContractLoader.load(config)
    ```
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

from bento.contracts.catalogs import ReasonCodeCatalog, RoutingMatrix
from bento.contracts.state_machines import StateMachineEngine


@dataclass
class ContractConfig:
    """Configuration for contract loading.

    Attributes:
        contracts_root: Root directory for contracts (relative or absolute)
        state_machines_dir: Subdirectory for state machine YAMLs
        reason_codes_pattern: Glob pattern for reason codes JSON
        routing_pattern: Glob pattern for routing matrix YAML
        events_dir: Subdirectory for event schemas
    """
    contracts_root: str = "contracts"
    state_machines_dir: str = "state-machines"
    reason_codes_pattern: str = "reason-codes/reason_codes*.json"
    routing_pattern: str = "routing/event_routing_matrix*.yaml"
    events_dir: str = "events"

    # Advanced: custom file patterns
    state_machine_patterns: list[str] = field(
        default_factory=lambda: ["*.state-machine.*.yaml", "*.state-machine.yaml"]
    )


@dataclass
class Contracts:
    """Container for loaded contracts.

    Attributes:
        state_machines: State machine engine for transition validation
        reason_codes: Reason code catalog
        routing: Event routing matrix
        schemas: Event schema registry (optional)
    """
    state_machines: StateMachineEngine
    reason_codes: ReasonCodeCatalog
    routing: RoutingMatrix
    schemas: Any = None  # EventSchemaRegistry, optional to avoid import


class ContractLoader:
    """Unified loader for all contract types.

    Loads contracts from files based on configuration and provides
    a Contracts container with all loaded components.

    Example:
        ```python
        # Simple usage
        contracts = ContractLoader.load_from_dir("./")

        # Access components
        contracts.state_machines.validate("Order", "DRAFT", "Submit")
        code = contracts.reason_codes.get("VALIDATION_FAILED")
        topic = contracts.routing.topic_for("OrderCreated")
        ```
    """

    @staticmethod
    def load(config: ContractConfig) -> Contracts:
        """Load contracts based on configuration.

        Args:
            config: Contract configuration

        Returns:
            Contracts container with all loaded components
        """
        if not HAS_YAML:
            raise ImportError(
                "PyYAML is required for contract loading. "
                "Install with: pip install pyyaml"
            )

        root = pathlib.Path(config.contracts_root)

        # Load reason codes
        reason_codes = ContractLoader._load_reason_codes(root, config)

        # Load routing matrix
        routing = ContractLoader._load_routing(root, config)

        # Load state machines
        state_machines = ContractLoader._load_state_machines(root, config)

        # Load event schemas (optional)
        schemas = ContractLoader._load_schemas(root, config)

        return Contracts(
            state_machines=state_machines,
            reason_codes=reason_codes,
            routing=routing,
            schemas=schemas,
        )

    @staticmethod
    def load_from_dir(project_root: str) -> Contracts:
        """Load contracts from a project root directory.

        Convenience method that uses default configuration.
        Expects contracts in {project_root}/contracts/

        Args:
            project_root: Path to project root directory

        Returns:
            Contracts container with all loaded components
        """
        root = pathlib.Path(project_root)
        contracts_dir = root / "contracts"

        # Try versioned structure first (contracts/loms/v1.0.0/)
        versioned_dirs = list(contracts_dir.glob("*/v*"))
        if versioned_dirs:
            # Use the first versioned directory found
            contracts_dir = versioned_dirs[0]

        config = ContractConfig(contracts_root=str(contracts_dir))
        return ContractLoader.load(config)

    @staticmethod
    def _load_reason_codes(root: pathlib.Path, config: ContractConfig) -> ReasonCodeCatalog:
        """Load reason codes from JSON file."""
        files = list(root.glob(config.reason_codes_pattern))
        if files:
            doc = json.loads(files[0].read_text(encoding="utf-8"))
            return ReasonCodeCatalog(doc)
        return ReasonCodeCatalog({"reason_codes": []})

    @staticmethod
    def _load_routing(root: pathlib.Path, config: ContractConfig) -> RoutingMatrix:
        """Load routing matrix from YAML file."""
        files = list(root.glob(config.routing_pattern))
        if files:
            doc = yaml.safe_load(files[0].read_text(encoding="utf-8"))
            return RoutingMatrix(doc or {})
        return RoutingMatrix({"routes": []})

    @staticmethod
    def _load_state_machines(root: pathlib.Path, config: ContractConfig) -> StateMachineEngine:
        """Load state machines from YAML files."""
        sm_dir = root / config.state_machines_dir
        machines: dict[str, dict[str, Any]] = {}

        if sm_dir.exists():
            for pattern in config.state_machine_patterns:
                for path in sm_dir.glob(pattern):
                    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
                    if doc and "aggregate" in doc:
                        aggregate = doc["aggregate"]
                        machines[aggregate] = doc
                    else:
                        # Infer aggregate name from filename
                        # shipment.state-machine.full.v1_0.yaml -> Shipment
                        name = path.stem.split(".")[0].title()
                        machines[name] = doc or {}

        return StateMachineEngine(machines)

    @staticmethod
    def _load_schemas(root: pathlib.Path, config: ContractConfig) -> Any:
        """Load event schemas if available."""
        events_dir = root / config.events_dir
        envelope_path = events_dir / "envelope.schema.json"

        if events_dir.exists() and envelope_path.exists():
            try:
                from bento.contracts.schema_registry import EventSchemaRegistry
                return EventSchemaRegistry.from_dir(events_dir)
            except ImportError:
                # jsonschema not installed
                return None
        return None
