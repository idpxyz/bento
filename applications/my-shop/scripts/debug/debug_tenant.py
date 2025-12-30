"""Debug script to check tenant middleware."""

from fastapi.testclient import TestClient
from runtime.bootstrap_v2 import create_app


def main():
    app = create_app()
    client = TestClient(app)

    print("\n=== Testing Tenant Middleware ===\n")

    # Test with header
    print("1. Request WITH X-Tenant-ID header:")
    response = client.get("/api/v1/auth/me/context", headers={"X-Tenant-ID": "test-tenant"})
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Tenant ID from response: {data.get('tenant_id')}")
    print(f"   Full response: {data}")

    # Test without header
    print("\n2. Request WITHOUT X-Tenant-ID header:")
    response = client.get("/api/v1/auth/me/context")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Tenant ID from response: {data.get('tenant_id')}")


if __name__ == "__main__":
    main()
