"""Bento Contracts - Contracts-as-Code Module.

This module provides infrastructure for managing business contracts as code,
including state machines, reason codes, event routing, schema validation,
and breaking change detection.

Key Components:
- StateMachineEngine: Validates aggregate state transitions based on YAML definitions
- ReasonCodeCatalog: Manages error/reason codes from JSON contracts
- RoutingMatrix: Maps event types to message topics
- EventSchemaRegistry: Validates events against JSON schemas
- BreakingChangeDetector: Detects breaking changes between schema versions
- SchemaComparator: Compares two JSON schemas and provides diff information
- CompatibilityValidator: Validates compatibility between schema versions
- ContractLoader: Unified loader for all contract types

Example:
    ```python
    from bento.contracts import (
        ContractLoader, ContractConfig,
        BreakingChangeDetector, CompatibilityValidator
    )

    config = ContractConfig(contracts_root="./contracts")
    contracts = ContractLoader.load(config)

    # Validate state transition
    contracts.state_machines.validate("Order", "DRAFT", "Submit")

    # Detect breaking changes
    detector = BreakingChangeDetector()
    report = detector.detect(old_schema, new_schema)
    if not report.is_compatible:
        print(f"Breaking changes: {len(report.breaking_changes)}")

    # Validate compatibility
    validator = CompatibilityValidator()
    result = validator.validate_backward_compatible(old_schema, new_schema)
    ```
"""

from bento.contracts.state_machines import StateMachineEngine, StateTransitionException
from bento.contracts.catalogs import ReasonCode, ReasonCodeCatalog, RoutingMatrix
from bento.contracts.schema_registry import EventSchemaRegistry
from bento.contracts.breaking_change_detector import (
    BreakingChangeDetector,
    BreakingChange,
    BreakingChangeReport,
    ChangeType,
)
from bento.contracts.schema_comparator import SchemaComparator, SchemaDiff
from bento.contracts.compatibility_validator import (
    CompatibilityValidator,
    CompatibilityResult,
    CompatibilityMode,
)
from bento.contracts.mock_generator import MockGenerator
from bento.contracts.sdk_generator import SDKGenerator
from bento.contracts.openapi_generator import OpenAPIGenerator
from bento.contracts.loader import ContractLoader, ContractConfig, Contracts

__all__ = [
    # Core types
    "ReasonCode",
    "ChangeType",
    "CompatibilityMode",
    # Core engines
    "StateMachineEngine",
    "ReasonCodeCatalog",
    "RoutingMatrix",
    "EventSchemaRegistry",
    # Breaking change detection (P1)
    "BreakingChangeDetector",
    "BreakingChange",
    "BreakingChangeReport",
    # Schema comparison (P1)
    "SchemaComparator",
    "SchemaDiff",
    # Compatibility validation (P1)
    "CompatibilityValidator",
    "CompatibilityResult",
    # Mock / SDK / Generator (P2)
    "MockGenerator",
    "SDKGenerator",
    "OpenAPIGenerator",
    # Loader
    "ContractLoader",
    "ContractConfig",
    "Contracts",
    # Exceptions
    "StateTransitionException",
]
