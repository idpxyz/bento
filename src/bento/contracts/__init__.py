"""Bento Contracts - Contracts-as-Code Module.

This module provides infrastructure for managing business contracts as code,
including state machines, reason codes, event routing, and schema validation.

Key Components:
- StateMachineEngine: Validates aggregate state transitions based on YAML definitions
- ReasonCodeCatalog: Manages error/reason codes from JSON contracts
- RoutingMatrix: Maps event types to message topics
- EventSchemaRegistry: Validates events against JSON schemas
- ContractLoader: Unified loader for all contract types

Example:
    ```python
    from bento.contracts import ContractLoader, ContractConfig

    config = ContractConfig(contracts_root="./contracts")
    contracts = ContractLoader.load(config)

    # Validate state transition
    contracts.state_machines.validate("Order", "DRAFT", "Submit")

    # Get reason code info
    code = contracts.reason_codes.get("VALIDATION_FAILED")

    # Get event routing
    topic = contracts.routing.topic_for("OrderCreated")
    ```
"""

from bento.contracts.state_machines import StateMachineEngine, StateTransitionException
from bento.contracts.catalogs import ReasonCode, ReasonCodeCatalog, RoutingMatrix
from bento.contracts.schema_registry import EventSchemaRegistry
from bento.contracts.loader import ContractLoader, ContractConfig, Contracts

__all__ = [
    # Core types
    "ReasonCode",
    # Core engines
    "StateMachineEngine",
    "ReasonCodeCatalog",
    "RoutingMatrix",
    "EventSchemaRegistry",
    # Loader
    "ContractLoader",
    "ContractConfig",
    "Contracts",
    # Exceptions
    "StateTransitionException",
]
