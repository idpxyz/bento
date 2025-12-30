"""
Unit tests for Bento Contracts module.
"""
import json

import pytest
import yaml

from bento.contracts import (
    ContractConfig,
    ContractLoader,
    ReasonCodeCatalog,
    RoutingMatrix,
    StateMachineEngine,
    StateTransitionException,
)


class TestStateMachineEngine:
    """Tests for StateMachineEngine."""

    @pytest.fixture
    def order_sm(self):
        """Sample Order state machine definition."""
        return {
            "aggregate": "Order",
            "states": ["DRAFT", "SUBMITTED", "COMPLETED", "CANCELLED"],
            "terminal_states": ["COMPLETED", "CANCELLED"],
            "transitions": [
                {"from": "DRAFT", "command": "Submit", "to": "SUBMITTED"},
                {"from": "SUBMITTED", "command": "Complete", "to": "COMPLETED"},
                {"from": ["DRAFT", "SUBMITTED"], "command": "Cancel", "to": "CANCELLED"},
                {"from": None, "command": "Audit", "to": None},
            ]
        }

    @pytest.fixture
    def engine(self, order_sm):
        return StateMachineEngine({"Order": order_sm})

    def test_valid_single_state_transition(self, engine):
        engine.validate("Order", "DRAFT", "Submit")

    def test_valid_multi_state_transition(self, engine):
        engine.validate("Order", "DRAFT", "Cancel")
        engine.validate("Order", "SUBMITTED", "Cancel")

    def test_wildcard_transition(self, engine):
        engine.validate("Order", "DRAFT", "Audit")
        engine.validate("Order", "SUBMITTED", "Audit")
        engine.validate("Order", "COMPLETED", "Audit")

    def test_invalid_transition_raises(self, engine):
        with pytest.raises(StateTransitionException) as exc:
            engine.validate("Order", "COMPLETED", "Submit")
        assert exc.value.aggregate == "Order"
        assert exc.value.current_state == "COMPLETED"
        assert exc.value.command == "Submit"

    def test_get_allowed_commands(self, engine):
        commands = engine.get_allowed_commands("Order", "DRAFT")
        assert "Submit" in commands
        assert "Cancel" in commands
        assert "Audit" in commands

    def test_get_states(self, engine):
        states = engine.get_states("Order")
        assert "DRAFT" in states
        assert "SUBMITTED" in states

    def test_get_terminal_states(self, engine):
        terminal = engine.get_terminal_states("Order")
        assert "COMPLETED" in terminal
        assert "CANCELLED" in terminal

    def test_aggregates_property(self, engine):
        assert "Order" in engine.aggregates


class TestReasonCodeCatalog:
    """Tests for ReasonCodeCatalog."""

    @pytest.fixture
    def catalog(self):
        doc = {
            "reason_codes": [
                {"reason_code": "VALIDATION_FAILED", "http_status": 400, "category": "VALIDATION"},
                {"reason_code": "NOT_FOUND", "http_status": 404, "category": "CLIENT"},
            ]
        }
        return ReasonCodeCatalog(doc)

    def test_get_existing_code(self, catalog):
        code = catalog.get("VALIDATION_FAILED")
        assert code is not None
        assert code.http_status == 400
        assert code.category == "VALIDATION"

    def test_get_nonexistent_code(self, catalog):
        assert catalog.get("UNKNOWN") is None

    def test_all_codes(self, catalog):
        assert len(catalog.all()) == 2

    def test_by_category(self, catalog):
        validation_codes = catalog.by_category("VALIDATION")
        assert len(validation_codes) == 1
        assert validation_codes[0].code == "VALIDATION_FAILED"

    def test_contains(self, catalog):
        assert "VALIDATION_FAILED" in catalog
        assert "UNKNOWN" not in catalog


class TestRoutingMatrix:
    """Tests for RoutingMatrix."""

    @pytest.fixture
    def matrix(self):
        doc = {
            "routes": [
                {"event_type": "OrderCreated", "topic": "order.events", "produced_by": "order-service"},
                {"event_type": "OrderUpdated", "topic": "order.events"},
            ]
        }
        return RoutingMatrix(doc)

    def test_topic_for_existing(self, matrix):
        assert matrix.topic_for("OrderCreated") == "order.events"

    def test_topic_for_unknown_raises(self, matrix):
        with pytest.raises(KeyError):
            matrix.topic_for("Unknown")

    def test_get_route(self, matrix):
        route = matrix.get_route("OrderCreated")
        assert route is not None
        assert route.topic == "order.events"
        assert route.produced_by == "order-service"

    def test_contains(self, matrix):
        assert "OrderCreated" in matrix
        assert "Unknown" not in matrix


class TestContractLoader:
    """Tests for ContractLoader."""

    @pytest.fixture
    def contracts_dir(self, tmp_path):
        """Create a temporary contracts directory."""
        contracts = tmp_path / "contracts"

        # Reason codes
        rc_dir = contracts / "reason-codes"
        rc_dir.mkdir(parents=True)
        (rc_dir / "reason_codes.full.v1_0.json").write_text(json.dumps({
            "reason_codes": [{"reason_code": "TEST", "http_status": 400}]
        }))

        # Routing
        routing_dir = contracts / "routing"
        routing_dir.mkdir(parents=True)
        (routing_dir / "event_routing_matrix.full.v1_0.yaml").write_text(yaml.dump({
            "routes": [{"event_type": "TestEvent", "topic": "test.events"}]
        }))

        # State machines
        sm_dir = contracts / "state-machines"
        sm_dir.mkdir(parents=True)
        (sm_dir / "order.state-machine.yaml").write_text(yaml.dump({
            "aggregate": "Order",
            "states": ["DRAFT", "DONE"],
            "transitions": [{"from": "DRAFT", "command": "Complete", "to": "DONE"}]
        }))

        return tmp_path

    def test_load_from_dir(self, contracts_dir):
        contracts = ContractLoader.load_from_dir(str(contracts_dir))

        assert contracts.reason_codes.get("TEST") is not None
        assert contracts.routing.topic_for("TestEvent") == "test.events"
        contracts.state_machines.validate("Order", "DRAFT", "Complete")

    def test_load_with_config(self, contracts_dir):
        config = ContractConfig(contracts_root=str(contracts_dir / "contracts"))
        contracts = ContractLoader.load(config)

        assert len(contracts.reason_codes) == 1

    def test_missing_contracts_graceful(self, tmp_path):
        contracts = ContractLoader.load_from_dir(str(tmp_path))

        assert len(contracts.reason_codes) == 0
        assert len(contracts.routing) == 0
