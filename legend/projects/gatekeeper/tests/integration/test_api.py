# tests/integration/test_api.py
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_policy_evaluate():
    payload = {
        "principal": {"sub": "u1", "scope": ["orders:create"]},
        "action": "create",
        "resource": "orders",
        "context": {}
    }
    response = client.post("/policy/evaluate", json=payload)
    assert response.status_code == 200
    assert response.json()["allow"] is True
