from contract_governance.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()


def test_create_contract_version():
    data = {
        "contract_id": "test-contract",
        "version": "1.0.0",
        "contract_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
        },
        "released_by": "test@example.com",
        "release_notes": "Initial release",
    }
    response = client.post("/api/v1/contract-versions", json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["contract_id"] == "test-contract"
    assert result["version"] == "1.0.0"
    assert result["status"] == "draft"


def test_get_contract_version():
    data = {
        "contract_id": "test-contract-2",
        "version": "1.0.0",
        "contract_schema": {"type": "object"},
        "released_by": "test@example.com",
    }
    create_response = client.post("/api/v1/contract-versions", json=data)
    assert create_response.status_code == 200

    get_response = client.get("/api/v1/contract-versions/test-contract-2/1.0.0")
    assert get_response.status_code == 200
    assert get_response.json()["version"] == "1.0.0"


def test_list_contract_versions():
    data = {
        "contract_id": "test-contract-3",
        "version": "1.0.0",
        "contract_schema": {"type": "object"},
        "released_by": "test@example.com",
    }
    client.post("/api/v1/contract-versions", json=data)

    response = client.get("/api/v1/contract-versions/test-contract-3")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_release_contract_version():
    data = {
        "contract_id": "test-contract-4",
        "version": "1.0.0",
        "contract_schema": {"type": "object"},
        "released_by": "test@example.com",
    }
    client.post("/api/v1/contract-versions", json=data)

    response = client.post("/api/v1/contract-versions/test-contract-4/1.0.0/release")
    assert response.status_code == 200
    assert response.json()["status"] == "released"


def test_create_approval():
    data = {
        "contract_id": "test-contract",
        "version": "1.0.0",
        "approvers": ["alice@example.com", "bob@example.com"],
    }
    response = client.post("/api/v1/approvals", json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "pending"
    assert len(result["approvers"]) == 2


def test_approve():
    approval_data = {
        "contract_id": "test-contract",
        "version": "1.0.0",
        "approvers": ["alice@example.com"],
    }
    approval_response = client.post("/api/v1/approvals", json=approval_data)
    approval_id = approval_response.json()["id"]

    response = client.post(f"/api/v1/approvals/{approval_id}/approve?approver=alice@example.com")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_create_change():
    data = {
        "contract_id": "test-contract",
        "from_version": "1.0.0",
        "to_version": "1.1.0",
        "changed_by": "john@example.com",
        "change_type": "compatible",
        "changes": {"added_fields": ["status"]},
        "reason": "Add status field",
    }
    response = client.post("/api/v1/changes", json=data)
    assert response.status_code == 200
    assert response.json()["change_type"] == "compatible"


def test_create_dependency():
    data = {
        "contract_id": "order-service",
        "service_id": "payment-service",
        "version": "1.0.0",
        "dependency_type": "producer",
    }
    response = client.post("/api/v1/dependencies", json=data)
    assert response.status_code == 200
    assert response.json()["dependency_type"] == "producer"


def test_contract_insights_endpoint():
    contract_id = "insights-contract"
    version = "2.0.0"

    # Create contract version
    client.post(
        "/api/v1/contract-versions",
        json={
            "contract_id": contract_id,
            "version": version,
            "contract_schema": {"type": "object"},
            "released_by": "qa@example.com",
            "release_notes": "Insights release",
        },
    )

    # Create approval stage
    client.post(
        "/api/v1/approvals",
        json={
            "contract_id": contract_id,
            "version": version,
            "approvers": ["alice@example.com", "bob@example.com"],
        },
    )

    # Create change record
    client.post(
        "/api/v1/changes",
        json={
            "contract_id": contract_id,
            "from_version": "1.0.0",
            "to_version": version,
            "changed_by": "alice@example.com",
            "change_type": "compatible",
            "changes": {"fields_added": ["status"]},
            "reason": "Add status field",
        },
    )

    # Create dependency
    client.post(
        "/api/v1/dependencies",
        json={
            "contract_id": contract_id,
            "service_id": "order-service",
            "version": version,
            "dependency_type": "consumer",
        },
    )

    response = client.get(f"/api/v1/contract-versions/{contract_id}/{version}/insights")
    assert response.status_code == 200

    payload = response.json()
    assert payload["contract_version"]["contract_id"] == contract_id
    assert payload["contract_version"]["version"] == version
    assert payload["workflow"] is not None
    assert payload["workflow"]["workflow_id"] == f"{contract_id}:{version}"
    assert payload["change_history"]["contract_id"] == contract_id
    assert len(payload["change_history"]["changes"]) >= 1
    assert len(payload["compatibility"]["rules"]) >= 1
    assert len(payload["dependency_graph"]["links"]) >= 1
