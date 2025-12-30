"""
Contract Loader - Contracts-as-Code.

Loads all contracts (state machines, reason codes, routing, schemas) from files.
"""

import json
import pathlib

import yaml
from loms.shared.contracts.catalogs import ReasonCodeCatalog, RoutingMatrix
from loms.shared.contracts.schema_registry import EventSchemaRegistry
from loms.shared.contracts.state_machines import StateMachineEngine


class ContractLoader:
    """
    Loads all contracts from the contracts/ directory.

    Usage:
        contracts = ContractLoader.load_from_dir("/path/to/project")
        contracts["state_machines"].validate("Shipment", "DRAFT", "PlaceHold")
    """

    @staticmethod
    def load_from_dir(root: str) -> dict:
        """
        Load all contracts from the project root directory.

        Args:
            root: Path to project root (contains contracts/ directory)

        Returns:
            dict with keys: state_machines, reason_codes, routing, schemas
        """
        p = pathlib.Path(root)

        # Reason codes
        reason_path = p / "contracts/reason-codes/reason_codes.full.v1_0.json"
        reason_doc = (
            json.loads(reason_path.read_text(encoding="utf-8"))
            if reason_path.exists()
            else {"reason_codes": []}
        )

        # Routing matrix
        routing_path = p / "contracts/routing/event_routing_matrix.full.v1_0.yaml"
        routing_doc = (
            yaml.safe_load(routing_path.read_text(encoding="utf-8"))
            if routing_path.exists()
            else {"routes": []}
        )

        # State machines
        machines = {}
        sm_dir = p / "contracts/state-machines"
        if sm_dir.exists():
            sm_shipment_path = sm_dir / "shipment.state-machine.full.v1_0.yaml"
            sm_leg_path = sm_dir / "leg.state-machine.full.v1_0.yaml"
            if sm_shipment_path.exists():
                machines["Shipment"] = yaml.safe_load(sm_shipment_path.read_text(encoding="utf-8"))
            if sm_leg_path.exists():
                machines["Leg"] = yaml.safe_load(sm_leg_path.read_text(encoding="utf-8"))

        # Event schemas
        schemas = None
        events_dir = p / "contracts/events"
        if events_dir.exists() and (events_dir / "envelope.schema.json").exists():
            schemas = EventSchemaRegistry.from_dir(events_dir)

        return {
            "reason_codes": ReasonCodeCatalog(reason_doc),
            "routing": RoutingMatrix(routing_doc),
            "state_machines": StateMachineEngine(machines),
            "schemas": schemas,
        }
